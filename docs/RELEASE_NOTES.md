# Auto7z 7.0.0

這一版將桌面入口統一為Vue 3 + Element Plus + Tauri 2，保留成熟的Python解壓核心。提供繁體中文、明暗主題、克萊因藍選中態和滑動分段導航，文件佇列與常駐候選密碼為主要工作區；日誌、解壓軟體設定各自獨立。

- 批量、後綴修改、多密碼、遞迴、分卷首卷辨識、取消、失敗重試與結果查看。
- 後綴可選常見格式或自訂，支援.tar.gz；改後綴不等於轉換壓縮格式。
- 真實7-Zip嘗試進度與整批文件完成數分開，未知總量不虛構百分比。
- 按需載入Element組件；元件JS約984KB→410KB、CSS約363KB→116KB。這是構建體積比較，不是啟動時間或解壓性能基準。
- 清理退休的Qt／Fluent實作、重複入口及舊構建腳本；歷史版本仍可取得。

## 選擇下載

| 檔案 | 用途 |
| --- | --- |
| Windows-x64-Single.exe | 單檔下載入口，內嵌Python後台與7-Zip；首次校驗並釋放至獨立版本快取 |
| Windows-x64-Portable.zip | 完整依賴資料夾版，解壓後執行Auto7z/Auto7z.exe，保留resources |
| Windows-x64-Setup.exe | 安裝版 |
| SHA256SUMS.txt | 三種檔案的SHA256校驗 |

Windows 10／11 x64，需要系統Microsoft Edge WebView2 Runtime。單EXE啟動器使用.NET Framework 4.8；Windows 10 22H2／11通常已有。無需另裝Python、Node.js或Rust。Single不是完全不落地的EXE，首次會釋放依賴到%LOCALAPPDATA%/Auto7z/Runtime，後續逐檔校驗並重用快取。

設定沿用%APPDATA%/local.auto7z.element/settings.json以保留試用版偏好。密碼、佇列與日誌僅保留於本次工作階段。外層原包保留，取消不刪既有成功結果。WinRAR不隨包分發，可於設定指定自行安裝的版本。原始碼、授權、重建腳本及驗證範圍見專案README與docs/VALIDATION.md。

發行檔未進行程式碼簽章，可用本專案Release附帶的SHA256核對檔案。
