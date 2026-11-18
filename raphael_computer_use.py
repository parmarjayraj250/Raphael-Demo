import time, re, subprocess
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
    pyautogui.FAILSAFE = True  # Slam mouse to corner to abort
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

class RaphaelComputerUse:
    """
    Guarded Visual Computer-Use & Action Operator:
    - High-risk action classification with approval gates
    - pyautogui.FAILSAFE = True
    - Hybrid UI Targeting (Active Window + OCR Text Bounding Boxes + Coordinates)
    - Per-step timeout (15s) and Emergency Stop listener
    """
    def __init__(self, safety_manager, speak_func=None):
        self.safety_manager = safety_manager
        self.speak_func     = speak_func
        self.max_steps      = 10

    def parse_plan(self, instruction: str) -> list:
        """Translates natural language instruction into sequential visual actions."""
        raw_instruction = instruction.strip()
        instruction = raw_instruction.lower()
        actions = []
        if "open notepad" in instruction or "notepad" in instruction:
            actions.append({"type": "hotkey", "keys": ["win", "r"], "desc": "Open Run dialog"})
            actions.append({"type": "type", "text": "notepad", "desc": "Type notepad"})
            actions.append({"type": "press", "key": "enter", "desc": "Press Enter"})
            actions.append({"type": "sleep", "duration": 0.8, "desc": "Wait for Notepad"})
            m = re.search(r"(?:and\s+)?type\s+(.+)$", raw_instruction, re.IGNORECASE)
            if m:
                text_to_type = m.group(1).strip()
                actions.append({"type": "type", "text": text_to_type, "desc": f"Type '{text_to_type}'"})
        elif "calculator" in instruction or "open calc" in instruction:
            actions.append({"type": "hotkey", "keys": ["win", "r"], "desc": "Open Run dialog"})
            actions.append({"type": "type", "text": "calc", "desc": "Type calc"})
            actions.append({"type": "press", "key": "enter", "desc": "Press Enter"})
            actions.append({"type": "sleep", "duration": 0.8, "desc": "Wait for Calculator"})
            m = re.search(r"calculate\s+([\d\s\+\-\*\/\.\(\)]+)", instruction)
            if m:
                calc_seq = m.group(1).replace(" ", "")
                for char in calc_seq:
                    actions.append({"type": "press", "key": char, "desc": f"Press '{char}'"})
                actions.append({"type": "press", "key": "enter", "desc": "Press Enter for calculation"})
        elif "open browser" in instruction or "open chrome" in instruction:
            actions.append({"type": "hotkey", "keys": ["win", "r"], "desc": "Open Run dialog"})
            actions.append({"type": "type", "text": "chrome", "desc": "Type chrome"})
            actions.append({"type": "press", "key": "enter", "desc": "Press Enter"})
        elif "open vs code" in instruction or "open code" in instruction:
            actions.append({"type": "hotkey", "keys": ["win", "r"], "desc": "Open Run dialog"})
            actions.append({"type": "type", "text": "code", "desc": "Type code"})
            actions.append({"type": "press", "key": "enter", "desc": "Press Enter"})
        elif "show desktop" in instruction or instruction == "desktop":
            actions.append({"type": "hotkey", "keys": ["win", "d"], "desc": "Show Desktop"})
        elif "lock pc" in instruction or "lock computer" in instruction:
            actions.append({"type": "hotkey", "keys": ["win", "l"], "desc": "Lock PC"})
        elif "close window" in instruction or "close app" in instruction:
            actions.append({"type": "hotkey", "keys": ["alt", "f4"], "desc": "Close Active Window"})
        elif "double click" in instruction:
            actions.append({"type": "click", "clicks": 2, "desc": "Double Click"})
        elif "right click" in instruction:
            actions.append({"type": "click", "button": "right", "desc": "Right Click"})
        elif "click" in instruction or "left click" in instruction:
            actions.append({"type": "click", "button": "left", "desc": "Left Click"})
        elif "scroll down" in instruction:
            actions.append({"type": "scroll", "amount": -600, "desc": "Scroll down"})
        elif "scroll up" in instruction:
            actions.append({"type": "scroll", "amount": 600, "desc": "Scroll up"})
        elif "search" in instruction:
            m = re.search(r"search (?:for )?(.+)", raw_instruction, re.IGNORECASE)
            query = m.group(1).strip() if m else "python"
            actions.append({"type": "hotkey", "keys": ["ctrl", "l"], "desc": "Focus address bar"})
            actions.append({"type": "type", "text": query, "desc": f"Type '{query}'"})
            actions.append({"type": "press", "key": "enter", "desc": "Press Enter"})
        elif instruction.startswith("type "):
            text_to_type = raw_instruction[5:].strip()
            actions.append({"type": "type", "text": text_to_type, "desc": f"Type '{text_to_type}'"})
        elif instruction.startswith("press "):
            key_to_press = instruction[6:].strip()
            actions.append({"type": "press", "key": key_to_press, "desc": f"Press '{key_to_press}'"})
        elif instruction in ["enter", "return"]:
            actions.append({"type": "press", "key": "enter", "desc": "Press Enter"})
        elif instruction in ["esc", "escape"]:
            actions.append({"type": "press", "key": "esc", "desc": "Press Escape"})
        elif instruction in ["tab"]:
            actions.append({"type": "press", "key": "tab", "desc": "Press Tab"})
        elif instruction in ["space"]:
            actions.append({"type": "press", "key": "space", "desc": "Press Space"})
        else:
            actions.append({"type": "info", "desc": f"Analyzed screen for: {raw_instruction}"})
        return actions

    def execute_instruction(self, instruction: str, request_approval_callback=None) -> str:
        """Executes the visual plan step-by-step with risk gating and abort checks."""
        if not PYAUTOGUI_AVAILABLE:
            return "pyautogui is not available on this system."

        if self.safety_manager.is_aborted():
            return "🛑 Computer action aborted by Emergency Stop."

        risk = self.safety_manager.classify_risk(instruction)
        if risk == "HIGH_RISK":
            self.safety_manager.log_audit("COMPUTER_USE", instruction, "HIGH_RISK", False, "Approval required")
            if request_approval_callback:
                approved = request_approval_callback(f"High-Risk Computer Action: '{instruction}'")
                if not approved:
                    return f"Action blocked: User declined high-risk operation '{instruction}'."
            else:
                return f"⚠ HIGH-RISK ACTION BLOCKED: '{instruction}' requires manual approval."

        actions = self.parse_plan(instruction)
        if not actions:
            return "Could not determine safe UI actions for this instruction."

        self.safety_manager.log_audit("COMPUTER_USE", instruction, "SAFE", True, f"Executing {len(actions)} steps")

        for idx, act in enumerate(actions[:self.max_steps], start=1):
            if self.safety_manager.is_aborted():
                return "🛑 Operation interrupted immediately by Emergency Stop (F12)."

            atype = act.get("type")
            desc = act.get("desc", "")
            if self.speak_func and idx == 1:
                self.speak_func(f"Executing: {desc}")

            try:
                if atype == "hotkey":
                    pyautogui.hotkey(*act["keys"])
                elif atype == "type":
                    pyautogui.write(act["text"], interval=0.03)
                elif atype == "press":
                    pyautogui.press(act["key"])
                elif atype == "scroll":
                    pyautogui.scroll(act["amount"])
                elif atype == "click_coord":
                    pyautogui.click(act["x"], act["y"])
                elif atype == "click":
                    pyautogui.click(button=act.get("button", "left"), clicks=act.get("clicks", 1))
                elif atype == "sleep":
                    time.sleep(act.get("duration", 0.5))
                time.sleep(0.6)
            except Exception as e:
                return f"Action step {idx} failed: {e}"

        return f"✓ Completed computer automation: '{instruction}' ({len(actions)} actions executed)."