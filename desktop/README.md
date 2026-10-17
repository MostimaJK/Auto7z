# Auto7z Fluent

Microsoft `@fluentui/react-components` **9.74.9**、React **19.3.1**／TypeScript、Tauri **2.12.4**（CLI **2.12.3**）。透過私有 stdin/stdout JSON-lines 重用上層 `extraction.py`；沒有 HTTP 解壓服務、不載入 PyQt。Python／C++ 舊入口均保留。

## 啟動

根目錄執行 `Start_Auto7z_Fluent.bat`。存在 release 時直接啟動，否則使用開發模式；不自動安裝依賴、不發布。Windows 10／11 x64 需要 WebView2 Runtime。開發另需 Node.js、Rust stable MSVC、Visual Studio 2022 C++ 工作負載與 Windows SDK、Python 3.10+。優先使用根目錄 `.venv/Scripts/python.exe`，缺少時使用 PATH 的 Python。背景僅使用標準庫。

```powershell
cd desktop
npm ci
$env:PATH="$env:USERPROFILE/.cargo/bin;"+$env:PATH
npm run desktop
```

`npm run dev` 僅供瀏覽器版面預覽，沒有本機解壓能力，會清楚提示。

## 建置

```powershell
cd desktop
npm run build       # TypeScript + 前端正式建置
npm run package     # PyInstaller + Tauri release + NSIS
```

腳本使用既有 `.build-venv` 的 PyInstaller。新機先建立該虛擬環境並安裝 PyInstaller（根目錄 `requirements-build.txt` 亦包含它）。產物在 `src-tauri/target/release/`；安裝包在 `bundle/nsis/`。可攜執行時須一起保留 `resources/` 引擎、7-Zip 與授權文件，不能只複製主 EXE。WinRAR 不隨新套件散佈，請安裝合法版本後設定路徑。版本由 npm／Cargo lockfiles 鎖定；首次建置需要下載依賴。

打包腳本的授權收集使用 Python 3.11+ 的 `tomllib`。會收集現有生產 JavaScript 套件與 Cargo 鎖定套件的授權聲明，放入 resources/licenses。

## 功能與資料

- 同一佇列提供遞迴解壓、還原後綴並解壓、只改後綴。文件／資料夾拖入、原生多選；資料夾遞迴掃描，分卷只加入首卷。一般解壓只收支援的壓縮包，後綴模式接受其他文件；跳過符號連結與 `.auto7z-` 暫存目錄。
- 候選密碼按行或逗號分隔；僅保留本次工作階段。設定內含引擎路徑、遞迴深度、預檢逾時、停滯保護及成功後內層刪除。
- 取消等待所屬子進程退出，成功結果保留。Windows Job Object 在背景異常退出時回收後代進程。每次嘗試隔離暫存、同名結果另建目錄；外層原包保留。
- 重試略過成功項。部分完成／取消的還原後綴任務使用目前原包重試；重新解壓外層到新目錄，先前結果仍保留。
- 本輪文件完成數、結果狀態、目前活動分開顯示。核心沒有可靠位元組總量，使用 Fluent 不確定進度並明示未知，不顯示虛構百分比。
- 選取列可查看完整路徑、錯誤與結果；文字可選取複製。日誌保留最近 2,000 筆活動與引擎有界診斷，不宣稱完整收錄 7-Zip 原始輸出。
- Ctrl+O 加文件、Ctrl+Shift+O 加資料夾、Ctrl+Enter 開始；方向鍵移動文件列、空白鍵選取、Enter 查看。淺色／深色／跟隨系統。最小 640×480 邏輯像素；窄視窗詳情移至下方，內容獨立滾動。

設定：`%LOCALAPPDATA%/Auto7zFluent/settings.json`，首次在開發環境只讀匯入根目錄舊設定，不回寫舊版。佇列、結果紀錄與密碼只保留在目前工作階段；輸出文件實際保存在磁碟。清空佇列不刪磁碟文件。設定取消不保存。

## 測試

根目錄執行：

```powershell
./.venv/Scripts/python.exe -m unittest discover -s tests -v
python -m unittest discover -s desktop/tests -v
```

橋接測試使用真實 7-Zip 驗證批量重試、加密分卷、多密碼、遞迴部分結果、改名衝突與超過 260 字元路徑。取消案例為模擬耗時工作，但確實創建、取消和回收子進程；不等同大型壓縮包取消效能測試。實際視覺／互動檢查見 `design-notes.md`。

可重現版面診斷：啟動前為該進程設定 `AUTO7Z_VERIFY_SIZE=640x480`；`AUTO7Z_VERIFY_ZOOM=1.5` 可放大 WebView。這些選項不修改系統 DPI，不等同跨 DPI 顯示器實測。掃描同樣可取消，已加入項目保留。

## 架構選擇

Rust 層轉送限定 JSON 指令並提供原生選擇器；前端沒有通用 shell 能力。獨立 Python 進程在執行緒中處理 IO，以事件回報。關閉宿主時透過 EOF 合作取消，異常終止由 Windows Job Object 保護。

C++ 引擎也可復用，但目前 `--engine request response` 只在結束後回傳結果，仍需增補即時事件和外部取消協議。因此首版復用已獨立、有測試的 Python 核心。無法安裝 Rust 的機器可用建置套件；若環境禁止 WebView2，舊 Qt 入口是可行替代。

官方參考：[Fluent React](https://react.fluentui.dev/)、[Tauri 依賴](https://v2.tauri.app/start/prerequisites/)、[Tauri 事件](https://v2.tauri.app/develop/calling-frontend/)。
