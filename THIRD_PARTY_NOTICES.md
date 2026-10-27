# 第三方元件與授權

Auto7z 當前版本中由 JackyNgai 擁有著作權的程式碼自 2026-10-27 起採 MIT，見 LICENSE。第三方元件、二進位及其授權文件繼續依各自條款分發，不適用本專案的 MIT 授權。此前已發布的 GPL-3.0 副本仍可按原授權使用。

- CPython：PSF 等授權。發行包 resources/licenses/Python.txt 收錄實際建置執行環境的授權。來源：https://www.python.org/downloads/source/
- 7-Zip：原版 7z.exe／7z.dll，LGPL、BSD 與 unRAR 附加條款，見 licenses/7-Zip.txt 與 LGPL-3.0.txt。原始碼：https://www.7-zip.org/download.html
- PyInstaller：GPL 與打包例外。發行包 resources/licenses/PyInstaller.txt 包含實際使用版本原文。來源：https://github.com/pyinstaller/pyinstaller
- Vue、Element Plus 及 JavaScript 生產依賴：逐套件版本／授權原文收錄於 resources/licenses/JavaScript-dependencies.txt。來源：https://github.com/vuejs/core 、https://github.com/element-plus/element-plus
- Tauri、Rust鎖定依賴：版本／授權原文收錄於 resources/licenses/Rust-dependencies.txt。來源：https://github.com/tauri-apps/tauri 及各crate原始碼。
- WebView2、Windows .NET Framework：使用系統提供的執行環境，不隨便攜ZIP或單EXE內嵌分發。NSIS安裝器可能協助安裝WebView2，依微軟條款及網絡環境處理。

7.0不再包含PyQt、Qt、PyQt-Fluent-Widgets或WinRAR。使用者可選擇自行安裝的合法WinRAR路徑。打包腳本、版本鎖檔與單檔啟動器原始碼隨本專案公開，發行包中保留所有實際運行依賴的授權聲明。建置工具授權不等於其原始碼被內嵌至產品。

## MPL-2.0 元件的原始碼

Rust鎖定依賴中包含未修改的MPL-2.0元件：cssparser 0.37.0、cssparser-macros 0.7.1、dtoa-short 0.3.5、option-ext 0.2.0、selectors 0.38.0。其原始碼繼續採MPL-2.0，可在 https://crates.io/crates/<名稱>/<版本> 的「Download」取得原版套件，或使用下列版本固定的原始碼下載地址：

- https://crates.io/api/v1/crates/cssparser/0.37.0/download
- https://crates.io/api/v1/crates/cssparser-macros/0.7.1/download
- https://crates.io/api/v1/crates/dtoa-short/0.3.5/download
- https://crates.io/api/v1/crates/option-ext/0.2.0/download
- https://crates.io/api/v1/crates/selectors/0.38.0/download

發行包內 resources/licenses/Rust-dependencies.txt 保留對應許可原文。第三方元件的修改或再分發仍須遵守其原有條款。
