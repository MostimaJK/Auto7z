# Auto7z 桌面架構

現行前端為Vue 3.5.44／TypeScript、Element Plus 2.14.7與Tauri 2.12.4。只有實際使用的組件及樣式被註冊與打包；分段選擇器是保留Element Plus單選行為的Vue組件，不含React。

資料流：Vue → 限定Tauri JSON指令 → 獨立Python JSON-lines後台 → extraction.Engine → 7-Zip／WinRAR。沒有HTTP解壓服務，前端不具通用shell能力。掃描與解壓在後台執行緒，stdin仍能接收取消；EOF合作終止、Windows Job Object回收所屬後代進程。

後台使用標準庫，不載入Qt；開發從原始碼啟動，release使用PyInstaller獨立後台。7-Zip輸出以磁碟暫存保留有界診斷，獨立讀取句柄解析真實進度，不改動子進程的共用寫入位置。當前嘗試進度與整批完成數分開，未知總量不虛構百分比。

設定識別碼沿用local.auto7z.element，避免遺失既有偏好。單EXE只是同一便攜內容的校驗／釋放啟動器；不引入另一套前端或解壓實作。快取按版本及內容雜湊隔離，檢查逐檔SHA256，準備過程有跨進程互斥與暫存目錄原子發佈，既有不完整／改動快取另建修復目錄而不覆寫。

開發、建置、系統需求、下載與測試請看根目錄 [README](../README.md)。現行驗證見 [VALIDATION](../docs/VALIDATION.md)。過去的Qt／Fluent實作保留於Git歷史和6.1.0 Release，不再作為當前可運行入口。
