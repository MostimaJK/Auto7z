# 第三方元件與授權

Auto7z 公開原始碼及發行採 GNU GPL v3，見 LICENSE。

- CPython：PSF 等授權。發行包 resources/licenses/Python.txt 收錄實際建置執行環境的授權。來源：https://www.python.org/downloads/source/
- 7-Zip：原版 7z.exe／7z.dll，LGPL、BSD 與 unRAR 附加條款，見 licenses/7-Zip.txt 與 LGPL-3.0.txt。原始碼：https://www.7-zip.org/download.html
- PyInstaller：GPL 與打包例外。發行包 resources/licenses/PyInstaller.txt 包含實際使用版本原文。來源：https://github.com/pyinstaller/pyinstaller
- Vue、Element Plus 及 JavaScript 生產依賴：逐套件版本／授權原文收錄於 resources/licenses/JavaScript-dependencies.txt。來源：https://github.com/vuejs/core 、https://github.com/element-plus/element-plus
- Tauri、Rust鎖定依賴：版本／授權原文收錄於 resources/licenses/Rust-dependencies.txt。來源：https://github.com/tauri-apps/tauri 及各crate原始碼。
- WebView2、Windows .NET Framework：使用系統提供的執行環境，不隨便攜ZIP或單EXE內嵌分發。NSIS安裝器可能協助安裝WebView2，依微軟條款及網絡環境處理。

7.0不再包含PyQt、Qt、PyQt-Fluent-Widgets或WinRAR。使用者可選擇自行安裝的合法WinRAR路徑。打包腳本、版本鎖檔與單檔啟動器原始碼隨本專案公開，發行包中保留所有實際運行依賴的授權聲明。建置工具授權不等於其原始碼被內嵌至產品。
