# Auto7z Element

Element Plus **2.14.7**、Vue **3.5.44**／TypeScript、Tauri **2.12.4**（CLI **2.12.3**）。Element Plus 是 Vue 組件庫，因此本輪將 React 前端改為 Vue 3；Tauri 宿主與成熟的 `extraction.py` 保留。後台不載入 PyQt。

## 啟動

根目錄執行 **Start_Auto7z_Element.bat**，優先啟動本地 release，其次 debug，沒有編譯檔時進入開發模式。debug 需要現有 Python 環境；release 帶獨立後台。Windows 10／11 x64 需要 WebView2 Runtime。腳本不自動安裝依賴、不發布。

開發需要 Node.js、Rust stable MSVC、Visual Studio C++ 工作負載與 Windows SDK、Python 3.10+。後台優先使用根目錄 `.venv/Scripts/python.exe`，缺少時使用 PATH 的 Python；僅使用標準庫。

```powershell
cd desktop
npm ci
$env:PATH="$env:USERPROFILE/.cargo/bin;"+$env:PATH
npm run desktop
```

`npm run dev` 只供瀏覽器版面預覽，會提示使用桌面入口處理文件。

## 建置

```powershell
cd desktop
npm run build                       # Vue TypeScript 檢查與前端建置
npm run tauri -- build --debug --no-bundle
npm run package                     # PyInstaller、Tauri release、NSIS 本地安裝包
```

打包腳本使用根目錄 `.build-venv` 的 PyInstaller，授權收集需 Python 3.11+。新機先建立該虛擬環境並安裝 PyInstaller（`requirements-build.txt` 亦包含它）。產物在 `src-tauri/target/release/auto7z-element.exe`，安裝包在 `bundle/nsis/`。可攜執行時保留同級 resources 內的後台、7-Zip 與授權文件；不要只複製主 EXE。WinRAR 不隨新套件散佈，請使用自行安裝的合法版本。版本鎖在 npm／Cargo lockfiles。

## 使用與設定

- 工作區上方直接選擇遞迴解壓、修改後綴、改後綴並解壓。三段選擇器為保留 Element Plus 單選語義的液態玻璃視覺改編，具有滑動、形變、按壓與指標高光；尊重減少動態效果／透明效果偏好。它是 Windows WebView 實作，不是 Apple 原生 Liquid Glass。後兩者可輸入目標後綴。切換已完成的佇列會提示清空紀錄，磁碟文件保留。
- 支援文件／資料夾拖入與原生選擇器。資料夾遞迴掃描，分卷只加入首卷；一般解壓只收支援壓縮包，後綴模式接受其他文件。跳過符號連結與 `.auto7z-` 暫存目錄。
- 候選密碼在兩個解壓模式常駐，每行或逗號分隔，僅留在本次工作階段。單純改後綴不顯示密碼。
- 文件完成數、目前活動與結果分開顯示。7-Zip 的 `-bsp1` 實際回報驅動目前壓縮包的本次解壓進度條，直接更新、不做進度彈性補間；不是整批百分比，也不估算已處理位元組或剩餘時間。內層包、密碼重試、引擎切換會重置範圍；預檢、WinRAR 或工具未提供數據時顯示不確定活動，不虛構數字。
- 取消管理所屬子進程並保留成功結果；重試略過成功項。部分完成會從目前原包重新解壓至新目錄，並非續傳。外層原包保留，同名結果另建目錄。
- 點擊文件名稱查看完整來源、結果與錯誤，可選取複製及開啟結果目錄。日誌在獨立頁，可選取／整份複製，保留最近 2,000 筆有界活動與診斷，並非全部 7-Zip 原始輸出。
- 設定在獨立頁：選內置 7-Zip 或自訂執行檔，選填 WinRAR；提供原生瀏覽與路徑存在性檢查。檢查不等於驗證軟體版本或執行相容性，執行失敗會於任務結果顯示。
- 設定可調遞迴深度、預檢逾時、停滯保護、內層刪除及淺／深／系統主題。先儲存才套用，工作中不能修改；未儲存離開有提示。
- Ctrl+O 加文件、Ctrl+Shift+O 加資料夾、Ctrl+Enter 開始；Tab 切換控件、方向鍵選單選按鈕，文件名稱按鈕可鍵盤開啟詳情。

新版設定由 Tauri app_config_dir 指定，Windows 為 `%APPDATA%/local.auto7z.element/settings.json`。首次只讀匯入根目錄舊設定，之後獨立原子保存。舊 Python、C++ 與 Fluent 設定不覆寫。佇列、密碼與日誌不跨啟動保存；清空佇列不刪磁碟文件。

## 保留舊版與回退

本輪分支 `codex/element-plus-desktop`；前一版 Fluent 原始碼在 `codex/fluent-tauri-desktop`。既有 `Start_Auto7z_Fluent.bat` 可啟動原 Fluent release；它的開發後備入口使用目前 checkout 的前端，欲開發 Fluent 請先切回該分支。原 `Start_Auto7z.bat`、Python 模組及 `Auto7zCpp/` 保留。

## 架構與測試

Vue → Tauri 限定 JSON 指令 → 獨立 Python 後台 → 現有 Engine → 7-Zip／WinRAR。掃描與解壓在後台執行緒執行，stdin 仍可接收取消。關閉宿主透過 EOF 合作取消；Windows Job Object 在宿主異常結束時回收後代進程。C++ 引擎目前結束後才回傳結果，故先復用已有即時回報與取消的 Python 核心。

```powershell
python -m unittest discover -s desktop/tests -v
./.venv/Scripts/python.exe -m unittest discover -s tests -v
```

橋接測試包含真實加密分卷／多密碼、批量重試、遞迴部分結果、後綴衝突、超過 260 字元路徑、工具路徑檢查與設定隔離。取消單元案例使用模擬耗時 extractor，但創建和回收的子進程是真實的。原生視覺與真實解壓檢查見 `design-notes.md`。

診斷選項：`AUTO7Z_VERIFY_SIZE=640x480` 指定測試窗口；`AUTO7Z_VERIFY_ZOOM=2` 放大 WebView，不修改系統 DPI，不等同跨 DPI 顯示器實測。

官方參考：[Element Plus](https://element-plus.org/en-US/guide/installation.html)、[Tauri prerequisites](https://v2.tauri.app/start/prerequisites/)。
