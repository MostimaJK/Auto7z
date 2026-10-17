# Auto7z 6.1.0

## Element Plus／Tauri 試用版

新增獨立桌面介面在 `desktop/`，使用 Element Plus 2.14.7、Vue 3／TypeScript 與 Tauri 2，復用現有 Python 解壓核心。執行根目錄 **`Start_Auto7z_Element.bat`**；三種處理方式直接點選，候選密碼常駐，日誌與設定使用獨立頁面。設定支援內置或自訂解壓軟體路徑。依賴、開發啟動、建置及行為邊界見 [desktop/README.md](desktop/README.md)。舊 Python `Start_Auto7z.bat` 和 `Auto7zCpp/` 均保留；Fluent 原始碼保留於 `codex/fluent-tauri-desktop` 分支，既有 Fluent release 仍可用原 bat 比較。新版設定獨立保存，不覆寫舊設定。本次僅本地試用，未推送或發布。

Windows 桌面批量解壓助手，支持修改後綴、自動選擇 7-Zip / WinRAR、多密碼嘗試與多層遞歸解壓。

## 下載

[GitHub Releases v6.1.0](https://github.com/MostimaJK/Auto7z/releases/tag/v6.1.0)

- **Python Single**：單一 EXE，已內附依賴與 7-Zip；不需要安裝 Python。啟動時會解開內嵌依賴。
- **Python Portable**：ZIP 資料夾版，解壓後執行 Auto7z.exe，請保留 _internal；適合重視啟動速度。
- **C++ Portable**：獨立的 C++／Qt 6 版本，解壓後執行 Auto7zCpp.exe，保留同級 DLL 與 plugins。原始碼在 Auto7zCpp/。

本次套件適用 Windows 10／11 x64，附 SHA256SUMS.txt。只附帶 7-Zip，不附帶 WinRAR；需要 WinRAR 時可指定自行安裝的合法版本。設定檔保存在 EXE 同級，勿放在不可寫入的系統目錄。

## 6.1.0 效能調整

- 非預設頁面首次使用才建立，保持原導覽與功能。
- 子程序完成後立即喚醒等待，取消仍採有界等待；大量短任務不再固定每次等 150ms。
- 無密碼輸入跳過不影響嘗試順序的額外目錄預檢；有候選密碼時仍保留辨識。
- 獨立打包環境，排除預覽與不需要的 Qt／資料分析模組。
- 本機原始碼模式首幀五次中位數：一次建立所有頁面 0.897s、延遲建立 0.760s（約 15%）；不是冷開機、打包版或所有電腦的保證。原始數據見 artifacts/startup-benchmark.json。
- 保持逐檔排程以維持遞迴、密碼優先與取消的一致性；沒有盲目增加解壓並行。

## 本次修復

- **大文件持續等待**：取消無密碼 5 秒、有密碼 30～60 秒的總時長限制。目錄預檢默認等待 30 秒，超時後直接嘗試解壓。
- **可取消與可選停滯保護**：默認不自動停止。可選保護同時參考進程 CPU、工具輸出和文件寫入；0 表示關閉。慢盤、網絡盤建議關閉。
- **隔離每次嘗試**：每個密碼和引擎使用獨立臨時目錄，失敗只清理本次目錄；成功發佈到不重名目錄。取消只停止本次子進程。
- **真正的遞歸層級**：最外層爲第 1 層，同層多個包不消耗深度；保留內層原包時不會重複解壓。
- **結果與重試**：區分成功、部分完成、失敗與取消，保留隊列與錯誤詳情。重試跳過成功文件，部分完成從原包重新解壓到新目錄。
- **自動選擇引擎**：Auto 只需一個可用引擎；有兩個時嘗試備用引擎。當前任務中優先複用成功密碼，不保存密碼。
- **原包保留**：最外層原包始終保留，內層默認也保留。舊設置的刪除偏好繼續保留。內層只有自身成功解壓後才按設置刪除。
- **任務界面**：默認進入遞歸解壓，工具路徑可摺疊，文件隊列、實時活動、結果和底部操作明確。

## 啓動

當前工作區已建立 `.venv`。雙擊 `Start_Auto7z.bat`，或者在 PowerShell 中運行：

```powershell
.\.venv\Scripts\python.exe main.py
```

新電腦建議建立獨立環境：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

不要混裝 `PyQt-Fluent-Widgets` 與 `PyQt6-Fluent-Widgets`，兩者共享 `qfluentwidgets` 包名，會發生 Qt5 / Qt6 類型衝突。

程序查找打包資源、程序同級目錄和常見系統安裝目錄中的解壓工具，也可手動指定。`7z.dll` 應與 `7z.exe` 放在一起。

## 使用

1. 拖入或選擇文件，使用「自動選擇」引擎。
2. 如有密碼，每行一個，或用逗號分隔。
3. 點擊「開始解壓」。進度條表示文件隊列進度，活動文本顯示當前文件、引擎、候選和已用時；不估算剩餘時間。
4. 完成後查看每個文件的狀態與詳情。「打開結果目錄」打開最近一個可用結果目錄。
5. 補充密碼或修正路徑後重試未成功文件。已完成結果保留，重試產生新目錄，不覆蓋舊結果。

### 進度與佈局

主界面固定使用 Apple 啓發的細藍色進度條，數值直接更新。已移除樣式選擇、動態開關和預覽入口。進度百分比按隊列文件數計算，不代表單個壓縮包的字節進度或成功率。

文件隊列與清空操作放在同一區域；底部保留狀態、進度、結果和開始／取消操作。空閒時只顯示「準備就緒」，運行時顯示當前活動，結束後顯示結果統計；詳細錯誤可在「查看結果」中查看。歷史配色探索保留在 `progress-inspiration.md`，不參與主界面操作。

還原後綴聯動成功時保留還原後的後綴；最外層失敗或取消且尚無結果時，嘗試還原原名。同名目標存在時拒絕改名。

取消保留已發佈的結果，清理當前未完成嘗試。若發佈結果時移動失敗，保留 `.auto7z-*` 臨時目錄，並在詳情中提示位置。

遞歸識別 zip、rar、7z、tar、gz、bz2、xz、tgz，以及常見 `.7z.001` / `.zip.001` 和 `.part1.rar` 入口；分卷需齊全，遞歸掃描忽略後續卷。只有標準壓縮後綴的內層文件會自動遞歸處理。

## 設置

設置保存到項目目錄或打包 EXE 同級目錄的 `settings.json`，以原子替換方式保存。舊總時長限制自動停用。運行中的任務使用啓動時的設置。

停滯保護是啓發式，不能證明卡死。建議保持默認的 0，並使用取消按鈕控制任務。

## 驗證

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

測試覆蓋密碼輪詢、文件名加密、中文路徑、遞歸層級、保留內層原包、損壞文件、輸出衝突、超過舊超時閾值、取消進程隔離、設置遷移與界面重試。測試樣本均放在臨時目錄。

目前介面見 `artifacts/apple-final.png`、`artifacts/apple-final-compact.png`，設計記錄見 `design-notes.md`。尚未使用用戶數十 GB 實際壓縮包做壓力測試。

## 打包

安裝 PyInstaller 後：

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconsole --onedir --icon=Auto7z.ico --name=Auto7z --add-binary "7z.exe;." --add-binary "7z.dll;." main.py
```

本次未生成發佈 EXE。分發所附工具前需覈對各工具許可。
