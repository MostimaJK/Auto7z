"""Extraction engine independent of the GUI; each attempt owns its staging folder."""
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path


class Cancelled(Exception):
    pass


@dataclass
class Result:
    source: str
    status: str
    output: str = ""
    detail: str = ""
    archive: str = ""


class Engine:
    def __init__(self, path_7z, path_rar, passwords=(), mode="auto", depth=20,
                 delete_inner=False, idle_timeout=0, precheck_timeout=30,
                 notify=None, progress=None, delete_source=False):
        self.tools = {"7z": path_7z, "winrar": path_rar}
        self.passwords = list(dict.fromkeys(p for p in passwords if p))
        self.mode, self.depth = mode, depth
        self.delete_inner, self.idle_timeout = delete_inner, idle_timeout
        self.delete_source = delete_source
        self.precheck_timeout = precheck_timeout
        self.notify = notify or (lambda message: None)
        self.progress = progress or (lambda data: None)
        self.progress_context = {}
        self.cancelled = threading.Event()
        self.preferred_password = None

    def cancel(self):
        self.cancelled.set()

    def check_cancel(self):
        if self.cancelled.is_set():
            raise Cancelled()

    @staticmethod
    def _cpu_time(process):
        # CPU work also counts as activity during solid-archive decompression.
        if os.name != "nt":
            return 0
        import ctypes
        from ctypes import wintypes
        values = [wintypes.FILETIME() for _ in range(4)]
        fn = ctypes.windll.kernel32.GetProcessTimes
        fn.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        if fn(wintypes.HANDLE(int(process._handle)), *(ctypes.byref(v) for v in values)):
            return sum((v.dwHighDateTime << 32) + v.dwLowDateTime for v in values[2:])
        return 0

    @staticmethod
    def _folder_activity(folder):
        count, size, modified = 0, 0, 0
        if folder:
            for root, dirs, files in os.walk(folder, followlinks=False):
                dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
                for name in files:
                    try:
                        stat = os.stat(os.path.join(root, name), follow_symlinks=False)
                        count += 1
                        size += stat.st_size
                        modified = max(modified, stat.st_mtime_ns)
                    except OSError:
                        pass
        return count, size, modified

    def _run(self, command, folder=None, limit=0):
        self.check_cancel()
        # Spool instead of PIPE: no pipe deadlock, no unbounded RAM use.
        # Independent reader: seeking the child's output handle would corrupt its
        # shared file position. Keep the diagnostic spool and bounded reader separate.
        with tempfile.TemporaryDirectory(prefix="auto7z-output-") as capture, \
                open(Path(capture) / "output.log", "w+b") as output, \
                open(Path(capture) / "output.log", "rb") as progress_output:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                       stdout=output, stderr=subprocess.STDOUT,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            started = last_active = last_report = time.monotonic()
            previous = None
            progress_tail, reported = b"", None
            def read_progress():
                nonlocal progress_tail, reported
                if folder is None or "-bsp1" not in command:
                    return
                chunk = progress_output.read(65536)
                if not chunk:
                    return
                progress_tail = (progress_tail + chunk)[-65536:]
                values = [match for match in re.finditer(rb"(?:^|[\r\n\x08]) *(\d{1,3})%(?=\s|\x08|$)", progress_tail) if int(match[1]) <= 100]
                if values:
                    percent = int(values[-1][1])
                    if 0 <= percent <= 100 and percent != reported:
                        reported = percent
                        self.progress({**self.progress_context, "percent": percent})
                    progress_tail = progress_tail[values[-1].end():][-4096:]
            try:
                while process.poll() is None:
                    self.check_cancel()
                    now = time.monotonic()
                    read_progress()
                    if limit and now - started > limit:
                        raise TimeoutError("目錄預檢超時，將直接嘗試解壓")
                    if now - last_report >= 1:
                        activity = (os.fstat(output.fileno()).st_size, self._cpu_time(process),
                                    self._folder_activity(folder) if self.idle_timeout else ())
                        if activity != previous:
                            previous, last_active = activity, now
                        if self.idle_timeout and folder and now - last_active > self.idle_timeout:
                            raise TimeoutError(f"連續 {self.idle_timeout} 秒未檢測到活動；可關閉停滯保護後重試")
                        self.notify(f"{getattr(self, 'activity', '目錄預檢')} · 已用時 {int(now-started)} 秒 · 可取消")
                        last_report = now
                    # Wait wakes immediately when the child exits; bounded for cancellation.
                    try:
                        process.wait(timeout=0.05)
                    except subprocess.TimeoutExpired:
                        pass
                read_progress()
                output.seek(max(0, os.fstat(output.fileno()).st_size - 262144))
                return process.returncode, output.read().decode("utf-8", errors="replace")
            finally:
                if process.poll() is None:
                    # Only stop the child belonging to this attempt.
                    process.kill()
                process.wait()

    def _tool_order(self, source):
        available = [t for t in ("7z", "winrar") if os.path.isfile(self.tools[t])]
        if self.mode != "auto":
            return [self.mode] if self.mode in available else []
        return available

    def _encrypted(self, source):
        if not os.path.isfile(self.tools["7z"]) or self.mode == "winrar":
            return None
        try:
            code, listing = self._run([self.tools["7z"], "l", "-slt", "-sccUTF-8",
                                       "-p", "--", str(source)], limit=self.precheck_timeout)
            if code:
                return None  # Header encryption, unsupported format or precheck failure.
            # Any encrypted entry needs a password. Archive-level Path is not an entry.
            return "Encrypted = +" in listing
        except TimeoutError:
            self.notify("預檢耗時較長，繼續直接解壓")
            return None

    @staticmethod
    def _unique(path):
        path = Path(path)
        candidate, index = path, 1
        while candidate.exists():
            candidate = path.with_name(f"{path.name}_{index}")
            index += 1
        return candidate

    @staticmethod
    def _discard(stage, parent):
        # Never recursively remove a user destination or a computed unchecked path.
        stage, parent = Path(stage).resolve(), Path(parent).resolve()
        if stage.parent != parent or not stage.name.startswith(".auto7z-"):
            raise ValueError("拒絕清理非任務臨時目錄")
        shutil.rmtree(stage)

    def extract(self, source):
        source = Path(source).absolute()
        self.check_cancel()
        self.progress_context = {"archive": source.name, "tool": "", "attempt": 0}
        self.progress({**self.progress_context, "percent": None})
        tools = self._tool_order(source)
        if not tools:
            raise RuntimeError("未找到可用解壓引擎，請檢查工具路徑")
        # With no candidate passwords both branches try the same empty password.
        encrypted = self._encrypted(source) if self.passwords else None
        candidates = self.passwords.copy()
        if self.preferred_password in candidates:
            candidates.remove(self.preferred_password)
            candidates.insert(0, self.preferred_password)
        if encrypted is False:
            candidates.insert(0, None)
        else:
            candidates.append(None)
        errors = {}
        for tool in tools:
            for index, password in enumerate(candidates, 1):
                self.check_cancel()
                self.activity = f"{source.name} · {tool} · {'無密碼' if password is None else f'密碼候選 {index}'}"
                self.notify(self.activity)
                self.progress_context = {"archive": source.name, "tool": tool, "attempt": index}
                self.progress({**self.progress_context, "percent": None})
                stage = Path(tempfile.mkdtemp(prefix=".auto7z-", dir=source.parent))
                publish_failed = False
                try:
                    if tool == "7z":
                        command = [self.tools[tool], "x", f"-o{stage}", "-y", "-bsp1",
                                   "-sccUTF-8", "-p" + (password or ""), "--", str(source)]
                    else:
                        command = [self.tools[tool], "x", "-y", "-o+", "-ibck", "-inul", "-cfg-",
                                   "-p" + password if password is not None else "-p-",
                                   str(source), str(stage) + os.sep]
                    code, output = self._run(command, stage)
                    if code == 0:
                        target = self._unique(source.with_suffix(""))
                        try:
                            os.rename(stage, target)
                        except OSError:
                            publish_failed = True
                            raise RuntimeError(f"解壓已完成但無法移動結果，文件保留在 {stage}")
                        if password is not None:
                            self.preferred_password = password
                        return target
                    # Keep error output bounded and redact passwords before displaying.
                    for secret in self.passwords:
                        output = output.replace(secret, "[密碼]")
                    lines = output.strip().splitlines()
                    diagnostic = [line for line in lines if re.search(
                        r"error|wrong|cannot|corrupt|crc|錯誤|無法|損壞", line, re.I)]
                    detail = " / ".join((diagnostic or lines)[-4:])[:400]
                    errors[tool] = f"{tool} 返回 {code}: {detail or '密碼錯誤、文件損壞或格式不支持'}"
                    if code in (7, 8, 9, 255):
                        break  # CLI / memory / file-create / user-abort cannot be fixed by another password.
                finally:
                    if stage.exists() and not publish_failed:
                        self._discard(stage, source.parent)
        raise RuntimeError("\n".join(errors.values()) if errors else "解壓失敗")

    @staticmethod
    def is_archive(path):
        name = path.name.lower()
        if re.search(r"\.part\d+\.rar$", name):
            return bool(re.search(r"\.part0*1\.rar$", name))
        return path.suffix.lower() in {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz"} or name.endswith((".7z.001", ".zip.001"))

    @staticmethod
    def _scan(folder):
        for root, dirs, files in os.walk(folder, followlinks=False):
            dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
            for name in sorted(files):
                path = Path(root, name)
                if not path.is_symlink() and Engine.is_archive(path):
                    yield path

    @staticmethod
    def archive_snapshot(source):
        """Capture only an exact, contiguous archive family, never a broad glob delete."""
        source = Path(source)
        name = source.name
        pattern, first = None, 1
        split = re.fullmatch(r"(.+)\.(001)", name, re.I)
        part = re.fullmatch(r"(.+\.part)(0*1)(\.rar)", name, re.I)
        if split:
            pattern = re.compile(re.escape(split[1]) + r"\.(\d{3})", re.I)
        elif part:
            pattern = re.compile(re.escape(part[1]) + r"(\d{" + str(len(part[2])) + r"})" + re.escape(part[3]), re.I)
        elif source.suffix.lower() in ('.rar', '.zip'):
            first = 0 if source.suffix.lower() == '.rar' else 1
            letter = 'r' if first == 0 else 'z'
            pattern = re.compile(re.escape(source.stem) + r"\." + letter + r"(\d{2})", re.I)
        numbered = []
        if pattern:
            for path in source.parent.iterdir():
                match = pattern.fullmatch(path.name)
                if match:
                    numbered.append((int(match[1]), path))
        numbered.sort()
        if numbered and [number for number, _ in numbered] != list(range(first, first + len(numbered))):
            raise ValueError('分卷序號不連續；未刪除壓縮文件')
        members = [path for _, path in numbered if path != source] + [source]
        snapshot = []
        for path in members:
            if path.is_symlink() or not path.is_file():
                raise ValueError(f'不是可清理的普通壓縮文件：{path}')
            stat = path.stat()
            snapshot.append((path, (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)))
        return snapshot

    def remove_archive(self, snapshot):
        self.check_cancel()
        for path, expected in snapshot:
            stat = path.stat()
            if path.is_symlink() or (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns) != expected:
                raise ValueError(f'壓縮文件已變更，未刪除：{path}')
        # Check the whole family before deleting anything; retain the entry volume until last.
        for path, _ in snapshot:
            path.unlink()
            self.notify(f'已刪除壓縮文件：{path}')

    def process(self, source, real_ext=""):
        original = Path(source).absolute()
        current = original
        output = None
        try:
            self.check_cancel()
            is_volume = bool(re.search(r'\.001$|\.part0*1\.rar$', current.name, re.I)) or (
                current.suffix.lower() == '.rar' and current.with_suffix('.r00').exists()) or (
                current.suffix.lower() == '.zip' and current.with_suffix('.z01').exists())
            if real_ext and not is_volume and not current.name.lower().endswith(real_ext.lower()):
                target = current.with_suffix(real_ext)
                if target.exists():
                    raise RuntimeError("目標後綴文件已存在，請先處理同名文件")
                current.rename(target)
                current = target
            cleanup_error = ''
            source_snapshot = None
            if self.delete_source:
                try:
                    source_snapshot = self.archive_snapshot(current)
                except (OSError, ValueError) as error:
                    cleanup_error = f'來源清理未完成：{error}'
            output = self.extract(current)
            queue = deque((p, 2) for p in self._scan(output))
            issues = [cleanup_error] if cleanup_error else []
            while queue:
                self.check_cancel()
                inner, depth = queue.popleft()
                if depth > self.depth:
                    issues.append(f"達到 {self.depth} 層上限，保留 {inner.name}")
                    continue
                try:
                    self.notify(f"第 {depth} 層 · {inner.name}")
                    inner_snapshot = self.archive_snapshot(inner) if self.delete_inner else None
                    inner_output = self.extract(inner)
                    queue.extend((p, depth + 1) for p in self._scan(inner_output))
                    if self.delete_inner:
                        self.remove_archive(inner_snapshot)
                except Cancelled:
                    raise
                except Exception as error:
                    issues.append(f"{inner.name}: {error}")
            self.check_cancel()
            if self.delete_source and not issues and source_snapshot:
                try:
                    self.remove_archive(source_snapshot)
                except Cancelled:
                    raise
                except (OSError, ValueError) as error:
                    issues.append(f'來源清理未完成：{error}')
            result = Result(str(original), "partial" if issues else "success", str(output), "\n".join(issues), str(current))
            return result
        except Cancelled:
            result = Result(str(original), "cancelled", str(output or ""), "已取消；已完成的結果保留", str(current if output else original))
            return result
        except Exception as error:
            result = Result(str(original), "failed", str(output or ""), str(error), str(current if output else original))
            return result
        finally:
            if output is None and current != original and current.exists() and not original.exists():
                try:
                    current.rename(original)
                except OSError as error:
                    result.archive = str(current)
                    result.detail += f"\n原名還原失敗，原包保留在 {current}: {error}"
