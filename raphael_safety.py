import os, sys, time, threading, subprocess, re
from datetime import datetime

AUDIT_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raphael_audit.log")

class RaphaelSafetyManager:
    """
    Central Safety, Risk Management, and Emergency Stop Engine.
    Handles independent F12 aborts, active subprocess killing, and structured audit logging.
    """
    def __init__(self, callback_alert=None):
        self.callback_alert = callback_alert
        self._abort_event = threading.Event()
        self._active_subprocesses = []
        self._proc_lock = threading.Lock()
        self._high_risk_patterns = [
            r"\b(delete|remove|rmdir|rm|format|erase)\b",
            r"\b(install|pip install|npm install|setup\.exe)\b",
            r"\b(password|passcode|secret|api_key|token|credit_card)\b",
            r"\b(buy|purchase|checkout|pay)\b",
            r"\b(shutdown|reboot|restart)\b",
            r"\b(powershell -enc|cmd /c del|sudo)\b"
        ]

    def log_audit(self, category: str, action: str, risk_level: str, approved: bool, details: str = ""):
        """Appends a safe audit log entry with log rotation and secret redaction."""
        clean_details = re.sub(r'(token|key|password|passcode|secret|auth|bearer)\s*[:=]\s*\S+', r'\1: [REDACTED]', details, flags=re.IGNORECASE)
        clean_details = re.sub(r'\b[0-9a-fA-F]{32,64}\b', '[REDACTED_HASH]', clean_details)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = (
            f"[{timestamp}] CATEGORY: {category.upper()} | ACTION: {action} | "
            f"RISK: {risk_level} | APPROVED: {approved} | DETAILS: {clean_details}\n"
        )
        try:
            # Rotate audit log when it exceeds 2MB
            if os.path.exists(AUDIT_LOG_FILE) and os.path.getsize(AUDIT_LOG_FILE) > 2 * 1024 * 1024:
                bak = AUDIT_LOG_FILE + ".1"
                try:
                    if os.path.exists(bak):
                        os.remove(bak)
                    os.rename(AUDIT_LOG_FILE, bak)
                except Exception:
                    pass
            with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass

    def classify_risk(self, command_or_action: str) -> str:
        """Classifies an action as 'SAFE' or 'HIGH_RISK'."""
        text = command_or_action.lower()
        for pat in self._high_risk_patterns:
            if re.search(pat, text):
                return "HIGH_RISK"
        return "SAFE"

    def register_subprocess(self, proc: subprocess.Popen):
        """Tracks active subprocesses so they can be forcibly killed if F12 is pressed."""
        with self._proc_lock:
            self._active_subprocesses.append(proc)

    def unregister_subprocess(self, proc: subprocess.Popen):
        with self._proc_lock:
            if proc in self._active_subprocesses:
                self._active_subprocesses.remove(proc)

    def trigger_emergency_stop(self, source: str = "F12"):
        """
        IMMEDIATE EMERGENCY STOP:
        Fires independently of the main AI loop.
        Signals cancellation and forcibly terminates all registered subprocesses.
        """
        self._abort_event.set()
        self.log_audit("SAFETY", f"EMERGENCY_STOP_TRIGGERED ({source})", "CRITICAL", True, "Forced termination of active workers and subprocesses.")

        with self._proc_lock:
            for proc in self._active_subprocesses:
                try:
                    proc.kill()
                except Exception:
                    pass
            self._active_subprocesses.clear()

        if self.callback_alert:
            try:
                self.callback_alert("🛑 EMERGENCY STOP TRIGGERED: All autonomous operations halted immediately.")
            except Exception:
                pass

    def is_aborted(self) -> bool:
        return self._abort_event.is_set()

    def reset_emergency_stop(self):
        self._abort_event.clear()
        self.log_audit("SAFETY", "EMERGENCY_STOP_RESET", "INFO", True, "System returned to ready state.")