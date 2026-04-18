# VIBECODE_IDE
VIBECODE_IDE_GUI


The settings allow you to configure the AI, language, and window mode.

The settings panel allows users to configure the AI backend, interface language, and window mode based on their personal workflow and usage preferences. I personally recommend using a local AI setup, because this tool was originally designed for users who do not want to pay for subscriptions or consume unnecessary tokens. Its main purpose is to reduce token costs while still maintaining an efficient AI-assisted development process.

After the user finishes outlining the logic architecture, they can press COPY to copy the generated prompt. This prompt can then be pasted into Claude or ChatGPT, allowing the AI to carry out more precise boundary analysis, requirement clarification, and structured discussion based on the user’s design.

Once the requirements and boundaries have been refined, the resulting specification document can be pasted into a new conversation and used directly for code generation.
<img width="734" height="437" alt="image" src="https://github.com/user-attachments/assets/bd5cae97-740a-4dbb-a840-a8b8a4c96ecf" />

輸出的prompt

你是一位資深需求訪談師。以下是一份功能需求描述： ## 整體摘要 本系統旨在建立一個基於 Arduino Uno 的哥布林紙娃娃顯示裝置，透過 4 個物理按鈕和一個 OLED 螢幕，實現一個互動式的角色模擬展示。系統的核心功能是模擬哥布林角色在閒置時的隨機散步行為，並在使用者按下指定按鈕時，根據按鈕類型執行攻擊、切換武器或更換裝備等特定動作。 ## 主要流程 1. **初始化階段 (SETUP)：** 系統啟動，完成所有硬體（如 OLED 螢幕）和角色狀態的初始化設置。 2. **主循環渲染 (LOOP)：** 系統進入主循環，持續呼叫 Render() 和 Goblin() 函式。 * **閒置行為：** 如果無按鈕輸入，哥布林角色（32x32）會自動執行左右散步的移動動作，X 座標範圍限定在 10 到 120 之間。 * **動作觸發：** 當任何一個物理按鈕被按下時，主循環暫停，並進入特定的事件處理流程，執行與按鈕對應的動作（例如攻擊或換裝）。 3. **動作執行與返回：** 根據按鈕輸入，系統依次處理武器切換（上/下）、武器攻擊或裝備切換。動作完成後，系統會回到主循環，重新渲染角色，並繼續模擬散步或保持在新的狀態。 ## 決策分支 系統的決策點發生在主循環監測到任何物理按鈕訊號時，每個按鈕都會觸發一個獨立的處理流程： * **當按下「攻擊動作」（BTN_ATTACK）時：** 觸發 Weapon_attack(INT X) 流程，執行指定武器的攻擊動作。 * **當按下「切換鎧甲裝備」（BTN_APPLY）時：** 觸發 clothes_SW(INT X) 流程，用於切換角色的整體裝備或鎧甲。 * **當按下「切換武器 - 上一個」（BTN_UP）：** 觸發 weapon_sw(INT X) 流程，切換到下一個索引的武器。 * **當按下「切換武器 - 下一個」（BTN_DOWN）：** 觸發 weapon_sw(INT X) 流程，切換到上一個索引的武器。 ## 資料與狀態 * **系統輸入資料 (Input)：** * 物理按鈕的訊號（時間序、按鍵 ID）。 * 武器索引（INT X）。 * 裝備索引（INT X）。 * **系統狀態變化 (State)：** * **位置狀態：** 哥布林角色 X 座標 (介於 10 到 120 之間) 會隨時間變化。 * **武器狀態：** 透過 weapon_sw 保持當前選定的武器索引。 * **裝備狀態：** 透過 clothes_SW 保持當前選定的裝備或鎧甲索引。 * **繪圖狀態：** 需要在 OLED 螢幕上持續繪製角色動畫和動作畫面。 * **系統輸出結果 (Output)：** * 透過 SD1306 OLED 螢幕即時顯示哥布林的 32x32 圖像。 * 根據動作，應展示攻擊動畫、角色換裝的視覺效果，或保持散步移動的動畫。 ## AI 實作 Prompt 請實作一個基於 Arduino Uno 的哥布林角色互動展示系統，功能需求如下： 1. **硬體平台與介面：** 系統必須使用 Arduino Uno 核心，並透過 SD1306 OLED 螢幕進行繪圖輸出。 2. **核心動畫與狀態管理：** 必須建立一個主循環 (Main Loop) 來持續管理角色狀態。在閒置時，哥布林角色（32x32 圖像）應模擬沿著 X 軸（10~120）的左右散步動畫。 3. **按鈕輸入與事件處理：** 系統必須監測 4 個物理按鈕的輸入，每個按鈕需綁定一套明確的事件處理流程： * **武器切換 (UP/DOWN)：** 實現循環的武器索引切換邏輯 (weapon_sw)，模擬切換武器的視覺效果。 * **攻擊動作 (ATTACK)：** 根據當前武器索引，觸發具體的攻擊動畫 (Weapon_attack)。 * **裝備切換 (APPLY)：** 根據當前裝備索引，觸發裝備更換的視覺效果 (clothes_SW)。 4. **功能細節要求：** 系統需具備至少 5 種武器（刀+盾/劍/雙手槌/機關槍/雙手劍）和至少 2 套裝備（全身鎧甲/草裙/布甲）的選擇與切換機制。 5. **輸出邏輯：** 確保所有的按鈕輸入都能暫停散步動畫，執行指定的動畫動作，動作結束後，系統必須平滑地返回到主循環繼續散步，保持視覺連貫性。 請從第一個模組開始進行行為邊界訪談： 1. 每次只問我一個問題 2. 每題提供 3～4 個選項，最後一項永遠是「E. 自訂（請描述）」 3. 等我回答後再問下一個，直到所有模組確認完畢 4. 最後輸出一份完整的技術規格文件


邊界討論

最後結果

https://github.com/user-attachments/assets/3914fe4f-b21a-4ccd-85dc-611f1a104fcf





