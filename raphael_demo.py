import os
import sys
import socket
import threading
from pathlib import Path

# Ensure working directory is the script's directory
_SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(_SCRIPT_DIR)
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from raphael import Raphael
from raphael_legacy_gui import RaphaelGUI

# Dedicated Demo Sandbox jailed directory
SANDBOX_DIR = (_SCRIPT_DIR / "demo_sandbox").resolve()
os.makedirs(SANDBOX_DIR, exist_ok=True)

_DEMO_SINGLETON_PORT = 47292
_DEMO_SINGLETON_SOCKET = None


def _is_safe_sandbox_path(target_path: str) -> tuple[bool, Path]:
    """Strictly validates that target_path resolves inside SANDBOX_DIR.
    Rejects directory traversal (..) and absolute paths outside the sandbox.
    """
    try:
        raw = str(target_path).strip().replace("/", "\\")
        # Traversal check before resolution
        parts = Path(raw).parts
        if ".." in parts:
            return False, SANDBOX_DIR
        resolved = (SANDBOX_DIR / raw).resolve() if not os.path.isabs(raw) else Path(raw).resolve()
        # Verify it stays strictly within the sandbox folder
        if resolved.is_relative_to(SANDBOX_DIR):
            return True, resolved
        return False, resolved
    except Exception:
        return False, SANDBOX_DIR


class RaphaelDemoEngine(Raphael):
    """Restricted Raphael engine designed specifically for safe demo distribution.
    Enforces safe_mode in constructor, zero LAN servers, zero destructive commands,
    and strict file jailing inside demo_sandbox.
    """

    def __init__(self, callback_print=None, hide_window_callback=None, show_window_callback=None,
                 on_speak_start=None, on_speak_end=None):
        # 1. Pass demo_mode=True upfront to constructor (kills web servers & ghost daemons)
        super().__init__(
            callback_print=callback_print,
            hide_window_callback=hide_window_callback,
            show_window_callback=show_window_callback,
            on_speak_start=on_speak_start,
            on_speak_end=on_speak_end,
            demo_mode=True,
        )
        self.singleton_socket = None

    def _register_demo_tools(self):
        """Registers only safe, verified tools for demo mode."""
        self.tool_registry.register(
            name="system_status",
            description="Reports CPU, memory, disk usage, and battery statistics.",
            handler=self.system_status,
            risk_level="SAFE",
            permission="system",
        )
        self.tool_registry.register(
            name="free_up_ram",
            description="Frees unused RAM via Python garbage collection.",
            handler=self.free_up_ram,
            risk_level="SAFE",
            permission="system",
        )
        self.tool_registry.register(
            name="web_search",
            description="Searches the web using DuckDuckGo.",
            handler=self.web_search,
            schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            risk_level="SAFE",
            permission="network",
        )
        self.tool_registry.register(
            name="get_weather",
            description="Fetches live weather reports for a location.",
            handler=self.get_weather,
            schema={"type": "object", "properties": {"location": {"type": "string"}}},
            risk_level="SAFE",
            permission="network",
        )
        self.tool_registry.register(
            name="sandbox_read_file",
            description="Reads a text note or file strictly inside the demo_sandbox folder.",
            handler=self.demo_read_file,
            schema={"type": "object", "properties": {"filename": {"type": "string"}}, "required": ["filename"]},
            risk_level="SAFE",
            permission="file",
        )
        self.tool_registry.register(
            name="sandbox_write_file",
            description="Writes text content to a note strictly inside the demo_sandbox folder.",
            handler=self.demo_write_file,
            schema={"type": "object", "properties": {"filename": {"type": "string"}, "content": {"type": "string"}}, "required": ["filename", "content"]},
            risk_level="SAFE",
            permission="file",
        )
        self.tool_registry.register(
            name="sandbox_list_files",
            description="Lists all files in the demo_sandbox folder.",
            handler=self.demo_list_files,
            risk_level="SAFE",
            permission="file",
        )

    # ── Jailed Sandbox File Handlers ──────────────────────────────────────────
    def read_file(self, filepath: str, summarize: bool = False) -> str:
        safe, path = _is_safe_sandbox_path(filepath)
        if not safe:
            return "🔒 Demo Edition: Access outside demo_sandbox is blocked for your security."
        if not path.is_file():
            return f"File '{path.name}' not found in demo_sandbox."
        try:
            content = path.read_text(encoding="utf-8", errors="replace").strip()
            if not content:
                return "File is empty."
            if summarize:
                return self.ai_chat("Summarize this file:\n" + content[:2000])
            return content[:1000]
        except Exception as e:
            return f"Error: {e}"

    def demo_read_file(self, filename: str) -> str:
        safe, path = _is_safe_sandbox_path(filename)
        if not safe:
            return "🔒 Demo Edition: Access outside the demo sandbox is blocked for your security."
        if not path.is_file():
            return f"File '{path.name}' not found in demo_sandbox."
        try:
            return path.read_text(encoding="utf-8", errors="replace")[:10000]
        except Exception as e:
            return f"Error reading file: {e}"

    def demo_write_file(self, filename: str, content: str) -> str:
        safe, path = _is_safe_sandbox_path(filename)
        if not safe:
            return "🔒 Demo Edition: Access outside the demo sandbox is blocked for your security."
        try:
            path.write_text(content, encoding="utf-8")
            return f"✓ Successfully saved to demo_sandbox\\{path.name} ({len(content)} characters)."
        except Exception as e:
            return f"Error writing file: {e}"

    def demo_list_files(self) -> str:
        try:
            items = [f.name for f in SANDBOX_DIR.iterdir() if f.is_file()]
            if not items:
                return "The demo_sandbox folder is currently empty."
            return "Files in demo_sandbox:\n" + "\n".join(f"  • {item}" for item in items)
        except Exception as e:
            return f"Error listing files: {e}"

    # ── Override Respond with Strict Guardrails ──────────────────────────────
    def respond(self, text, is_voice=False):
        t = text.strip().lower()
        if not t:
            return None

        # Check sandbox file reading/listing requests
        if t in ["list sandbox", "sandbox files", "list files in sandbox", "show sandbox", "show demo files"]:
            return self.demo_list_files()

        # Deterministic guardrails (app launch, shell, destructive disk, mouse/screen)
        # Inherits all gating from Raphael.respond() while providing extra demo shortcuts
        return super().respond(text, is_voice=is_voice)


def _ensure_demo_single_instance():
    """Binds to dedicated demo port 47292 to avoid colliding with main Raphael on 47291."""
    global _DEMO_SINGLETON_SOCKET
    _DEMO_SINGLETON_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _DEMO_SINGLETON_SOCKET.bind(("127.0.0.1", _DEMO_SINGLETON_PORT))
        _DEMO_SINGLETON_SOCKET.listen(5)
        return True
    except OSError:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect(("127.0.0.1", _DEMO_SINGLETON_PORT))
            s.sendall(b"WAKEUP\n")
            s.close()
            print("[Raphael Demo] Existing instance found. Restored to screen.")
        except Exception:
            pass
        return False


if __name__ == "__main__":
    if not _ensure_demo_single_instance():
        sys.exit(0)

    # Initialize the demo engine with demo_mode=True
    engine = RaphaelDemoEngine()
    engine.singleton_socket = _DEMO_SINGLETON_SOCKET

    # Launch native desktop GUI with demo=True
    app = RaphaelGUI(engine=engine, demo=True)
    app.run()
