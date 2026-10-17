"""Private JSON-lines protocol. No network listener and no Qt dependency."""
import ctypes
import json
import os
import re
import sys
import tempfile
import threading
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] if not getattr(sys, "frozen", False) else Path(sys.executable).parent
sys.path.insert(0, str(ROOT))
from extraction import Engine


def own_process_job():
    """If this backend dies, Windows also terminates only its descendant processes."""
    if os.name != "nt":
        return None
    from ctypes import wintypes as w
    class Basic(ctypes.Structure):
        _fields_ = [("processTime", ctypes.c_int64), ("jobTime", ctypes.c_int64),
                    ("flags", w.DWORD), ("min", ctypes.c_size_t), ("max", ctypes.c_size_t),
                    ("active", w.DWORD), ("affinity", ctypes.c_size_t), ("priority", w.DWORD), ("scheduling", w.DWORD)]
    class Io(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in ("readOps", "writeOps", "otherOps", "readBytes", "writeBytes", "otherBytes")]
    class Extended(ctypes.Structure):
        _fields_ = [("basic", Basic), ("io", Io), ("processMemory", ctypes.c_size_t),
                    ("jobMemory", ctypes.c_size_t), ("peakProcess", ctypes.c_size_t), ("peakJob", ctypes.c_size_t)]
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateJobObjectW.restype = w.HANDLE
    api.CreateJobObjectW.argtypes = [ctypes.c_void_p, w.LPCWSTR]
    api.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
    api.GetCurrentProcess.restype = w.HANDLE
    api.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    handle = api.CreateJobObjectW(None, None)
    info = Extended()
    info.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not handle or not api.SetInformationJobObject(handle, 9, ctypes.byref(info), ctypes.sizeof(info)) or not api.AssignProcessToJobObject(handle, api.GetCurrentProcess()):
        raise OSError(ctypes.get_last_error(), "無法建立解壓進程保護")
    return handle  # must stay open for the lifetime of the backend


DEFAULTS = dict(path_7z="", path_rar="", max_recursion_depth=20,
                idle_timeout_seconds=0, timeout_7z_precheck=30,
                delete_after_extract=False, theme="system")


class Bridge:
    def __init__(self, emit, config=None):
        self.emit = emit
        self.config = config or Path(os.environ.get("AUTO7Z_CONFIG_DIR", str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Auto7zFluent"))) / "settings.json"
        self.settings = DEFAULTS.copy()
        self.warning = ""
        # Existing configuration is imported read-only; writes use a separate file.
        source = self.config if self.config.exists() else ROOT / "settings.json"
        if source.exists():
            try:
                self.settings.update(self.validate(json.loads(source.read_text(encoding="utf-8"))))
            except Exception as e:
                self.warning = f"設定讀取失敗，已使用預設值：{e}"
        for key, executable, subdir in (("path_7z", "7z.exe", "7-Zip"), ("path_rar", "WinRAR.exe", "WinRAR")):
            if not self.settings[key]:
                candidates = [ROOT / executable, Path(os.environ.get("ProgramFiles", "C:/Program Files")) / subdir / executable]
                self.settings[key] = next((str(p) for p in candidates if p.is_file()), "")
        self.rows = []
        self.busy = False
        self.scanning = False
        self.engine = None
        self.thread = None
        self.lock = threading.RLock()
        self.sequence = 0
        self.activity = "準備就緒"
        self.completed = self.total = 0
        self.current = None
        self.stopping = False
        self.progress = None
        self.scan_cancel = threading.Event()

    @staticmethod
    def validate(data):
        if not isinstance(data, dict):
            raise ValueError("設定必須是物件")
        out = DEFAULTS.copy()
        for key, low, high in (("max_recursion_depth", 1, 100), ("idle_timeout_seconds", 0, 86400), ("timeout_7z_precheck", 3, 300)):
            value = data.get(key, out[key])
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{key} 必須介於 {low} 與 {high}")
            out[key] = value
        for key in ("path_7z", "path_rar"):
            if not isinstance(data.get(key, ""), str):
                raise ValueError("工具路徑必須是文字")
            out[key] = data.get(key, "")
        if type(data.get("delete_after_extract", False)) is not bool:
            raise ValueError("內層刪除選項無效")
        out["delete_after_extract"] = data.get("delete_after_extract", False)
        out["theme"] = data.get("theme", "system")
        if out["theme"] not in ("system", "light", "dark"):
            raise ValueError("主題無效")
        return out

    def state(self):
        with self.lock:
            return dict(rows=[dict(r) for r in self.rows], busy=self.busy, scanning=self.scanning,
                        activity=self.activity, current=self.current, stopping=self.stopping,
                        completed=self.completed, total=self.total, progress=self.progress)

    def publish(self):
        self.emit(dict(event="state", data=self.state()))

    def log(self, message):
        self.emit(dict(event="log", data=str(message)))

    def notify(self, text):
        with self.lock:
            self.activity = text
        self.emit(dict(event="activity", data=text))
        self.log(text)

    def report_progress(self, data):
        with self.lock:
            self.progress = data
        self.emit(dict(event="progress", data=data))

    def idle(self):
        if self.busy or self.scanning:
            raise ValueError("請等待目前工作完成或先取消")

    def add(self, paths, include_all=False):
        self.idle()
        if not isinstance(paths, list) or not paths or len(paths) > 10000 or any(not isinstance(p, str) for p in paths):
            raise ValueError("請選擇文件或資料夾")
        self.scanning = True
        self.scan_cancel.clear()
        self.stopping = False
        self.activity = "正在掃描文件…"
        self.publish()
        def scan():
            added = skipped = 0
            try:
                known = {os.path.normcase(r["source"]) for r in self.rows}
                for raw in paths:
                    if self.scan_cancel.is_set():
                        break
                    path = Path(raw).absolute()
                    if path.is_symlink():
                        self.log(f"略過符號連結：{path}")
                        skipped += 1
                        continue
                    if not path.exists():
                        self.log(f"路徑不存在：{path}")
                        skipped += 1
                        continue
                    candidates = [path]
                    if path.is_dir():
                        candidates = self.walk_files(path, self.scan_cancel)
                    for p in candidates:
                        if self.scan_cancel.is_set():
                            break
                        # Secondary volumes are never independent tasks, even for disguised-input mode.
                        secondary = bool(re.search(r"\.(?:7z|zip)\.(?!001$)\d{3}$|\.part(?!0*1\.rar$)\d+\.rar$|\.[rz]\d{2}$", p.name, re.I))
                        if secondary or (not include_all and not Engine.is_archive(p)):
                            self.log(f"略過{'非首卷' if secondary else '不支援的後綴'}：{p}")
                            skipped += 1
                            continue
                        key = os.path.normcase(str(p))
                        if key in known:
                            continue
                        known.add(key)
                        self.sequence += 1
                        with self.lock:
                            self.rows.append(dict(id=str(self.sequence), source=str(p), size=p.stat().st_size,
                                                  status="pending", output="", detail="", archive=""))
                        added += 1
                self.log(f"已加入 {added} 個文件；略過 {skipped} 個非入口或不適用文件")
                if not added and skipped and not self.scan_cancel.is_set():
                    self.emit(dict(event="error", data="未加入可處理文件；請選擇壓縮包首卷，偽裝後綴請先切換處理方式。詳情見工作日誌。"))
            except Exception as e:
                self.emit(dict(event="error", data=f"掃描失敗：{e}"))
            finally:
                self.scanning = False
                self.stopping = False
                self.activity = "掃描已取消；已加入文件保留" if self.scan_cancel.is_set() else "準備就緒"
                self.publish()
        self.thread = threading.Thread(target=scan)
        self.thread.start()

    @staticmethod
    def walk_files(folder, stop=None):
        for root, dirs, files in os.walk(folder, followlinks=False):
            if stop and stop.is_set():
                return
            dirs[:] = [d for d in dirs if not Path(root, d).is_symlink() and not d.startswith(".auto7z-")]
            for name in sorted(files):
                if stop and stop.is_set():
                    return
                p = Path(root, name)
                if not p.is_symlink():
                    yield p

    def start(self, mode="extract", extension="", passwords=None, engine_mode="auto"):
        self.idle()
        if mode not in ("extract", "rename", "restore") or engine_mode not in ("auto", "7z", "winrar"):
            raise ValueError("處理方式或引擎無效")
        if mode != "extract" and not re.fullmatch(r"\.[A-Za-z0-9]{1,12}(?:\.[A-Za-z0-9]{1,12}){0,2}", extension):
            raise ValueError("後綴須以點開頭，每段限 1–12 個英數字，最多三段（例如 .zip、.tar.gz）")
        if not isinstance(passwords or [], list) or any(not isinstance(p, str) for p in (passwords or [])):
            raise ValueError("密碼格式無效")
        sources = [r for r in self.rows if r["status"] != "success"]
        if not sources:
            raise ValueError("沒有待處理文件")
        s = self.settings.copy()
        self.engine = Engine(s["path_7z"], s["path_rar"], passwords or [], engine_mode,
                             s["max_recursion_depth"], s["delete_after_extract"],
                             s["idle_timeout_seconds"], s["timeout_7z_precheck"], self.notify, self.report_progress)
        if mode != "rename" and not self.engine._tool_order(Path(sources[0]["source"])):
            raise ValueError("找不到可用解壓引擎，請在設定中指定工具路徑")
        self.busy, self.stopping = True, False
        self.progress = None
        self.completed, self.total = 0, len(sources)
        self.publish()
        def run():
            try:
                for row in sources:
                    if self.engine.cancelled.is_set():
                        break
                    with self.lock:
                        row["status"] = "running"
                        self.current = row["id"]
                        self.progress = None
                    self.publish()
                    # On partial/cancelled restore, the renamed archive remains the retry source.
                    source = row["archive"] or row["source"]
                    if mode == "rename":
                        try:
                            self.engine.check_cancel()
                            path = Path(source)
                            target = path if path.name.lower().endswith(extension.lower()) else path.with_suffix(extension)
                            if target != path:
                                if target.exists():
                                    raise ValueError("目標文件已存在，未覆蓋")
                                path.rename(target)
                            result = dict(status="success", output="", detail=f"已改名：{target}", archive=str(target))
                        except Exception as e:
                            result = dict(status="cancelled" if self.engine.cancelled.is_set() else "failed", output="", detail=str(e), archive=source)
                    else:
                        result = asdict(self.engine.process(source, extension if mode == "restore" else ""))
                        result.pop("source")
                    with self.lock:
                        # A retry failure must not hide an earlier completed outer result.
                        if not result["output"] and row["output"]:
                            result["output"] = row["output"]
                        row.update(result)
                        self.completed += 1
                    self.log(f"{row['status']} · {row['source']}\n{row['output']}\n{row['detail']}")
                    self.publish()
                    if row["status"] == "cancelled":
                        break
            except Exception as e:
                with self.lock:
                    for row in sources:
                        if row["status"] == "running":
                            row.update(status="failed", detail=str(e))
                self.emit(dict(event="error", data=str(e)))
            finally:
                with self.lock:
                    self.busy = self.stopping = False
                    self.current = None
                    self.activity = "已取消；成功結果保留" if self.engine.cancelled.is_set() else "處理完成"
                self.publish()
        self.thread = threading.Thread(target=run)
        self.thread.start()

    def dispatch(self, op, args):
        if op == "init":
            return dict(settings=self.settings, state=self.state(), warning=self.warning,
                        tools=dict(bundled_7z=str(ROOT / "7z.exe"), bundled_7z_exists=(ROOT / "7z.exe").is_file(), settings_file=str(self.config)))
        if op == "check_tools":
            return {key: bool(isinstance(args.get(key), str) and args[key] and Path(args[key]).is_file()) for key in ("path_7z", "path_rar")}
        if op == "add":
            self.add(**args)
        elif op == "start":
            self.start(**args)
        elif op == "cancel":
            if self.scanning:
                self.stopping = True
                self.scan_cancel.set()
                self.publish()
            elif self.busy:
                self.stopping = True
                self.engine.cancel()
                self.notify("正在取消，等待解壓進程退出…")
                self.publish()
        elif op == "remove":
            self.idle()
            self.rows = [r for r in self.rows if r["id"] not in args["ids"]]
            self.completed = self.total = 0
            self.publish()
        elif op == "save":
            self.idle()
            data = self.validate(args)
            self.config.parent.mkdir(parents=True, exist_ok=True)
            name = None
            try:
                with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.config.parent, delete=False) as f:
                    name = f.name
                    json.dump(data, f, ensure_ascii=False, indent=2)
                os.replace(name, self.config)
            finally:
                if name and Path(name).exists():
                    Path(name).unlink()
            self.settings = data
            return data
        elif op == "open":
            row = next(r for r in self.rows if r["id"] == args["id"])
            path = Path(row["output"]) if row["output"] else Path(row["archive"] or row["source"]).parent
            if not path.is_dir():
                raise ValueError(f"結果目錄不存在：{path}")
            os.startfile(path)
        else:
            raise ValueError("不支援的操作")
        return None

    def shutdown(self):
        self.scan_cancel.set()
        if self.engine:
            self.engine.cancel()
        if self.thread:
            self.thread.join()


def main():
    # Rust writes UTF-8 even when Windows' legacy ANSI code page differs.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    job = own_process_job()
    output_lock = threading.Lock()
    def emit(message):
        with output_lock:
            print(json.dumps(message, ensure_ascii=True), flush=True)
    bridge = Bridge(emit)
    try:
        for line in sys.stdin:
            request = {}
            try:
                request = json.loads(line)
                value = bridge.dispatch(request["op"], request.get("args", {}))
                emit(dict(id=request["id"], ok=True, data=value))
            except Exception as e:
                emit(dict(id=request.get("id"), ok=False, error=str(e)))
    finally:
        bridge.shutdown()
    # Do not close job explicitly while self is a member; OS releases it at exit.
    _ = job


if __name__ == "__main__":
    main()
