# Auto7zCpp 6.1.0

Auto7z 的獨立 C++17／Qt 6 Widgets 版本，原始碼及可攜式執行檔不需要 Python。保留改後綴、遞歸解壓、改後綴解壓、設置四個頁面的分組、操作流程、繁體中文、Password 欄位及 Apple 啟發細藍色進度條。Qt 6 原生控件與視窗裝飾會有細節差異，不宣稱與 Qt5 Fluent 控件逐像素一致。

## 使用

解壓 C++ Portable 套件後執行 `Auto7zCpp.exe`，保留 DLL、platforms、translations 與 licenses 資料夾。已附帶 7-Zip；WinRAR 需另行安裝或指定合法版本路徑。設定保存在 EXE 同級的 `settings.json`，不儲存 Password。

- 候選密碼輪詢，批次優先復用成功密碼。
- 無密碼輸入直接解壓，省略不會改變嘗試順序的預檢。
- 解壓不限總時長；可取消與可選 CPU／輸出／文件活動停滯保護。
- 每次嘗試獨立臨時目錄、衝突另建目錄、失敗清理僅限本次目錄。
- 真實遞迴深度、分捲入口識別、保留原包；內層刪除僅限成功結果。
- 成功／部分完成／失敗／取消結果保留；重試跳過成功項，聯動從還原後原包重試。
- 即時佇列百分比按檔案數計算，不等於單檔位元組進度或成功率。
- 非預設頁面延遲建立；背景解壓不阻塞介面。

## 建置

Windows 10／11 x64，Visual Studio 2022 C++ 工作負載、CMake 3.21+、Qt 6.5+ MSVC x64 動態版本。本次使用 Qt 6.8.3／MSVC 2022。

```powershell
./build.ps1 -QtDirectory C:/Qt/6.8.3/msvc2022_64
```

可用 `-CMake` 指定 cmake.exe 完整路徑。腳本採用 windeployqt 並附帶 MSVC app-local DLL；不使用靜態 Qt。WinRAR 不隨包散佈。

## 驗證

```powershell
$env:PATH="C:/Qt/6.8.3/msvc2022_64/bin;"+$env:PATH
$env:AUTO7Z_TEST_7Z=(Resolve-Path ../7z.exe).Path
./build/Release/engine_tests.exe
./build/Release/ui_tests.exe
python tests/test_parity.py ./dist/Auto7zCpp.exe -v
```

測試工具可用 `--engine request.json response.json` 直接驗證 C++ 引擎；`--snapshot image.png 1` 擷取頁面（0=改後綴，1=解壓，2=聯動，3=設置）。正常使用不需要這些參數。速度取決於解壓引擎、磁碟與任務；C++ 移植不會直接加速相同的 7-Zip 演算法。

授權與第三方說明見上層 LICENSE、THIRD_PARTY_NOTICES.md；Qt 6 原始碼：https://download.qt.io/archive/qt/6.8/6.8.3/single/ 。
