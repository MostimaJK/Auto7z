# MIT 授權變更與檢查記錄

日期：2026-10-27。檢查基準：`9d5772bf4cbdcd816798b7a439098dc1f8f7a5b6` 的當前程式碼與鎖定依賴。

## 授權範圍

經專案擁有者指示，當前版本中由 JackyNgai 擁有著作權的 Auto7z 程式碼與自有文件改採根目錄 LICENSE 的 MIT 授權。第三方程式庫、工具二進位、第三方素材與其授權原文不因此重新授權。

對XERJ所詢問的提交 `9d5772bf4cbdcd816798b7a439098dc1f8f7a5b6`，其中由JackyNgai擁有著作權的修改亦額外按MIT條款提供；此項許可不改變提交中第三方內容的授權。

此前已依 GPL-3.0 發布的副本仍可按原授權使用。本次變更不將整個 Git 歷史中的舊 PyQt／Fluent 版本及其依賴一併改為 MIT。既有發行附件沒有重新建置或替換；後續建置會複製新的 LICENSE 與第三方聲明。

## 已檢查的證據

- `git shortlog -sne HEAD` 列出一個提交作者：JackyNgai，共17次提交。這不能單獨證明全部內容的權利來源。
- 檢查目前受追蹤的自有程式碼與第三方來源／版權標記，未發現內嵌第三方 GPL 或 AGPL 程式碼的明示標記。這是程式碼與中繼資料檢查，並非對未標記程式碼來源的獨立鑑定。
- 當前後台僅依賴 Python 標準庫；舊 PyQt、Qt、PyQt-Fluent-Widgets 已從目前版本移除。
- `desktop/package-lock.json` 中47個非根目錄、非dev套件的宣告授權為 MIT、Apache-2.0（含雙授權）、BSD-2-Clause、BSD-3-Clause、ISC。
- `cargo metadata --locked --offline --filter-platform x86_64-pc-windows-msvc --format-version 1` 解析出251個套件（包含Auto7z）。宣告授權沒有缺失，未出現GPL／AGPL；包括MIT、Apache-2.0、BSD、Zlib、Unicode、Unlicense、CC0及MPL-2.0等條款或其組合。
- Cargo.lock 共包含421個外部套件條目，部分為其他平台依賴；本次完整解析範圍為Windows x64 MSVC，未宣稱已檢查所有其他平台的發行組合。
- 5個MPL-2.0元件保持原授權，不併入Auto7z自有程式碼的MIT授權；第三方聲明補上固定版本原始碼下載位置。
- 7-Zip作為獨立工具隨包提供，保留LGPL、BSD與unRAR附加限制。PyInstaller保留實際使用版本的許可及打包例外。根目錄MIT授權不取代這些條款。
- 現有建置腳本會將根目錄LICENSE與THIRD_PARTY_NOTICES.md複製到resources；Portable／Single打包清單已包含它們，無須修改打包流程。

## 對外說明

MIT允許商業使用、修改和再分發，使用者須保留必要的版權與許可聲明。專案的MIT標記只描述自有內容，第三方元件仍須依各自條款使用。

參考：

- MIT：https://opensource.org/license/mit
- MPL整合作品與原始碼取得義務：https://www.mozilla.org/en-US/MPL/2.0/FAQ/
- PyInstaller打包例外：https://pyinstaller.org/en/stable/license.html
