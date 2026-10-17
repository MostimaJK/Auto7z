# Fluent 重構記錄

## 檢查與方向

已讀本機最新安裝 `uiux-product-designer` v2.7.0。未找到適用 AGENTS.md。檢查了 Python GUI、獨立 extraction.py／worker、C++ Qt 引擎與 CLI，以及兩套測試。

基線來自現有 `artifacts/apple-final.png` 及來源碼：

1. 大拖入區與空列表分開佔位，空狀態操作沒有成組置中。
2. 密碼常駐大區域，擠壓工作列表。
3. 三種流程分散在頁面，不利於同一批文件處理與比較。
4. 結果集中在額外文字區，列表缺少路徑／大小／狀態的直接對照。
5. 文件數百分比容易被誤認為位元組進度，且原介面不支援完整明暗外觀。

採用使用者指定 Fluent UI React v9；不套用技能的預設 Material／Apple 視覺。沿用安靜、清楚、工作內容優先的偏好，無 Dashboard、KPI 卡或裝飾圖。官方 webLightTheme／webDarkTheme 語意 tokens 決定背景、文字、選取、焦點與狀態；品牌藍用於主操作。4／8px 間距、原生 Fluent 控件圓角，內文 14px，繁體中文優先 Microsoft JhengHei UI 字體。路徑換行，全文可選取；不靠縮字或省略號掩蓋路徑。

單一列表工作區，模式與引擎在上方；密碼、日誌展開，設定使用 Fluent Dialog。空狀態將圖示、說明、主入口和幫助居中成組；有內容時入口移到隊列工具列。選取一列才出現結果詳情，窄視窗移到下方。狀態列分開本輪完成數、目前活動與未知位元組進度，不使用計時百分比或彈性插值。

## 參考證據

技能本機索引未配置；另從使用者已有壓縮參考庫讀取並實際打開三張圖片，留在 ignored artifacts/fluent-references，未加入產品或公開文件：

- Attio web Aug 2024 0：頁面下方可見表格與就近工具列，採用列表優先；上方為行銷頁，不作工作台尺寸依據。
- Figma web Jul 2025 0：下方可見主要工作面與右側屬性，採用選中內容的上下文詳情；不複製三欄畫布、品牌或宣傳區。
- Spotify web Dec 2024 0：深色階層與主要內容／持續底部區域可分辨；只參考明暗表面層級，不繼承音樂卡片或播放列。

以上是直接從 zip 檔取得的圖片，沒有冒稱匹配 UI3487 等索引 ID。主要組件規範仍以 Microsoft 官方 Fluent 套件為準。

## 架構與保留能力

React／TypeScript → Tauri command → 獨立 Python JSON-lines 後台 → 原有 extraction.Engine → 7z／WinRAR。Python 後台不 import PyQt，Rust 不提供通用 shell 操作。以執行緒處理掃描與佇列，標準輸入仍可接收取消。每個引擎進程合作終止；背景程序的 Windows Job Object 保護異常宿主退出。新設定獨立原子寫入，舊配置只讀；不改動舊 Python／C++ 入口及使用者資料。

保留批量、改後綴、多密碼、遞迴、分卷、工具路徑、深度、預檢、停滯保護、內層保留／刪除、取消、重試、結果與可複製日誌。成功項跳過重試，失敗改名自動回復由原引擎負責。部分完成重試重新解壓外層至新目錄，保留舊結果；不承諾從內層進度續傳。

## 已完成檢查

- Python 原版 21 項測試全部通過（含真實 7-Zip／WinRAR）。
- C++ 引擎 7 項、UI 4 項通過。最初 UI 測試啟動缺 Qt plugin path，曾彈錯誤；指定該進程的 QT_PLUGIN_PATH／QT_QPA_PLATFORM_PLUGIN_PATH 後通過，沒有改動系統 Qt 設定或舊版代碼。
- 新後台 12 項測試通過：真實加密分卷與多密碼、批次失敗重試、部分完成後改名來源重試、資料夾首卷掃描、同名保護、原子設定、超過 260 字元路徑、協議 EOF、原生 UTF-8 路徑傳輸、可取消掃描、Windows Job 異常退出回收。
- 取消案例是模擬耗時 extractor，但實際創建並回收子進程，驗證既有成功結果保留；不當作真實大型壓縮包的效能證據。
- PyInstaller 獨立後台已建置並用 JSON init／EOF 真實啟動，確認附帶 7z 路徑。
- TypeScript／Vite 正式建置通過。實際瀏覽器預覽已檢查置中空狀態，預覽中禁用本機功能並提示桌面入口。

## 原生與打包檢查

- Rust stable 1.99.1／MSVC，Tauri Rust 2.12.4／CLI 2.12.3 實際 release 編譯並產生 NSIS，本機未發現宿主不相容。
- 原生 Windows 選擇器：Ctrl+O 多選、Ctrl+Shift+O 選資料夾；真實批量 4 項得 3 成功／1 損壞失敗，第二個候選密碼解開加密包、嵌套內容已核對。重試本輪只有 1 項，未重建成功結果。
- 打包版以獨立測試設定啟動，確認路徑指向隨包 resources/7z.exe，真實選取繁體中文空格文件並成功遞迴解壓；開啟結果目錄已由 Explorer 視窗確認。
- 明暗 Fluent 外觀與原生標題欄已檢查。設定 Dialog 與 Escape 關閉、只在本次階段保留密碼／結果。短窗口檢查後，空隊列不顯示篩選列；窄工作區改單一捲動；較次要的大小欄在窄窗口隱藏，全文路徑仍可取得。
- 200% WebView 放大（1280×960 原生窗口、約 640×480 CSS 工作面）已實際檢查：空狀態成組置中、佇列可讀、開始／取消／重試保持可見。截圖 `artifacts/fluent-200-percent.png`。
- 在打包版實際解壓 104,952,022 bytes、12,000 個文件的 ZIP，運行中以介面取消；回到已取消／重試狀態後確認沒有該任務的 7z.exe，沒有 `.auto7z-*` 暫存目錄，未發布未完成結果，先前成功結果仍存在。截圖 `artifacts/fluent-real-cancel.png`。這是特定本機樣本的功能驗證，不宣稱取消時延或效能基準。
- 已計算兩種官方主題的正文／輔助文字對表面與畫布、選取文字、主按鈕文字共 10 組固色對比，全部超過 4.5:1；不將它當作完整無障礙認證。
- 依賴版本由 package-lock／Cargo.lock 鎖定，JavaScript／Rust 授權收集隨 resources 打包。未自動推送、安裝或發布 Release。
- 最終 `Start_Auto7z_Fluent.bat` 已實際啟動 release，保留原生窗口供試用；前端開發伺服器已停止。最終淺／深色截圖為 `artifacts/fluent-final-light.png`、`artifacts/fluent-final-dark.png`。NSIS 本機產物約 10.85 MiB。

佇列／結果紀錄僅保留本次工作階段；日誌最近 2,000 筆。位元組進度仍未知，未偽造。跨顯示器實際 DPI 切換與原生拖放尚未列為已驗證；縮放診斷不等同系統 DPI 實測。NSIS 已建置，不自動安裝到使用者系統。

## 2026-10-18 小範圍視覺修訂

使用者指出預設控件形態過於方正、原生 Select 彈層陳舊。本輪先提供可比較的獨立預覽，不覆蓋先前 release；入口為根目錄 `Preview_Auto7z_Fluent.bat`（debug 原生宿主，仍接真實 Python 後台，設定隔離至 artifacts/fluent-refinement-profile）。

- 處理方式、引擎、設定外觀統一使用官方 Dropdown／Option，保留受控值、選中勾選、方向鍵與 Enter 選擇、Escape 關閉；不再使用原生 Select 彈層。
- 以 Fluent tokens 做主題化：控件 10px、彈層 14px、主要表面 18px；選項 8px，柔和品牌選中底色。這是 Auto7z 的形態調整，不冒稱 Fluent 原始預設值。
- 配置集中於隊列標題旁，固定標籤放在控件上方；移除無功能的 Fluent 標籤。空狀態圖示、標題與操作仍成組置中，底部狀態改成較輕的內嵌表面。
- 未修改解壓核心、橋接協議或隊列行為，未安裝新依賴。
- TypeScript／Vite 與 Tauri debug 編譯通過；原生窗口實際展開處理方式選單，方向鍵與 Enter 切換到「還原後綴並解壓」，目標後綴欄位隨之顯示。
- 原生設定內的外觀 Dropdown 已檢查：彈層在 640×480 窗口內可見，Escape 只先關閉選單，設定對話框仍在。短窗口空狀態重排為居中的圖示／文字操作組合，沒有裁切或縮小字體；明暗兩種外觀已實際打開。
- 本輪只修改前端視覺與選擇器，因此驗證限定為類型／建置、原生渲染及選擇器互動，沒有把先前真實解壓驗證當作本輪重新跑過的結果。截圖：artifacts/fluent-refined-dropdown.png、fluent-refined-short.png、fluent-refined-dark.png。
