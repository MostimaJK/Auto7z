# Auto7z 7.0.0 發行驗證

日期：2026-10-18。目標：Windows 10／11 x64；本機實測Windows 11，未宣稱全部Windows版本、DPI或硬件均已覆蓋。

## 自動檢查

- `python -m unittest discover -s tests -v`：16項通過。
- `python -m unittest discover -s desktop/tests -v`：16項通過。
- Vue TypeScript、Vite、Rust release、獨立PyInstaller後台與NSIS建置通過。
- `scripts/verify_release.py`對兩種發行包分別啟動其中攜帶的後台與7-Zip，與開發Python核心分開驗證：真實加密／多密碼、嵌套ZIP內容、損壞包失敗、修復後只重試失敗項，原成功目錄不變。
- Portable內容符合明確允許清單，逐檔雜湊及三種發行檔SHA256一致，沒有使用者設定、WinRAR、照片或Qt檔案。另檢查PyInstaller外層TOC，未發現PyQt／PySide／QFluent項目。
- Single首次無快取時並行啟動兩個校驗進程，兩者成功完成；暖啟動不重寫已驗證檔案。模擬損壞僅改動本次新建快取中的README，成功另建修復目錄、保留原改動，後續重用修復快取，測試後還原測試文件。
- 暫存輸出協議、耗時取消單元案例包含明確標示的模擬子進程；不能把這些案例當成真實解壓性能測量。其餘標為真實7-Zip的案例均執行實際二進位。

## 原生與範圍

- Portable與Single都從各自獨立位置啟動真正Tauri窗口，按需載入後的工作區、常駐密碼與設定控件正常呈現。
- 沿用此前已實測的分段鼠標／方向鍵切換、自訂後綴改名、淺／深主題及640×480短窗口；此前真實100.1MB／12,000文件ZIP進度與10%取消結果仍作核心行為參考，並非本輪效能基準。
- 本輪未執行NSIS系統安裝／卸載，僅驗證安裝包構建與雜湊。不更改系統WebView2、顯示器DPI或註冊表偏好。
- 單檔依賴釋放、SHA驗證的耗時不等同UI首幀或解壓吞吐量；不以包體縮減宣稱這些效能同比改善。

## 清理與回復

舊PyQt、C++/Qt、Fluent入口及舊測試從當前發行線移除，可由Git歷史與v6.1.0恢復。舊本機build、dist、C++構建和資源快取移到工作區外的維護備份，沒有遞迴清除可能混入的設定。DEMO、使用者配置、WinRAR自行安裝副本、progress-inspiration.md及本地參考素材保留；歷史artifacts只取消版本追蹤，檔案仍在本機。

本輪Single原生窗口另外經Ctrl+O加入繁體中文ZIP、Ctrl+Enter執行，界面顯示成功，實際輸出文字已讀回核對；本地證據artifacts/v7-single-native-success.png。
