> 歷史設計參考（6.x）：現行7.x界面、啟動與發行方式請見README.md。當時的預覽程式已退休，素材與本文件保留供參考。

# 進度與加載效果探索 · Auto7z

> 2026-10-15 最終決定：主介面固定採用 Apple 簡潔樣式，已移除預覽與配色控制。以下內容為歷史探索紀錄。

## 最新反饋與當前版本（優先於下方歷史探索）

用戶試用後不認可彈性/平滑過渡，明確要求移除，改用直接更新；更喜歡 Apple、Google、Microsoft 的經典方向。
用戶進一步明確不喜歡 Google 波浪，喜歡 Apple 細橫條，並要求彩虹色加輕微發光的對比。
用戶已明確確認 Apple 簡潔、Google 直線、Microsoft Fluent 三種可使用；明確否定彩虹配色，保留微光動效的探索。
當前第四條爲參考 color-design skill 的候選「藍青 · 微光」：鈷藍 #2457A7 經藍青 #1973A4 過渡到青綠 #176B70，光暈緩慢呼吸。前三種已認可，不推斷新配色也已認可。默認仍爲 Apple。
進一步探索：當前候選擴展爲六種微光配色（克萊因藍、勃艮第紅、祖母綠、靛藍、普魯士藍與青綠、陶土紅），配色試驗檯新增底部下拉框，比較冷白、奶油、深色底與三檔光暈。此處色值是技能的屏幕近似配方，不是顏料或品牌標準。
預覽支持四種樣式與確定/未知進度比較；實際隊列使用確定進度。前三種是原生 Qt 改編，藍青微光爲自定義設計，均不宣稱官方控件的逐像素復刻。
下方 Motion、極光、霓虹與彈性實現記錄保留爲探索歷史，不再表示當前默認方案或已認可的最終偏好。
UIUX skill 本輪仍未更新，等待用戶確認經典樣式。

## 已確認的偏好（用戶本輪明確表達）

- 喜歡極光流彩的藍青紫，以及霓虹呼吸的紫粉與光暈。
- 喜歡 Motion 的彈性變化和平滑過渡，要求融合進 Auto7z。
- 收藏截圖 2 的 3D 幾何加載、截圖 3 的旋轉搜索弧、截圖 4 的往返橫條、截圖 5 的彩色圓弧，以及截圖 6 的地球加載，供其他項目使用。
- 進度條探索效果滿意後，再更新 uiux-product-designer skill。本輪沒有直接改寫 skill。

截圖已從臨時剪貼板目錄複製到 `artifacts/progress-inspiration/`。
截圖只證明外觀，運動方向和速度沿用用戶描述；未將靜態截圖當作完整動畫實測。

## 收藏清單

| 參考 | 作者與證據 | 用途建議 | 語義 |
|---|---|---|---|
| [Motion 彈性](https://motion.dev/examples/react-loading-progress-bar) | 截圖 1（本機歷史截圖，未散布） | 下載、解壓、導出等數值更新；短暫緩動追上真實值 | 確定進度的表現層 |
| [3D 幾何體](https://uiverse.io/AqFox/young-dragon-29) | AqFox；截圖 2（本機歷史截圖，未散布） | 3D、模型、技術工具的初始化 | 未知總量活動指示 |
| [旋轉搜索弧候選原帖](https://uiverse.io/mobinkakei/pink-deer-76) | mobinkakei；官方倉庫源碼包含 searching；截圖 3（本機歷史截圖，未散布） | 搜索、掃描、連接、服務發現 | 活動指示，不能標完成百分比 |
| 往返橫條 | TemplateVentures；截圖 4（本機歷史截圖，未散布）；尚未定位原帖 | 預檢、未知規模掃描；可保持橫條造型切換到確定進度 | 不確定進度 |
| [彩色圓弧候選原帖](https://uiverse.io/fanishah/wicked-wasp-20) | fanishah；截圖 5（本機歷史截圖，未散布）；尚未逐幀對照 | 創意、AI 工具、短暫處理 | 活動指示；需要數值數據纔可變爲確定進度 |
| 地球加載 | AatreyuShau；截圖 6（本機歷史截圖，未散布）；尚未定位原帖 | 地圖、地理數據、全球檢索、旅行項目 | 領域身份與等待反饋，不是精確地圖 |

## 補充的官方參考與遷移判斷

### Apple

- [Progress indicators HIG](https://developer.apple.com/design/human-interface-guidelines/progress-indicators)：優先準確的確定進度；可測後從不確定橫條轉換爲確定橫條，保持空間穩定。
- [SwiftUI ProgressView](https://developer.apple.com/documentation/swiftui/progressview)：線性與圓形原生樣式，適合作爲剋制的基線。
- [Apple Watch / Fitness Activity rings](https://www.apple.com/watch/close-your-rings/)：三個目標的同心圓環；參考多目標組織和清晰色彩身份。它們是健身目標完成度，不是下載或加載進度。
- 遷移建議：短緩動、圓潤端點、安靜的非焦點區域、完成反饋後穩定落下；這些是本項目建議，不是 Apple 原生參數的復刻。

### Google

- [Material 3 Expressive ProgressIndicator](https://github.com/material-components/material-components-android/blob/master/docs/components/ProgressIndicator.md)：波浪橫條/圓環，有確定與不確定模式，支持波長、振幅與厚度。
- [Material 3 Expressive LoadingIndicator](https://github.com/material-components/material-components-android/blob/master/docs/components/LoadingIndicator.md)：形狀與運動爲短等待增加辨識度，官方定位爲 5 秒以內的等待。
- [Wear OS 官方產品示例](https://android-developers.googleblog.com/2025/08/introducing-material-3-expressive-for-wear-os.html)：可觀察圍繞播放/暫停操作的波浪進度條；播放位置與任務完成進度是不同數據。
- 遷移建議：把低振幅波浪作爲候選樣式；只有短暫預檢或初始化才考慮形變加載，長時間解壓仍提供任務、層級與結果信息。

### Microsoft

- [Fluent 2 Progress bar](https://fluent2.microsoft.design/components/web/react/core/progressbar/usage)：結合簡短狀態與相關步驟，減少重複歸零引起的不確定感。
- 遷移建議：Auto7z 繼續保留隊列與當前活動兩個層級，外觀變化不改變成功/部分完成/失敗的結果語義。

## 下一輪候選（建議，尚未實現）

1. **極光彗星**：流動漸變 + 小光點前端 + 短尾跡；光點不能越過真實填充位置。
2. **低振幅波浪**：Google 參考，波動僅改變形狀，不改變完成長度。
3. **品牌形變**：幾何圖形旋轉與柔和形變，僅用於短等待。
4. **液態膠囊**：緩慢內流動與細高光，不覆蓋狀態文字。
5. **完成反饋**：真實完成後一次短掃光或端點合攏；失敗/取消停止循環，並給出恢復入口。
6. **領域加載**：地圖項目使用地球/瓦片加載；3D 項目用幾何體。不要把它們自動套在全部產品上。

## 本輪實現與驗證

- Auto7z 兩種原生進度條加入「彈性過渡 / 平滑過渡 / 直接更新」。
- value() 與事件仍立即反映真實數據；只有繪製長度緩動，限制在真實值內。新任務歸零立即復位。
- 彈性使用阻尼彈簧響應並限制數值反彈；平滑使用指數趨近。其手感受 Motion 啓發，沒有複製 Motion 的默認參數。
- 預覽增加「演示跳變」，從模擬 0% 切到 80%，不影響實際解壓。
- 已驗證數值範圍、單調性、最終收斂、動畫開關、隱藏停止、預覽隔離，以及既有任務重試。
- 官方原生 App 未在本機逐幀實測；以上官方參考來自文檔與產品展示，不宣稱復刻或動畫參數一致。

## 可供以後納入 UIUX skill 的條目

先判斷未知/確定進度和等待規模，再選品牌、領域與運動形式；記錄真值和顯示值的區分。
需覆蓋零進度、連續/跳躍更新、未知總量、完成、失敗、取消、隱藏、關閉動畫與窄窗口。
保留出處、截圖與適用條件；用戶認可後再將驗證過的案例整理入 skill，未驗證樣式繼續保留爲候選。
