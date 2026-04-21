# VIBECODE_IDE
VIBECODE_IDE_GUI


1.The settings allow you to configure the AI, language, and window mode.

<img width="350" height="348" alt="image" src="https://github.com/user-attachments/assets/6b5137c1-928d-4ca8-b096-7bfea26fd63b" />

2.After completing the vibe coding process, you can click VIBEOUT to export the prompt. This may take a short moment.


The settings panel allows users to configure the AI backend, interface language, and window mode based on their personal workflow and usage preferences. I personally recommend using a local AI setup, because this tool was originally designed for users who do not want to pay for subscriptions or consume unnecessary tokens. Its main purpose is to reduce token costs while still maintaining an efficient AI-assisted development process.

After the user finishes outlining the logic architecture, they can press COPY to copy the generated prompt. This prompt can then be pasted into Claude or ChatGPT, allowing the AI to carry out more precise boundary analysis, requirement clarification, and structured discussion based on the user’s design.

Once the requirements and boundaries have been refined, the resulting specification document can be pasted into a new conversation and used directly for code generation.
<img width="734" height="437" alt="image" src="https://github.com/user-attachments/assets/bd5cae97-740a-4dbb-a840-a8b8a4c96ecf" />

example: Output prompt
As a senior Requirements Analyst, I will translate your structured request and the interview rules into professional technical English.
Role: Senior Requirements Analyst
Project: Arduino-based "Goblin Paper Doll" Display Device
Overall Summary
This system aims to create an interactive character simulation display based on the Arduino Uno, utilizing four physical buttons and an OLED screen. The core functionality simulates a "Goblin" character's random walking behavior during idle states and executes specific actions—such as attacking, switching weapons, or changing equipment—when the user presses designated buttons.
Main Workflow
Initialization (SETUP): The system boots up, initializes hardware (SSD1306 OLED), and sets the initial character state.
Main Render Loop (LOOP): The system continuously calls Render() and Goblin() functions.
Idle Behavior: Without button input, the Goblin character (32x32) automatically performs a left-right walking animation, restricted within X-coordinates 10 to 120.
Action Trigger: When any physical button is pressed, the main loop pauses to execute the corresponding event handler (e.g., attack or gear change).
Execution & Return: Based on the input, the system processes weapon switching (Up/Down), weapon attacks, or equipment changes. Once completed, the system returns to the main loop to resume the walking simulation with the updated state.
Decision Branches
The system triggers independent processes upon detecting physical button signals:
BTN_ATTACK: Triggers Weapon_attack(int X) to execute the attack animation for the current weapon.
BTN_APPLY: Triggers clothes_SW(int X) to toggle the character's armor or outfit.
BTN_UP: Triggers weapon_sw(int X) to cycle to the next weapon index.
BTN_DOWN: Triggers weapon_sw(int X) to cycle to the previous weapon index.
Data & States
Inputs: Physical button signals (timing, Button ID), Weapon Index (Int), Equipment Index (Int).
State Changes:
Position: X-coordinate (10–120) fluctuates over time.
Weapon/Armor State: Current indices maintained via weapon_sw and clothes_SW.
Rendering State: Continuous drawing of animations on the OLED.
Outputs: Real-time 32x32 Goblin imagery on the SSD1306 OLED, including attack animations and visual equipment swaps.
Implementation Requirements
Hardware: Arduino Uno + SSD1306 OLED.
Animation: Main loop for idle X-axis (10–120) walking.
Events: 4 buttons for Weapon Up/Down, Attack, and Armor Toggle.
Content: Min. 5 weapons (Sword+Shield, Greatsword, Warhammer, Machine Gun, Claymore) and 2+ armor sets (Plate, Grass Skirt, Cloth).
Logic: Buttons must interrupt walking, execute action, then return smoothly to idle.
Interview Rules for Behavior Boundaries:
Ask only one question at a time.
Provide 3–4 options (A, B, C, D) per question; Option E is always "Custom (please describe)."
Proceed to the next question only after receiving an answer until all modules are confirmed.
Finally, output a comprehensive Technical Specification Document.
Now, let’s begin with the first module: Hardware & Connectivity.
Question 1: Regarding the 4 physical buttons, how do you prefer to handle the hardware wiring and signal logic?


A. Use internal INPUT_PULLUP (Active Low: buttons connect to GND).
B. Use external Pull-Down resistors (Active High: buttons connect to 5V).
C. Use an Analog Button Ladder (All 4 buttons on a single Analog pin to save IO).
D. Use an I2C Button Expansion module.
E. Custom (please describe).
What is your choice?



3.boundary discussion

4.output result:

https://github.com/user-attachments/assets/3914fe4f-b21a-4ccd-85dc-611f1a104fcf





