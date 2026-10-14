# 第三方元件與授權

Auto7z 的公開原始碼與本次發布採用 GNU GPL v3（見 LICENSE）。

- CPython：PSF 等授權，完整聲明見 licenses/Python.txt；https://www.python.org/downloads/source/ 。
- 已安裝依賴的授權原文見 licenses/dependencies/。
- PyQt5：GPL v3；https://www.riverbankcomputing.com/software/pyqt/ ，原始碼 https://pypi.org/project/PyQt5/#files
- PyQt-Fluent-Widgets：GPL v3；https://github.com/zhiyiYo/PyQt-Fluent-Widgets
- Qt 5：LGPL v3 / GPL；https://download.qt.io/archive/qt/5.15/ ，授權全文見 licenses。
- C++ 版 Qt 6：LGPL v3 / GPL；https://download.qt.io/archive/qt/6.8/6.8.3/single/ 。使用動態程式庫，不需 Python。
- 7-Zip：LGPL 與附加 BSD / unRAR 條款，未修改的 7z.exe / 7z.dll；https://www.7-zip.org/ ，原始碼 https://www.7-zip.org/download.html 。授權全文見 licenses/7-Zip.txt。
- PyInstaller：GPL 與打包例外；https://pyinstaller.org/ 。

Release 不包含 WinRAR.exe；如需使用 WinRAR，請自行安裝合法版本並設定工具路徑。原始碼、重建腳本與發行套件均在本專案公開提供。資料夾版使用動態 Qt 程式庫，保留使用者替換相容程式庫的能力。
