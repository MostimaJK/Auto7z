from PyQt5.QtCore import QObject, pyqtSignal
from extraction import Engine


class ExtractionWorker(QObject):
    info_signal = pyqtSignal(str, str, int)
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(int)
    result_signal = pyqtSignal(object)
    activity_signal = pyqtSignal(str)

    def __init__(self, exe_7z_path, exe_rar_path, file_paths, passwords,
                 is_all_in_one=False, real_ext="", engine_mode="auto",
                 max_recursion_depth=20, delete_after_extract=False,
                 idle_timeout_seconds=0, timeout_7z_precheck=30, source_aliases=None, **legacy):
        super().__init__()
        self.file_paths = list(file_paths)
        self.real_ext = real_ext if is_all_in_one else ""
        self.engine = Engine(exe_7z_path, exe_rar_path, passwords, engine_mode,
                             max_recursion_depth, delete_after_extract,
                             idle_timeout_seconds, timeout_7z_precheck,
                             self.activity_signal.emit)
        self.results = []
        self.source_aliases = source_aliases or {}

    def cancel(self):
        # Called directly by GUI: Event is thread-safe; queued slots cannot run
        # while the worker is inside its extraction loop.
        self.engine.cancel()

    def run(self):
        successes = 0
        try:
            for index, source in enumerate(self.file_paths):
                if self.engine.cancelled.is_set():
                    break
                self.progress_signal.emit(int(index * 100 / len(self.file_paths)),
                                          f"文件隊列 {index + 1}/{len(self.file_paths)}")
                result = self.engine.process(source, self.real_ext)
                result.source = self.source_aliases.get(source, result.source)
                self.results.append(result)
                self.result_signal.emit(result)
                successes += result.status == "success"
                if result.status == "cancelled":
                    break
            if not self.engine.cancelled.is_set():
                self.progress_signal.emit(100, "文件隊列處理結束")
        except Exception as error:
            self.info_signal.emit("error", str(error), 5000)
        finally:
            self.finished_signal.emit(successes)
