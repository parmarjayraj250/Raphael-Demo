import os, sys, time, threading, math, re, ctypes, subprocess
from datetime import datetime
try:
    import customtkinter as ctk
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

try:
    import pystray
    from PIL import Image as PILImage, ImageDraw as PILImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

from raphael import Raphael, RESEARCH_DIR, TTS_AVAILABLE, IS_WINDOWS, KEYBOARD_AVAILABLE

# ── Tray Icon ──────────────────────────────────────────────────────────────────
def _make_tray_icon():
    try:
        img = PILImage.new("RGBA", (64, 64), (15, 23, 42, 255))
        d   = PILImageDraw.Draw(img)
        d.ellipse((6, 6, 58, 58), outline=(56, 189, 248, 255), width=5)
        d.ellipse((24, 24, 40, 40), fill=(56, 189, 248, 255))
        return img
    except Exception:
        return None


# ── GUI: CELESTIAL EDGE (Deep Indigo & Gold) ──────────────────────────────────
class RaphaelGUI:
    DARK_BG        = "#070714"   # Deep Space Indigo Black
    PANEL_BG       = "#0c0c24"   # Deep Indigo Frame
    CARD_BG        = "#0f1026"   # Card Background
    CARD_BORDER    = "#1e1e48"   # Subtle Indigo Border
    GOLD_ACCENT    = "#f5a623"   # Bright Celestial Gold
    GOLD_BRIGHT    = "#ffb800"   # Vivid Gold
    GOLD_MUTED     = "#c59b27"   # Warm Muted Gold
    PURPLE_ACCENT  = "#6366f1"   # Celestial Indigo/Purple
    PURPLE_GLOW    = "#7c3aed"   # Neon Violet Glow
    NAV_ACTIVE_BG  = "#1e1b4b"   # Active Nav item
    NAV_ACTIVE_BRD = "#6366f1"   # Active Nav border
    TEXT_MAIN      = "#f8fafc"   # Clean White
    TEXT_MUTED     = "#8e8ea8"   # Slate Muted
    TEXT_GOLD      = "#f5a623"   # Gold Highlight
    GREEN          = "#4ade80"   # Online Green
    YELLOW         = "#f59e0b"   # Listening Amber
    RED            = "#ef4444"   # Danger Red
    ACCENT         = "#f5a623"   # Primary Accent (Gold)
    ACCENT2        = "#6366f1"   # Secondary Accent (Purple)
    BTN_DARK       = "#141432"
    BTN_HOVER      = "#22224e"

    def __init__(self, engine=None, demo=False):
        self.demo = demo
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        if self.demo:
            self.root.title("Raphael AI — Celestial Edge (Demo Edition)")
        else:
            self.root.title("Raphael AI — Celestial Edge")
        self.root.geometry("1020x760")
        self.root.minsize(900, 680)
        self.root.resizable(True, True)
        self.root.configure(fg_color=self.DARK_BG)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)

        self._wave_phase    = 0.0
        self._wave_active   = False
        self._orb_angle     = 0.0
        self._pill_win      = None
        self._recent_events = [
            ("Live news sources active", "1m ago"),
            ("ChromaDB vector memory online", "3m ago"),
            ("Proactive context intelligence ready", "6m ago"),
            ("Deep research agent standing by", "12m ago"),
            ("System health verified", "18m ago"),
        ]

        self.is_locked = False
        self.engine = engine or Raphael(
            callback_print=self._on_raphael_message,
            hide_window_callback=self.hide_window_sync,
            show_window_callback=self.show_window_sync,
            on_speak_start=self._on_speak_start,
            on_speak_end=self._on_speak_end
        )
        self.engine.gui = self
        if self.engine.memory.get("passcode"):
            self.is_locked = True

        self._build_ui()
        self._setup_tray()
        self._play_startup_chime()
        self._build_pill_widget()
        self._animate_hud_orb()
        self._draw_wave()
        self._start_gauge_updater()
        if self.is_locked:
            self._lock_ui()

        # ── One-time startup: register hotkeys (skip in demo) and show welcome ─
        if not self.demo:
            self._register_global_hotkey()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(200, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()
        if self.demo:
            welcome = "Celestial Edge (Demo Edition) online. System vitals, web search, and local AI ready."
        else:
            welcome = "Celestial Edge online. How can I assist you today?"
            n = self.engine.memory.get("user_name")
            if n:
                welcome = f"Welcome back, {n}. Celestial Edge systems operational."
        self.root.after(500, lambda: self._append("Raphael", welcome))

        # Background listener to pop window to front if user launches Raphael again
        def _singleton_wakeup():
            import raphael
            sock = getattr(self.engine, 'singleton_socket', None) or getattr(raphael, '_SINGLETON_SOCKET', None)
            if not sock:
                return
            while True:
                try:
                    conn, _ = sock.accept()
                    data = conn.recv(64)
                    conn.close()
                    if b"WAKEUP" in data:
                        self.root.after(0, self.show_from_tray)
                except Exception:
                    break
        threading.Thread(target=_singleton_wakeup, daemon=True).start()


    def _on_speak_start(self):
        def _do():
            self._start_wave()
            if hasattr(self, "status_dot"):
                self.status_dot.configure(text="● SPEAKING", text_color=self.GOLD_ACCENT, border_color=self.GOLD_ACCENT)
        self.root.after(0, _do)

    def _on_speak_end(self):
        def _do():
            self._stop_wave()
            if hasattr(self, "status_dot"):
                self.status_dot.configure(text="● ONLINE", text_color=self.PURPLE_ACCENT, border_color=self.PURPLE_ACCENT)
        self.root.after(0, _do)

    # ── Global Hotkey: Multi-Key Windows RegisterHotKey & Keyboard Hook ─────────
    def _register_global_hotkey(self):
        """
        Registers multi-key system-wide hotkeys (Ctrl+Alt+R, Ctrl+Shift+R, Ctrl+Alt+Space, F9, F10, Ctrl+Alt+X)
        using both Win32 RegisterHotKey API and Python keyboard library with key suppression.
        """
        def _trigger():
            self.root.after(0, self._on_global_hotkey)

        # Layer 1: Python keyboard library hook with key suppression (stops desktop icon jumping!)
        if KEYBOARD_AVAILABLE:
            for hk in ["ctrl+alt+r", "ctrl+shift+r", "ctrl+alt+space", "f9", "ctrl+alt+x"]:
                try:
                    keyboard.add_hotkey(hk, _trigger, suppress=False)
                except Exception:
                    pass
            try:
                keyboard.add_hotkey("f10", lambda: self.root.after(0, self.toggle_mini_hud), suppress=False)
            except Exception:
                pass
            try:
                keyboard.add_hotkey("ctrl+shift+f12", self._on_f12_emergency_stop, suppress=False)
            except Exception:
                pass

        # Layer 2: Win32 native RegisterHotKey API message pump
        if not IS_WINDOWS:
            return
        import ctypes
        import ctypes.wintypes

        MOD_ALT     = 0x0001
        MOD_CONTROL = 0x0002
        MOD_SHIFT   = 0x0004

        hotkeys = [
            (1, MOD_CONTROL | MOD_ALT,   0x52),  # Ctrl + Alt + R
            (2, MOD_CONTROL | MOD_SHIFT, 0x52),  # Ctrl + Shift + R
            (3, MOD_CONTROL | MOD_ALT,   0x20),  # Ctrl + Alt + Space
            (4, 0,                       0x78),  # F9 (single key shortcut)
            (5, 0,                       0x79),  # F10 (Mini-HUD toggle)
            (6, MOD_CONTROL | MOD_SHIFT, 0x7B),  # Ctrl+Shift+F12 (Emergency Stop)
        ]

        user32 = ctypes.windll.user32

        def _hotkey_thread():
            # Force message queue initialization for thread
            msg = ctypes.wintypes.MSG()
            user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

            registered = []
            for hid, mod, vk in hotkeys:
                ok = user32.RegisterHotKey(None, hid, mod, vk)
                if ok:
                    registered.append(hid)

            while True:
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret <= 0:
                    break
                if msg.message == 0x0312:  # WM_HOTKEY
                    if msg.wParam == 5:
                        self.root.after(0, self.toggle_mini_hud)
                    elif msg.wParam == 6:
                        self._on_f12_emergency_stop()
                    else:
                        self.root.after(0, self._on_global_hotkey)

            for hid in registered:
                user32.UnregisterHotKey(None, hid)

        threading.Thread(target=_hotkey_thread, daemon=True).start()

    def _on_f12_emergency_stop(self):
        """Immediately executes emergency stop in independent thread."""
        self.engine.safety_manager.trigger_emergency_stop("F12_KEY")
        def _update():
            if hasattr(self, "status_dot"):
                self.status_dot.configure(text="● READY (ABORTED)", text_color=self.RED, border_color=self.RED)
            self._append("System", "🛑 EMERGENCY STOP (F12) ACTIVATED: All computer actions and worker tasks terminated immediately.")
        self.root.after(0, _update)

    def _on_global_hotkey(self):
        """Called whenever Ctrl+Alt+R / Ctrl+Shift+R / Ctrl+Alt+Space is pressed."""
        ctx = self.engine.get_active_window_context()
        self.show_from_tray()
        if ctx and ctx.get("suggestion"):
            self._append("Context AI", ctx["suggestion"])

    # ── Startup Chime ──────────────────────────────────────────────────────────
    def _play_startup_chime(self):
        if not TTS_AVAILABLE:
            return
        def _chime():
            try:
                sample_rate = 44100
                tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_chime.wav")
                frames = []
                for freq, dur in [(440, 0.12), (554, 0.12), (659, 0.22)]:
                    n_samples = int(sample_rate * dur)
                    for i in range(n_samples):
                        t = i / sample_rate
                        fade = min(1.0, min(i, n_samples - i) / (sample_rate * 0.03))
                        val = int(32767 * fade * 0.35 * math.sin(2 * math.pi * freq * t))
                        frames.append(struct.pack('<h', max(-32768, min(32767, val))))
                with wave.open(tmp, 'w') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(b''.join(frames))
                pygame.mixer.music.load(tmp)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.05)
                pygame.mixer.music.unload()
                try:
                    os.remove(tmp)
                except Exception:
                    pass
            except Exception:
                pass
        threading.Thread(target=_chime, daemon=True).start()

    # ── Pill Widget (Floating Overlay) ─────────────────────────────────────────
    def _build_pill_widget(self):
        try:
            import tkinter as tk
            pill = tk.Toplevel(self.root)
            pill.overrideredirect(True)
            pill.attributes("-topmost", True)
            pill.attributes("-alpha", 0.90)
            pill.configure(bg=self.DARK_BG)
            pill.geometry("180x36+" + str(self.root.winfo_screenwidth() - 200) + "+10")

            self._pill_canvas = tk.Canvas(pill, width=180, height=36, bg=self.DARK_BG, highlightthickness=0)
            self._pill_canvas.pack()
            self._pill_canvas.create_oval(0, 0, 180, 36, outline=self.GOLD_ACCENT, width=1)

            self._pill_text = self._pill_canvas.create_text(
                90, 18, text="◈ RAPHAEL  ●", fill=self.GOLD_ACCENT,
                font=("Helvetica", 10, "bold")
            )
            pill.bind("<Button-1>", lambda e: self.show_from_tray())
            self._pill_win = pill
            self._animate_pill()
        except Exception:
            pass

    def _animate_pill(self):
        try:
            if self._pill_win and self._pill_canvas:
                phase = time.time() % 2
                color = self.GREEN if phase < 1 else self.GOLD_ACCENT
                self._pill_canvas.itemconfigure(self._pill_text, text="◈ RAPHAEL  ●", fill=color)
                self._pill_win.after(600, self._animate_pill)
        except Exception:
            pass

    # ── Animated HUD Orb & Radar ───────────────────────────────────────────────
    def _animate_hud_orb(self):
        """Draws rotating futuristic orbital rings with the golden R emblem."""
        try:
            c = getattr(self, "orb_canvas", None)
            if c:
                c.delete("orb")
                w = c.winfo_width() or 130
                h = c.winfo_height() or 130
                cx, cy = w // 2, h // 2
                self._orb_angle = (self._orb_angle + 0.04) % (2 * math.pi)

                # Outer glowing arc 1 (Cyan/Indigo)
                r1 = int(w * 0.42)
                start1 = math.degrees(self._orb_angle)
                c.create_arc(cx - r1, cy - r1, cx + r1, cy + r1, start=start1, extent=130,
                             outline=self.BLUE_ACCENT if hasattr(self, "BLUE_ACCENT") else "#38bdf8",
                             width=2, style="arc", tags="orb")
                c.create_arc(cx - r1, cy - r1, cx + r1, cy + r1, start=start1 + 180, extent=80,
                             outline="#6366f1", width=2, style="arc", tags="orb")

                # Mid glowing arc 2 (Gold)
                r2 = int(w * 0.35)
                start2 = math.degrees(-self._orb_angle * 1.5)
                c.create_arc(cx - r2, cy - r2, cx + r2, cy + r2, start=start2, extent=90,
                             outline=self.GOLD_ACCENT, width=2.5, style="arc", tags="orb")
                c.create_arc(cx - r2, cy - r2, cx + r2, cy + r2, start=start2 + 150, extent=60,
                             outline=self.GOLD_MUTED, width=1.5, style="arc", tags="orb")

                # Inner circle background
                r3 = int(w * 0.26)
                c.create_oval(cx - r3, cy - r3, cx + r3, cy + r3,
                              fill="#0d142e", outline=self.GOLD_ACCENT, width=1.5, tags="orb")

                # Orbiting particle planet
                px = cx + (r1 + 2) * math.cos(self._orb_angle)
                py = cy + (r1 + 2) * math.sin(self._orb_angle)
                c.create_oval(px - 4, py - 4, px + 4, py + 4, fill=self.GOLD_BRIGHT, outline="#fff", width=1, tags="orb")

                # Central Golden 'R' Letter
                font_sz = max(16, int(w * 0.18))
                c.create_text(cx, cy, text="R", fill=self.GOLD_BRIGHT,
                              font=("Helvetica", font_sz, "bold"), tags="orb")

            self.root.after(40, self._animate_hud_orb)
        except Exception:
            pass

    # ── Voice Wave Canvas ──────────────────────────────────────────────────────
    def _start_wave(self):
        self._wave_active = True

    def _stop_wave(self):
        self._wave_active = False

    def _draw_wave(self):
        try:
            c = getattr(self, "_wave_canvas", None)
            if c:
                c.delete("wave")
                w = c.winfo_width() or 260
                h = c.winfo_height() or 36
                cx = h // 2
                self._wave_phase += 0.25 if self._wave_active else 0.08
                bar_count = 22
                bar_width = max(3, (w // bar_count) - 3)
                for i in range(bar_count):
                    x = i * (bar_width + 3) + 8
                    if self._wave_active:
                        # High energy dancing equalizer when speaking/listening
                        val = math.sin(self._wave_phase + i * 0.55) * math.cos(self._wave_phase * 0.7 + i * 0.3)
                        bar_h = int(abs(val) * (h * 0.44)) + 4
                        color = self.GOLD_BRIGHT if i % 2 == 0 else self.GOLD_ACCENT
                    else:
                        # Calm idle breathing wave
                        val = math.sin(self._wave_phase + i * 0.3)
                        bar_h = int(abs(val) * 4) + 2
                        color = "#453818" if i % 2 == 0 else "#2d2410"

                    c.create_rectangle(x, cx - bar_h, x + bar_width, cx + bar_h,
                                       fill=color, outline="", tags="wave")
            self.root.after(35, self._draw_wave)
        except Exception:
            pass

    def toggle_mini_hud(self):
        """Toggles between full Celestial Edge Dashboard and floating compact Mini-HUD."""
        self._mini_hud_mode = not getattr(self, "_mini_hud_mode", False)
        if self._mini_hud_mode:
            # Switch to Mini-HUD: small 320x350 floating widget, topmost
            self.root.geometry("320x350")
            self.root.attributes("-topmost", True)
            self.root.resizable(False, False)
            if hasattr(self, "sidebar"):
                self.sidebar.pack_forget()
            if hasattr(self, "q_card"):
                self.q_card.pack_forget()
            if hasattr(self, "pop_card"):
                self.pop_card.pack_forget()
            self._append("System", "Mini-HUD Mode active. Press F10 to restore dashboard.")
        else:
            # Restore Full Dashboard: 1020x760
            self.root.geometry("1020x760")
            self.root.attributes("-topmost", False)
            self.root.resizable(True, True)
            if hasattr(self, "sidebar"):
                self.sidebar.pack(side="left", fill="y")
            if hasattr(self, "q_card"):
                self.q_card.pack(fill="x", pady=4)
            if hasattr(self, "pop_card"):
                self.pop_card.pack(fill="x", pady=4)
            self._append("System", "Restored full Celestial Edge Dashboard.")

    # ── Real-time Gauge Updater ────────────────────────────────────────────────
    def _start_gauge_updater(self):
        def _update():
            if not PSUTIL_AVAILABLE:
                return
            try:
                cpu  = int(psutil.cpu_percent(interval=None))
                ram  = int(psutil.virtual_memory().percent)
                disk = int(psutil.disk_usage("/").percent)
                bat  = psutil.sensors_battery()
                bat_pct = int(bat.percent) if bat else 85
                self.root.after(0, lambda: self._draw_gauges(cpu, ram, disk, bat_pct))
            except Exception:
                pass
            self.root.after(3000, _update)

        self.root.after(1000, _update)

    def _draw_gauges(self, cpu, ram, disk, bat):
        try:
            c = getattr(self, "gauge_canvas", None)
            if not c:
                return
            c.delete("gauge")
            metrics = [
                ("CPU", cpu, 34, "#38bdf8"),
                ("RAM", ram, 102, "#6366f1"),
                ("DISK", disk, 170, "#f59e0b"),
                ("BATTERY", bat, 238, "#22c55e"),
            ]
            for label, pct, x, color in metrics:
                y = 32
                r = 20
                # Background ring
                c.create_oval(x - r, y - r, x + r, y + r, outline="#141c38", width=3, tags="gauge")
                # Active progress arc
                extent = -int((pct / 100.0) * 360)
                c.create_arc(x - r, y - r, x + r, y + r, start=90, extent=extent,
                             outline=color, width=3, style="arc", tags="gauge")
                # Percentage text
                c.create_text(x, y, text=f"{pct}%", fill="#f8fafc",
                              font=("Helvetica", 8, "bold"), tags="gauge")
                # Label underneath
                c.create_text(x, y + 26, text=label, fill="#64748b",
                              font=("Helvetica", 7, "bold"), tags="gauge")
        except Exception:
            pass

    # ── UI Build (CELESTIAL EDGE) ──────────────────────────────────────────────
    def _build_ui(self):
        import tkinter as tk

        # ── 1. Top Header Bar ──────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self.root, fg_color=self.PANEL_BG, corner_radius=0, height=54)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # Left: Gold R Badge + Title
        hdr_left = ctk.CTkFrame(hdr, fg_color="transparent")
        hdr_left.pack(side="left", padx=14, pady=6)

        logo_box = ctk.CTkFrame(hdr_left, width=36, height=36, fg_color="#1a1406",
                                border_color="#d97706", border_width=1.5, corner_radius=8)
        logo_box.pack(side="left", padx=(0, 10))
        logo_box.pack_propagate(False)
        ctk.CTkLabel(
            logo_box, text="R",
            font=ctk.CTkFont(family="Helvetica", size=18, weight="bold"),
            text_color="#ffb800"
        ).pack(expand=True)

        title_box = ctk.CTkFrame(hdr_left, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(
            title_box, text="Raphael",
            font=ctk.CTkFont(family="Helvetica", size=16, weight="bold"),
            text_color="#f8fafc"
        ).pack(anchor="w")
        ctk.CTkLabel(
            title_box, text="AI Assistant",
            font=ctk.CTkFont(size=9),
            text_color="#64748b"
        ).pack(anchor="w")

        # Right: Status Badges & Window Controls
        hdr_right = ctk.CTkFrame(hdr, fg_color="transparent")
        hdr_right.pack(side="right", padx=14)

        # Status badge pill (Raphael with green dot)
        self.status_dot = ctk.CTkButton(
            hdr_right, text="● RAPHAEL ⌵", width=105, height=26,
            fg_color="#0c152e", hover_color="#141f3d",
            border_color="#1e294b", border_width=1,
            text_color="#f8fafc", font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=13, command=lambda: self._quick("system status")
        )
        self.status_dot.pack(side="left", padx=5)

        # Online Network pill
        net_pill = ctk.CTkButton(
            hdr_right, text="🌐 ONLINE", width=88, height=26,
            fg_color="#0a1c3d", hover_color="#122b5c",
            border_color="#1e40af", border_width=1,
            text_color="#38bdf8", font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=13, command=lambda: self._quick("system status")
        )
        net_pill.pack(side="left", padx=5)

        # Mobile Remote pill
        mobile_pill = ctk.CTkButton(
            hdr_right, text="📱 MOBILE", width=88, height=26,
            fg_color="#241406", hover_color="#3d230a",
            border_color="#d97706", border_width=1,
            text_color="#f5a623", font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=13, command=lambda: self._quick("pair mobile")
        )
        mobile_pill.pack(side="left", padx=5)

        # Research Vault pill
        research_pill = ctk.CTkButton(
            hdr_right, text="🔬 RESEARCH", width=95, height=26,
            fg_color="#1e1b4b", hover_color="#2e2b6b",
            border_color="#6366f1", border_width=1,
            text_color="#a5b4fc", font=ctk.CTkFont(size=10, weight="bold"),
            corner_radius=13, command=self._open_research_vault
        )
        research_pill.pack(side="left", padx=5)

        # Min / Tray / Close Icons
        ctk.CTkButton(
            hdr_right, text="─", width=26, height=26,
            fg_color="transparent", hover_color="#1e294b",
            font=ctk.CTkFont(size=12), command=self.hide_to_tray
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            hdr_right, text="✕", width=26, height=26,
            fg_color="transparent", hover_color="#7f1d1d",
            font=ctk.CTkFont(size=12), command=self.exit_app
        ).pack(side="left", padx=2)

        # Glowing separator
        sep = ctk.CTkFrame(self.root, fg_color="#192242", height=1, corner_radius=0)
        sep.pack(fill="x")

        # ── 2. Body Container (Left Nav + Main Content Area) ───────────────────
        body = ctk.CTkFrame(self.root, fg_color=self.DARK_BG, corner_radius=0)
        body.pack(fill="both", expand=True)

        # ── Left Navigation Sidebar ────────────────────────────────────────────
        sidebar = ctk.CTkFrame(body, fg_color=self.PANEL_BG, width=165, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        nav_items = [
            ("🏠  Commands",   "__nav_commands__", True),
            ("⚙  System",     "system status",     False),
            ("📑  Notes",      "view notes",        False),
            ("🔍  Search",     "__search_prompt__", False),
            ("✨  Automation", "view schedule",     False),
            ("📁  Files",      "organize my files", False),
            ("⚙  Settings",   "my facts",          False),
        ]

        ctk.CTkFrame(sidebar, fg_color="transparent", height=10).pack()
        for label, cmd, is_active in nav_items:
            if is_active:
                btn = ctk.CTkButton(
                    sidebar, text=label, width=145, height=38,
                    fg_color="#1a1406", hover_color="#261d08",
                    border_color="#f5a623", border_width=1.5,
                    text_color="#ffb800", font=ctk.CTkFont(size=11, weight="bold"),
                    anchor="w", corner_radius=8,
                    command=lambda c=cmd: self._nav_click(c)
                )
            else:
                btn = ctk.CTkButton(
                    sidebar, text=label, width=145, height=38,
                    fg_color="transparent", hover_color="#131c38",
                    border_width=0,
                    text_color="#94a3b8", font=ctk.CTkFont(size=11),
                    anchor="w", corner_radius=8,
                    command=lambda c=cmd: self._nav_click(c)
                )
            btn.pack(padx=10, pady=3)

        # Bottom Sidebar Card (CE v1.0 Celestial Edge Deep Indigo & Gold)
        sb_bot_card = ctk.CTkFrame(sidebar, fg_color="#0a1024", border_color="#182442",
                                   border_width=1, corner_radius=10)
        sb_bot_card.pack(side="bottom", fill="x", padx=10, pady=16)
        ctk.CTkLabel(
            sb_bot_card, text="👑  CE v1.0",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f5a623", anchor="w"
        ).pack(anchor="w", padx=10, pady=(8, 2))
        ctk.CTkLabel(
            sb_bot_card, text="Celestial Edge",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#f8fafc", anchor="w"
        ).pack(anchor="w", padx=10)
        ctk.CTkLabel(
            sb_bot_card, text="Deep Indigo & Gold",
            font=ctk.CTkFont(size=9),
            text_color="#64748b", anchor="w"
        ).pack(anchor="w", padx=10, pady=(0, 8))

        # ── Main Content Area (Scrollable) ─────────────────────────────────────
        main = ctk.CTkScrollableFrame(body, fg_color=self.DARK_BG, corner_radius=0)
        main.pack(side="left", fill="both", expand=True, padx=12, pady=10)

        # ── Top Hero Banner (Celestial Edge Atmospheric Horizon) ───────────────
        hero_frame = ctk.CTkFrame(main, fg_color="#080e22", corner_radius=14,
                                  border_color="#182444", border_width=1, height=105)
        hero_frame.pack(fill="x", pady=(0, 10))
        hero_frame.pack_propagate(False)

        hero_inner = ctk.CTkFrame(hero_frame, fg_color="transparent")
        hero_inner.pack(fill="both", expand=True, padx=18, pady=10)

        # Center top title block
        hero_center = ctk.CTkFrame(hero_inner, fg_color="transparent")
        hero_center.place(relx=0.5, rely=0.22, anchor="center")
        ctk.CTkLabel(
            hero_center, text="C E L E S T I A L   E D G E",
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#f5a623"
        ).pack()
        ctk.CTkLabel(
            hero_center, text="Deep Indigo & Gold",
            font=ctk.CTkFont(size=9), text_color="#a16207"
        ).pack()

        # Left big title
        hero_left = ctk.CTkFrame(hero_inner, fg_color="transparent")
        hero_left.pack(side="left", fill="y", pady=(10, 0))
        ctk.CTkLabel(
            hero_left, text="Raphael",
            font=ctk.CTkFont(family="Helvetica", size=28, weight="bold"),
            text_color="#ffffff", anchor="w"
        ).pack(anchor="w")
        ctk.CTkLabel(
            hero_left, text="Your AI Assistant",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#94a3b8", anchor="w"
        ).pack(anchor="w")
        ctk.CTkLabel(
            hero_left, text='"Think  •  Understand  •  Take Action"',
            font=ctk.CTkFont(size=10), text_color="#64748b", anchor="w"
        ).pack(anchor="w", pady=(2, 0))

        # Right motto
        hero_right = ctk.CTkFrame(hero_inner, fg_color="transparent")
        hero_right.pack(side="right", fill="y", pady=(46, 0))
        ctk.CTkLabel(
            hero_right, text="Logic  •  Productivity  •  Automation",
            font=ctk.CTkFont(size=10), text_color="#64748b"
        ).pack()

        # ── Middle Row: Greeting/Action Chips Card + System & Activity Cards ───
        mid_row = ctk.CTkFrame(main, fg_color="transparent")
        mid_row.pack(fill="x", pady=(0, 10))

        # Greeting & Quick Chips Card (Left)
        hud_card = ctk.CTkFrame(mid_row, fg_color=self.CARD_BG, corner_radius=14,
                                border_color=self.CARD_BORDER, border_width=1)
        hud_card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        hud_inner = ctk.CTkFrame(hud_card, fg_color="transparent")
        hud_inner.pack(fill="both", expand=True, padx=12, pady=12)

        # Orbital Radar Canvas
        self.orb_canvas = tk.Canvas(hud_inner, width=130, height=130, bg=self.CARD_BG,
                                    highlightthickness=0, bd=0)
        self.orb_canvas.pack(side="left", padx=(4, 12))

        # Greeting details and 5 Action Chips
        hud_col = ctk.CTkFrame(hud_inner, fg_color="transparent")
        hud_col.pack(side="left", fill="both", expand=True)

        user_n = self.engine.memory.get("user_name") or "Jay"
        hour = datetime.now().hour
        greet_word = "Good morning" if hour < 12 else ("Good afternoon" if hour < 18 else "Good evening")
        sun_icon = "☀️" if hour < 18 else "🌙"

        self.greet_lbl = ctk.CTkLabel(
            hud_col, text=f"{greet_word}, {user_n} {sun_icon}",
            font=ctk.CTkFont(family="Helvetica", size=18, weight="bold"),
            text_color="#f8fafc", anchor="w"
        )
        self.greet_lbl.pack(anchor="w", pady=(4, 2))

        ctk.CTkLabel(
            hud_col, text="How can I help you today?",
            font=ctk.CTkFont(size=12), text_color="#94a3b8", anchor="w"
        ).pack(anchor="w", pady=(0, 10))

        # Row of 5 Action Chips matching screenshot
        chips_row = ctk.CTkFrame(hud_col, fg_color="transparent")
        chips_row.pack(anchor="w", fill="x", pady=(0, 4))

        action_chips = [
            ("💡 Suggest something", "suggest something"),
            ("📑 Summarise a file",  "summarize clipboard"),
            ("🔍 Search the web",    "__search_prompt__"),
            ("⚙ Automate a task",   "view schedule"),
            ("🖥 Open an app",       "__open_app_dialog__"),
        ]
        for chip_lbl, chip_cmd in action_chips:
            ctk.CTkButton(
                chips_row, text=chip_lbl, height=30,
                fg_color="#0e1733", hover_color="#182552",
                border_color="#1e2c56", border_width=1,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#cbd5e1", corner_radius=15,
                command=lambda c=chip_cmd: self._quick(c)
            ).pack(side="left", padx=3)

        # Right Cards Container (width 290px)
        right_box = ctk.CTkFrame(mid_row, fg_color="transparent", width=290)
        right_box.pack(side="right", fill="y")
        right_box.pack_propagate(False)

        # Card 1: System Status
        sys_card = ctk.CTkFrame(right_box, fg_color=self.CARD_BG, corner_radius=12,
                                border_color=self.CARD_BORDER, border_width=1, height=110)
        sys_card.pack(fill="x", pady=(0, 6))
        sys_card.pack_propagate(False)

        sys_hdr = ctk.CTkFrame(sys_card, fg_color="transparent")
        sys_hdr.pack(fill="x", padx=10, pady=(6, 0))
        ctk.CTkLabel(
            sys_hdr, text="🌀 System Status", font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f8fafc"
        ).pack(side="left")
        ctk.CTkLabel(
            sys_hdr, text=">", font=ctk.CTkFont(size=11), text_color="#64748b"
        ).pack(side="right")

        self.gauge_canvas = tk.Canvas(sys_card, height=75, bg=self.CARD_BG,
                                      highlightthickness=0, bd=0)
        self.gauge_canvas.pack(fill="both", expand=True, padx=4)
        self._draw_gauges(2, 47, 66, 59)

        # Card 2: Recent Activity
        act_card = ctk.CTkFrame(right_box, fg_color=self.CARD_BG, corner_radius=12,
                                border_color=self.CARD_BORDER, border_width=1)
        act_card.pack(fill="both", expand=True)

        act_hdr = ctk.CTkFrame(act_card, fg_color="transparent")
        act_hdr.pack(fill="x", padx=10, pady=(6, 2))
        ctk.CTkLabel(
            act_hdr, text="🕒 Recent Activity", font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f8fafc"
        ).pack(side="left")

        self.act_list_frame = ctk.CTkFrame(act_card, fg_color="transparent")
        self.act_list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self._render_recent_activity()

        # ── Quick Commands (Spotify REMOVED! Replaced by AI Suggest) ───────────
        q_card = ctk.CTkFrame(main, fg_color=self.CARD_BG, corner_radius=12,
                              border_color=self.CARD_BORDER, border_width=1)
        q_card.pack(fill="x", pady=(0, 10))

        q_hdr = ctk.CTkFrame(q_card, fg_color="transparent")
        q_hdr.pack(fill="x", padx=14, pady=(8, 4))
        ctk.CTkLabel(
            q_hdr, text="⚡ Quick Commands",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f8fafc"
        ).pack(side="left")
        ctk.CTkButton(
            q_hdr, text="See All →", width=60, height=20,
            fg_color="transparent", hover_color="#182344",
            font=ctk.CTkFont(size=10), text_color="#64748b",
            command=lambda: self._quick("help")
        ).pack(side="right")

        q_bar = ctk.CTkFrame(q_card, fg_color="transparent")
        q_bar.pack(fill="x", padx=10, pady=(0, 10))

        quick_defs = [
            ("☁ Weather",        "Get latest weather",  "weather"),
            ("</> Open VS Code",  "Launch editor",       "open vs code"),
            ("💡 AI Suggest",     "Smart suggestions",   "suggest something"),
            ("🔍 Search Web",     "Find anything",       "__search_prompt__"),
            ("📑 Notes",          "Open notes",          "view notes"),
            ("🧹 Clean Temp",     "Free up space",       "clean temp files"),
            ("⚙ Free RAM",       "Optimize memory",     "free up ram"),
        ]
        for icon_title, sub, c_cmd in quick_defs:
            card = ctk.CTkFrame(q_bar, fg_color="#0e1630", border_color="#1a2546",
                                border_width=1, corner_radius=8, height=48)
            card.pack(side="left", padx=3, expand=True, fill="both")
            card.pack_propagate(False)

            l1 = ctk.CTkLabel(card, text=icon_title, font=ctk.CTkFont(size=10, weight="bold"),
                              text_color="#f8fafc")
            l1.pack(pady=(5, 0))
            l2 = ctk.CTkLabel(card, text=sub, font=ctk.CTkFont(size=8), text_color="#64748b")
            l2.pack(pady=(0, 4))

            for w in (card, l1, l2):
                w.bind("<Button-1>", lambda e, c=c_cmd: self._quick(c))
                w.bind("<Enter>", lambda e, f=card: f.configure(fg_color="#18244a", border_color="#38bdf8"))
                w.bind("<Leave>", lambda e, f=card: f.configure(fg_color="#0e1630", border_color="#1a2546"))

        # ── Popick Commands ───────────────────────────────────────────────────
        pop_card = ctk.CTkFrame(main, fg_color=self.CARD_BG, corner_radius=12,
                                border_color=self.CARD_BORDER, border_width=1)
        pop_card.pack(fill="x", pady=(0, 10))

        pop_hdr = ctk.CTkFrame(pop_card, fg_color="transparent")
        pop_hdr.pack(fill="x", padx=14, pady=(8, 4))
        ctk.CTkLabel(
            pop_hdr, text="⭐ Popick Commands",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f8fafc"
        ).pack(side="left")
        ctk.CTkButton(
            pop_hdr, text="See All →", width=60, height=20,
            fg_color="transparent", hover_color="#182344",
            font=ctk.CTkFont(size=10), text_color="#64748b",
            command=lambda: self._quick("help")
        ).pack(side="right")

        pop_bar = ctk.CTkFrame(pop_card, fg_color="transparent")
        pop_bar.pack(fill="x", padx=10, pady=(0, 10))

        pop_chips = [
            ("python run app.py", "run python app.py"),
            ("explain concept",   "explain neuromorphic computing"),
            ("read my screen",    "read my screen"),
            ("summarise file",    "summarize clipboard"),
            ("deep research",     "__research__"),
            ("my next alerts",    "my news alerts"),
        ]
        for chip_label, c_cmd in pop_chips:
            ctk.CTkButton(
                pop_bar, text=chip_label, height=28,
                fg_color="#090f24", hover_color="#172248",
                border_color="#1c2850", border_width=1,
                font=ctk.CTkFont(family="Consolas", size=10),
                text_color="#94a3b8", corner_radius=14,
                command=lambda c=c_cmd: self._quick(c)
            ).pack(side="left", padx=3, expand=True, fill="x")

        # ── Terminal & Conversation ────────────────────────────────────────────
        log_frame = ctk.CTkFrame(main, fg_color=self.CARD_BG, corner_radius=12,
                                 border_color=self.CARD_BORDER, border_width=1)
        log_frame.pack(fill="both", expand=True, pady=(0, 4))

        log_hdr = ctk.CTkFrame(log_frame, fg_color="transparent", height=28)
        log_hdr.pack(fill="x", padx=14, pady=(8, 2))
        ctk.CTkLabel(
            log_hdr, text="[>_] Terminal & Conversation",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f8fafc"
        ).pack(side="left")

        btn_box = ctk.CTkFrame(log_hdr, fg_color="transparent")
        btn_box.pack(side="right")
        ctk.CTkButton(
            btn_box, text="📋 Clear", width=55, height=20,
            fg_color="transparent", hover_color="#182344",
            font=ctk.CTkFont(size=10), text_color="#94a3b8",
            command=lambda: self._quick("__clear__")
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btn_box, text="📄 Copy", width=55, height=20,
            fg_color="transparent", hover_color="#182344",
            font=ctk.CTkFont(size=10), text_color="#94a3b8",
            command=self._copy_terminal
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btn_box, text="↗ Export", width=60, height=20,
            fg_color="transparent", hover_color="#182344",
            font=ctk.CTkFont(size=10), text_color="#94a3b8",
            command=self._export_terminal
        ).pack(side="left", padx=2)

        self.log = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            fg_color="#060a18",
            text_color="#f8fafc",
            border_width=0,
            corner_radius=8,
            height=135
        )
        self.log.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.log.tag_config("raphael", foreground="#f5a623")
        self.log.tag_config("user",    foreground="#a5b4fc")
        self.log.tag_config("system",  foreground="#94a3b8")

        # ── 3. Bottom Command Input Bar ────────────────────────────────────────
        bot_bar = ctk.CTkFrame(self.root, fg_color=self.PANEL_BG, corner_radius=0, height=72)
        bot_bar.pack(fill="x", side="bottom")
        bot_bar.pack_propagate(False)

        bot_inner = ctk.CTkFrame(bot_bar, fg_color="transparent")
        bot_inner.pack(fill="both", expand=True, padx=14, pady=12)

        # Big Gold Mic button
        self.mic_btn = ctk.CTkButton(
            bot_inner, text="🎙", width=48, height=48,
            fg_color="#1a1406", hover_color="#2b2009",
            border_color="#f5a623", border_width=2,
            text_color="#ffb800", font=ctk.CTkFont(size=18),
            corner_radius=12, command=self._voice
        )
        self.mic_btn.pack(side="left", padx=(0, 10))

        # Rounded Command Entry with Attachment clip inside
        inp_box = ctk.CTkFrame(bot_inner, fg_color="#0a1024", border_color="#1a274a",
                               border_width=1, corner_radius=12)
        inp_box.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.entry = ctk.CTkEntry(
            inp_box,
            placeholder_text="Type a command or say 'Hey Raphael'...",
            font=ctk.CTkFont(size=13),
            fg_color="transparent",
            border_width=0,
            text_color="#f8fafc",
        )
        self.entry.pack(side="left", fill="both", expand=True, padx=(12, 4))
        self.entry.bind("<Return>", lambda e: self._send())

        # Paperclip icon button inside entry
        clip_btn = ctk.CTkButton(
            inp_box, text="📎", width=34, height=34,
            fg_color="transparent", hover_color="#182344",
            text_color="#94a3b8", font=ctk.CTkFont(size=15),
            corner_radius=8, command=self._attach_file
        )
        clip_btn.pack(side="right", padx=(0, 6))

        # Gold Send button
        self.send_btn = ctk.CTkButton(
            bot_inner, text="➤", width=52, height=48,
            fg_color="#f5a623", hover_color="#ffb800",
            text_color="#070714", font=ctk.CTkFont(size=17, weight="bold"),
            corner_radius=12, command=self._send
        )
        self.send_btn.pack(side="right")

        # Security Lock Overlay
        self._build_lock_overlay()

    def _copy_terminal(self):
        try:
            import pyperclip
            content = self.log.get("1.0", "end").strip()
            if content:
                pyperclip.copy(content)
                self._append("System", "Terminal conversation copied to clipboard.")
        except Exception:
            pass

    def _export_terminal(self):
        try:
            from tkinter import filedialog
            content = self.log.get("1.0", "end").strip()
            if not content:
                return
            fn = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text file", "*.txt"), ("Markdown file", "*.md")],
                initialfile=f"raphael_chat_{int(time.time())}.txt"
            )
            if fn:
                with open(fn, "w", encoding="utf-8") as f:
                    f.write(content)
                self._append("System", f"Exported conversation to {os.path.basename(fn)}")
        except Exception:
            pass

    def _attach_file(self):
        try:
            from tkinter import filedialog
            fn = filedialog.askopenfilename(title="Select file for Raphael to summarize")
            if fn:
                self.entry.delete(0, "end")
                self.entry.insert(0, f"summarize file {fn}")
        except Exception:
            pass

    def _render_recent_activity(self):
        for widget in self.act_list_frame.winfo_children():
            widget.destroy()
        colors = ["#22c55e", "#38bdf8", "#a855f7", "#818cf8", "#f59e0b"]
        for idx, (action, t_ago) in enumerate(self._recent_events[:4]):
            row = ctk.CTkFrame(self.act_list_frame, fg_color="transparent", height=18)
            row.pack(fill="x", pady=1.5)
            dot_color = colors[idx % len(colors)]
            ctk.CTkLabel(
                row, text="●", font=ctk.CTkFont(size=9),
                text_color=dot_color
            ).pack(side="left", padx=(0, 5))
            ctk.CTkLabel(
                row, text=action, font=ctk.CTkFont(size=10),
                text_color="#f8fafc", anchor="w"
            ).pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(
                row, text=t_ago, font=ctk.CTkFont(size=9),
                text_color="#64748b", anchor="e"
            ).pack(side="right")

    def _add_recent_event(self, action):
        self._recent_events.insert(0, (action[:32], "Just now"))
        self.root.after(0, self._render_recent_activity)

    def _nav_click(self, cmd):
        if cmd == "__nav_commands__":
            self._quick("help")
        elif cmd == "__search_prompt__":
            q = self.entry.get().strip()
            if q:
                self._quick(f"search {q}")
            else:
                self._append("System", "Type a query in the input box, then click Search.")
        else:
            self._quick(cmd)

    # ── Log helpers ────────────────────────────────────────────────────────────
    def _append(self, sender, text, color=None):
        safe_text = str(text) if text is not None else ""
        def _do():
            try:
                self.log.configure(state="normal")
                prefix = "\n" + sender + ": "
                tag_name = sender.lower() if sender.lower() in ("raphael", "user", "system") else "system"
                self.log.insert("end", prefix, tag_name)
                self.log.insert("end", safe_text + "\n")
                self.log.see("end")
                self.log.configure(state="disabled")
            except Exception as e:
                print("[Log Append Error]", e)
        self.root.after(0, _do)

    def _on_raphael_message(self, text):
        if text.startswith("Raphael: "):
            text = text[9:]
        self._append("Raphael", text)

    # ── Security Lock Overlay ──────────────────────────────────────────────────
    def _build_lock_overlay(self):
        self.lock_frame = ctk.CTkFrame(self.root, fg_color="#04040d", corner_radius=0)

        box = ctk.CTkFrame(self.lock_frame, fg_color=self.CARD_BG, corner_radius=16,
                           border_color=self.GOLD_ACCENT, border_width=2)
        box.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.74, relheight=0.56)

        ctk.CTkLabel(
            box, text="🔒  CELESTIAL EDGE SECURITY CLEARANCE",
            font=ctk.CTkFont(family="Helvetica", size=16, weight="bold"),
            text_color=self.GOLD_ACCENT
        ).pack(pady=(28, 6))

        ctk.CTkLabel(
            box, text="Enter your master passcode to access Raphael.",
            font=ctk.CTkFont(size=12), text_color=self.TEXT_MUTED
        ).pack(pady=(0, 18))

        self.pass_entry = ctk.CTkEntry(
            box, placeholder_text="Enter Master Passcode...",
            show="•", font=ctk.CTkFont(size=14),
            fg_color=self.DARK_BG, border_color="#302e60",
            border_width=1, corner_radius=10, width=280, height=42,
            text_color=self.TEXT_MAIN
        )
        self.pass_entry.pack(pady=10)
        self.pass_entry.bind("<Return>", lambda e: self._attempt_unlock())

        self.lock_msg = ctk.CTkLabel(
            box, text="", font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.RED
        )
        self.lock_msg.pack(pady=6)

        ctk.CTkButton(
            box, text="UNLOCK RAPHAEL", width=280, height=42,
            fg_color=self.GOLD_ACCENT, hover_color=self.GOLD_BRIGHT,
            text_color="#070714", font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=10, command=self._attempt_unlock
        ).pack(pady=(10, 14))

    def _attempt_unlock(self):
        entered = self.pass_entry.get().strip()
        saved = self.engine.memory.get("passcode")
        if not saved:
            if entered:
                self.engine.set_passcode(entered)
                self.lock_msg.configure(text="● Passcode set & unlocked!", text_color=self.GREEN)
                self.root.after(700, self._unlock_ui)
            else:
                self._unlock_ui()
            return

        if self.engine.verify_passcode(entered):
            self.pass_entry.delete(0, "end")
            self.lock_msg.configure(text="● Access Granted", text_color=self.GREEN)
            self.root.after(400, self._unlock_ui)
        else:
            self.pass_entry.delete(0, "end")
            self.lock_msg.configure(text="⚠ ACCESS DENIED: Incorrect Passcode", text_color=self.RED)

    def _lock_ui(self):
        self.is_locked = True
        self.lock_msg.configure(text="")
        self.pass_entry.delete(0, "end")
        self.lock_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lock_frame.lift()
        self.pass_entry.focus_set()

    def _unlock_ui(self):
        self.is_locked = False
        self.lock_frame.place_forget()
        self.engine.speak("Security clearance granted. Celestial Edge online.")

    # ── Actions ────────────────────────────────────────────────────────────────
    def _open_research_vault(self, initial_topic=None):
        """Native In-App Celestial Research, Deep Search & Summary Vault."""
        if hasattr(self, "_research_win") and self._research_win is not None:
            try:
                if self._research_win.winfo_exists():
                    self._research_win.lift()
                    self._research_win.focus_force()
                    if initial_topic and hasattr(self, "_vault_entry") and self._vault_entry:
                        self._vault_entry.delete(0, "end")
                        self._vault_entry.insert(0, initial_topic)
                    return
            except Exception:
                pass

        vault = ctk.CTkToplevel(self.root)
        self._research_win = vault
        vault.title("RAPHAEL — Celestial Research & Deep Intelligence Vault")
        vault.geometry("1040x700")
        vault.minsize(860, 560)
        vault.configure(fg_color="#070714")

        # Top Bar
        top_bar = ctk.CTkFrame(vault, fg_color="#0c1022", height=60, corner_radius=0)
        top_bar.pack(fill="x")
        top_bar.pack_propagate(False)

        top_left = ctk.CTkFrame(top_bar, fg_color="transparent")
        top_left.pack(side="left", padx=16, pady=10)
        ctk.CTkLabel(
            top_left, text="🔬 CELESTIAL RESEARCH & DEEP SEARCH VAULT",
            font=ctk.CTkFont(family="Helvetica", size=15, weight="bold"),
            text_color="#38bdf8"
        ).pack(anchor="w")
        ctk.CTkLabel(
            top_left, text="Autonomous multi-source intelligence gathering, AI report synthesis & web summarization",
            font=ctk.CTkFont(family="Helvetica", size=10),
            text_color="#94a3b8"
        ).pack(anchor="w")

        top_right = ctk.CTkFrame(top_bar, fg_color="transparent")
        top_right.pack(side="right", padx=14, pady=10)

        def _open_folder():
            try:
                os.makedirs(RESEARCH_DIR, exist_ok=True)
                os.startfile(RESEARCH_DIR)
            except Exception as ex:
                status_lbl.configure(text=f"Error opening folder: {ex}")

        ctk.CTkButton(
            top_right, text="📂 Open Folder", width=105, height=28,
            fg_color="#1e293b", hover_color="#334155", text_color="#cbd5e1",
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=6,
            command=_open_folder
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            top_right, text="✕ Close", width=70, height=28,
            fg_color="#3f1d24", hover_color="#7f1d1d", text_color="#fca5a5",
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=6,
            command=vault.destroy
        ).pack(side="left")

        # Control Bar (Topic/URL Input + Actions)
        ctrl_frame = ctk.CTkFrame(vault, fg_color="#0f172a", corner_radius=8)
        ctrl_frame.pack(fill="x", padx=14, pady=10)

        input_row = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        input_row.pack(fill="x", padx=12, pady=(10, 6))

        vault_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Enter topic for Deep Research (e.g. Neuromorphic Computing) or URL to summarize...",
            font=ctk.CTkFont(size=12), fg_color="#070a14", text_color="#f8fafc",
            border_color="#334155", border_width=1, height=36
        )
        vault_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._vault_entry = vault_entry
        if initial_topic:
            vault_entry.insert(0, initial_topic)

        btn_row = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        status_lbl = ctk.CTkLabel(
            btn_row, text="● Ready • In-App Vault Operational",
            font=ctk.CTkFont(size=11), text_color="#64748b"
        )
        status_lbl.pack(side="left")

        btn_box = ctk.CTkFrame(btn_row, fg_color="transparent")
        btn_box.pack(side="right")

        # Split pane container (Left: Report list, Right: Viewer)
        body_frame = ctk.CTkFrame(vault, fg_color="transparent")
        body_frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        # Left: Reports sidebar
        left_pane = ctk.CTkFrame(body_frame, fg_color="#0d1124", width=310, corner_radius=8)
        left_pane.pack(side="left", fill="y", padx=(0, 10))
        left_pane.pack_propagate(False)

        left_hdr = ctk.CTkFrame(left_pane, fg_color="transparent")
        left_hdr.pack(fill="x", padx=10, pady=(10, 6))

        count_lbl = ctk.CTkLabel(
            left_hdr, text="Archived Reports",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#94a3b8"
        )
        count_lbl.pack(side="left")

        search_entry = ctk.CTkEntry(
            left_pane, placeholder_text="🔍 Filter reports...",
            height=28, font=ctk.CTkFont(size=11), fg_color="#070a14",
            border_color="#1e293b", text_color="#cbd5e1"
        )
        search_entry.pack(fill="x", padx=10, pady=(0, 6))

        list_scroll = ctk.CTkScrollableFrame(left_pane, fg_color="transparent")
        list_scroll.pack(fill="both", expand=True, padx=4, pady=(0, 6))

        # Right: Report viewer
        right_pane = ctk.CTkFrame(body_frame, fg_color="#0d1124", corner_radius=8)
        right_pane.pack(side="right", fill="both", expand=True)

        right_hdr = ctk.CTkFrame(right_pane, fg_color="#101730", height=48, corner_radius=8)
        right_hdr.pack(fill="x", padx=10, pady=8)
        right_hdr.pack_propagate(False)

        report_info = ctk.CTkFrame(right_hdr, fg_color="transparent")
        report_info.pack(side="left", padx=10, pady=4)

        report_title_lbl = ctk.CTkLabel(
            report_info, text="Select a report from the left pane or start a new search",
            font=ctk.CTkFont(size=12, weight="bold"), text_color="#f1f5f9"
        )
        report_title_lbl.pack(anchor="w")

        report_meta_lbl = ctk.CTkLabel(
            report_info, text="",
            font=ctk.CTkFont(size=10), text_color="#64748b"
        )
        report_meta_lbl.pack(anchor="w")

        right_tools = ctk.CTkFrame(right_hdr, fg_color="transparent")
        right_tools.pack(side="right", padx=10)

        speak_btn = ctk.CTkButton(
            right_tools, text="🔊 Speak", width=70, height=26,
            fg_color="#1e1b4b", hover_color="#2e2b6b", text_color="#a5b4fc",
            font=ctk.CTkFont(size=10, weight="bold"), corner_radius=6, state="disabled"
        )
        speak_btn.pack(side="left", padx=3)

        copy_btn = ctk.CTkButton(
            right_tools, text="📋 Copy", width=65, height=26,
            fg_color="#064e3b", hover_color="#047857", text_color="#6ee7b7",
            font=ctk.CTkFont(size=10, weight="bold"), corner_radius=6, state="disabled"
        )
        copy_btn.pack(side="left", padx=3)

        del_btn = ctk.CTkButton(
            right_tools, text="🗑 Delete", width=68, height=26,
            fg_color="#450a0a", hover_color="#7f1d1d", text_color="#fca5a5",
            font=ctk.CTkFont(size=10, weight="bold"), corner_radius=6, state="disabled"
        )
        del_btn.pack(side="left", padx=3)

        report_box = ctk.CTkTextbox(
            right_pane, font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#070a14", text_color="#f8fafc", wrap="word", corner_radius=6
        )
        report_box.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        report_box.insert("1.0", "Welcome to the Celestial Research Vault.\n\n"
                                 "• Type a topic above and click '🔬 Deep Research' to autonomously gather multi-source intelligence from DuckDuckGo and Wikipedia.\n"
                                 "• Or enter a URL and click '📄 Summarize URL' to distill any webpage into key takeaways.\n"
                                 "• Reports are archived locally and permanently indexed into Raphael's vector memory.")
        report_box.configure(state="disabled")

        selected_file = [None]

        def _load_report(filename):
            full_path = os.path.join(RESEARCH_DIR, filename)
            if not os.path.isfile(full_path):
                return
            selected_file[0] = full_path
            try:
                with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                report_title_lbl.configure(text=f"📄 {filename}")
                report_meta_lbl.configure(text=f"{len(content)} characters • {len(content.split())} words")
                report_box.configure(state="normal")
                report_box.delete("1.0", "end")
                report_box.insert("1.0", content)
                report_box.configure(state="disabled")
                speak_btn.configure(state="normal")
                copy_btn.configure(state="normal")
                del_btn.configure(state="normal")
            except Exception as ex:
                status_lbl.configure(text=f"Error reading {filename}: {ex}", text_color="#f87171")

        def _refresh_list(search_filter=""):
            for child in list_scroll.winfo_children():
                child.destroy()

            if not os.path.isdir(RESEARCH_DIR):
                os.makedirs(RESEARCH_DIR, exist_ok=True)

            files = [f for f in os.listdir(RESEARCH_DIR) if f.endswith(".md")]
            files.sort(key=lambda x: os.path.getmtime(os.path.join(RESEARCH_DIR, x)), reverse=True)

            filter_lower = search_filter.strip().lower()
            if filter_lower:
                files = [f for f in files if filter_lower in f.lower()]

            count_lbl.configure(text=f"{len(files)} Archived Reports")

            if not files:
                no_rep = ctk.CTkLabel(list_scroll, text="No reports found.\nStart a deep research or summarize a URL above!", font=ctk.CTkFont(size=11), text_color="#64748b")
                no_rep.pack(pady=20)
                return

            for fname in files:
                is_summary = fname.startswith("summary_")
                is_swarm = fname.startswith("swarm_")
                if is_swarm:
                    badge_text = "SWARM"
                    badge_bg = "#1e1b4b"
                    badge_fg = "#a5b4fc"
                elif is_summary:
                    badge_text = "SUMMARY"
                    badge_bg = "#3b0764"
                    badge_fg = "#d8b4fe"
                else:
                    badge_text = "RESEARCH"
                    badge_bg = "#082f49"
                    badge_fg = "#38bdf8"

                mtime = os.path.getmtime(os.path.join(RESEARCH_DIR, fname))
                dt_str = datetime.fromtimestamp(mtime).strftime("%b %d, %H:%M")

                clean_name = fname.replace("research_", "").replace("summary_", "").replace("swarm_", "").replace(".md", "")
                parts = clean_name.rsplit("_", 2)
                disp_title = parts[0].replace("_", " ").title() if len(parts) > 1 else clean_name

                card = ctk.CTkFrame(list_scroll, fg_color="#131936", corner_radius=6, border_color="#1e293b", border_width=1)
                card.pack(fill="x", padx=4, pady=3)

                hdr_row = ctk.CTkFrame(card, fg_color="transparent")
                hdr_row.pack(fill="x", padx=8, pady=(6, 2))

                ctk.CTkLabel(
                    hdr_row, text=badge_text,
                    font=ctk.CTkFont(size=9, weight="bold"),
                    fg_color=badge_bg, text_color=badge_fg,
                    corner_radius=4, padx=5, pady=1
                ).pack(side="left")

                ctk.CTkLabel(
                    hdr_row, text=dt_str,
                    font=ctk.CTkFont(size=9), text_color="#64748b"
                ).pack(side="right")

                title_lbl = ctk.CTkLabel(
                    card, text=disp_title,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color="#f1f5f9", anchor="w"
                )
                title_lbl.pack(fill="x", padx=8, pady=(0, 6))

                def _click(fn=fname):
                    _load_report(fn)

                card.bind("<Button-1>", lambda e, fn=fname: _click(fn))
                title_lbl.bind("<Button-1>", lambda e, fn=fname: _click(fn))
                hdr_row.bind("<Button-1>", lambda e, fn=fname: _click(fn))

        search_entry.bind("<KeyRelease>", lambda e: _refresh_list(search_entry.get()))

        def _speak_current():
            if selected_file[0] and os.path.isfile(selected_file[0]):
                try:
                    with open(selected_file[0], "r", encoding="utf-8", errors="replace") as f:
                        text = f.read()
                    cleaned = re.sub(r'[*#_`>|-]', ' ', text)
                    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                    self.engine.speak(cleaned[:800])
                    status_lbl.configure(text="🔊 Reading report aloud via Raphael voice engine...", text_color="#38bdf8")
                except Exception as ex:
                    status_lbl.configure(text=f"TTS error: {ex}", text_color="#f87171")

        def _copy_current():
            if selected_file[0] and os.path.isfile(selected_file[0]):
                try:
                    with open(selected_file[0], "r", encoding="utf-8", errors="replace") as f:
                        text = f.read()
                    vault.clipboard_clear()
                    vault.clipboard_append(text)
                    status_lbl.configure(text="📋 Report markdown copied to clipboard!", text_color="#22c55e")
                except Exception as ex:
                    status_lbl.configure(text=f"Copy error: {ex}", text_color="#f87171")

        def _delete_current():
            if selected_file[0] and os.path.isfile(selected_file[0]):
                try:
                    os.remove(selected_file[0])
                    status_lbl.configure(text="🗑 Report deleted successfully.", text_color="#f87171")
                    selected_file[0] = None
                    report_title_lbl.configure(text="Select a report from the left pane")
                    report_meta_lbl.configure(text="")
                    report_box.configure(state="normal")
                    report_box.delete("1.0", "end")
                    report_box.configure(state="disabled")
                    speak_btn.configure(state="disabled")
                    copy_btn.configure(state="disabled")
                    del_btn.configure(state="disabled")
                    _refresh_list(search_entry.get())
                except Exception as ex:
                    status_lbl.configure(text=f"Delete error: {ex}", text_color="#f87171")

        speak_btn.configure(command=_speak_current)
        copy_btn.configure(command=_copy_current)
        del_btn.configure(command=_delete_current)

        def _trigger_deep_research():
            topic = vault_entry.get().strip()
            if not topic:
                status_lbl.configure(text="⚠️ Please enter a research topic first.", text_color="#fbbf24")
                return
            status_lbl.configure(text=f"🚀 Deep research in progress on '{topic}'... Please wait.", text_color="#38bdf8")
            res_btn.configure(state="disabled")
            sum_btn.configure(state="disabled")
            clip_btn.configure(state="disabled")

            def _worker():
                try:
                    res, spoken = self.engine.deep_research(topic)
                    files = [f for f in os.listdir(RESEARCH_DIR) if f.endswith(".md") and "research_" in f]
                    files.sort(key=lambda x: os.path.getmtime(os.path.join(RESEARCH_DIR, x)), reverse=True)
                    latest = files[0] if files else None

                    def _ui_done():
                        status_lbl.configure(text=f"✅ Deep research complete on '{topic}'! Indexed to vector memory.", text_color="#22c55e")
                        res_btn.configure(state="normal")
                        sum_btn.configure(state="normal")
                        clip_btn.configure(state="normal")
                        _refresh_list()
                        if latest:
                            _load_report(latest)
                        self._append("Raphael", f"🔬 Deep Research complete on '{topic}'. Report saved and loaded into your Research Vault.")

                    vault.after(0, _ui_done)
                    self.engine.speak(spoken or f"Deep research on {topic} is complete and displayed in your vault.")
                except Exception as ex:
                    def _ui_err():
                        status_lbl.configure(text=f"❌ Error during research: {ex}", text_color="#f87171")
                        res_btn.configure(state="normal")
                        sum_btn.configure(state="normal")
                        clip_btn.configure(state="normal")
                    vault.after(0, _ui_err)

            threading.Thread(target=_worker, daemon=True).start()

        def _trigger_summarize_url():
            url = vault_entry.get().strip()
            if not url or ("http" not in url and "." not in url):
                status_lbl.configure(text="⚠️ Please enter a valid URL (e.g. https://example.com/article)", text_color="#fbbf24")
                return
            status_lbl.configure(text=f"📄 Summarizing webpage '{url}'... Please wait.", text_color="#38bdf8")
            res_btn.configure(state="disabled")
            sum_btn.configure(state="disabled")
            clip_btn.configure(state="disabled")

            def _worker():
                try:
                    res = self.engine.summarize_url(url)
                    files = [f for f in os.listdir(RESEARCH_DIR) if f.endswith(".md") and "summary_" in f]
                    files.sort(key=lambda x: os.path.getmtime(os.path.join(RESEARCH_DIR, x)), reverse=True)
                    latest = files[0] if files else None

                    def _ui_done():
                        status_lbl.configure(text=f"✅ Summary generated for {url}!", text_color="#22c55e")
                        res_btn.configure(state="normal")
                        sum_btn.configure(state="normal")
                        clip_btn.configure(state="normal")
                        _refresh_list()
                        if latest:
                            _load_report(latest)
                        self._append("Raphael", f"📄 Web Article Summary complete for '{url}'. Saved in your Research Vault.")

                    vault.after(0, _ui_done)
                    self.engine.speak(f"Web article summary is complete and saved.")
                except Exception as ex:
                    def _ui_err():
                        status_lbl.configure(text=f"❌ Error during summary: {ex}", text_color="#f87171")
                        res_btn.configure(state="normal")
                        sum_btn.configure(state="normal")
                        clip_btn.configure(state="normal")
                    vault.after(0, _ui_err)

            threading.Thread(target=_worker, daemon=True).start()

        def _trigger_clipboard_summary():
            try:
                clip_text = vault.clipboard_get()
            except Exception:
                clip_text = ""
            if not clip_text or len(clip_text.strip()) < 20:
                status_lbl.configure(text="⚠️ Clipboard is empty or contains less than 20 characters.", text_color="#fbbf24")
                return

            status_lbl.configure(text="📋 Summarizing clipboard text with AI... Please wait.", text_color="#38bdf8")
            res_btn.configure(state="disabled")
            sum_btn.configure(state="disabled")
            clip_btn.configure(state="disabled")

            def _worker():
                try:
                    prompt = (
                        "You are a research analyst. Summarize the following content in clear bullet points, "
                        f"highlighting key facts, takeaways, and action items:\n\n{clip_text[:7000]}"
                    )
                    summary = self.engine.ai_chat(prompt)
                    os.makedirs(RESEARCH_DIR, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    fn = f"summary_clipboard_{ts}.md"
                    p = os.path.join(RESEARCH_DIR, fn)
                    with open(p, "w", encoding="utf-8") as f:
                        f.write(f"# Clipboard Summary\n_Generated by Raphael AI on {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n{summary}")

                    def _ui_done():
                        status_lbl.configure(text="✅ Clipboard summary generated!", text_color="#22c55e")
                        res_btn.configure(state="normal")
                        sum_btn.configure(state="normal")
                        clip_btn.configure(state="normal")
                        _refresh_list()
                        _load_report(fn)
                        self._append("Raphael", "📋 Clipboard summary generated and loaded into your Research Vault.")

                    vault.after(0, _ui_done)
                    self.engine.speak("Clipboard content summarized and loaded into your vault.")
                except Exception as ex:
                    def _ui_err():
                        status_lbl.configure(text=f"❌ Error: {ex}", text_color="#f87171")
                        res_btn.configure(state="normal")
                        sum_btn.configure(state="normal")
                        clip_btn.configure(state="normal")
                    vault.after(0, _ui_err)

            threading.Thread(target=_worker, daemon=True).start()

        # Connect Buttons
        res_btn = ctk.CTkButton(
            btn_box, text="🔬 Deep Research", width=120, height=30,
            fg_color="#4f46e5", hover_color="#4338ca", text_color="#ffffff",
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=6,
            command=_trigger_deep_research
        )
        res_btn.pack(side="left", padx=4)

        sum_btn = ctk.CTkButton(
            btn_box, text="📄 Summarize URL", width=120, height=30,
            fg_color="#0284c7", hover_color="#0369a1", text_color="#ffffff",
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=6,
            command=_trigger_summarize_url
        )
        sum_btn.pack(side="left", padx=4)

        clip_btn = ctk.CTkButton(
            btn_box, text="📋 Summarize Clipboard", width=135, height=30,
            fg_color="#0d9488", hover_color="#0f766e", text_color="#ffffff",
            font=ctk.CTkFont(size=11, weight="bold"), corner_radius=6,
            command=_trigger_clipboard_summary
        )
        clip_btn.pack(side="left", padx=4)

        refresh_btn = ctk.CTkButton(
            btn_box, text="🔄", width=34, height=30,
            fg_color="#1e293b", hover_color="#334155", text_color="#cbd5e1",
            font=ctk.CTkFont(size=12, weight="bold"), corner_radius=6,
            command=lambda: _refresh_list(search_entry.get())
        )
        refresh_btn.pack(side="left", padx=4)

        # Initial load
        _refresh_list()
        files = [f for f in os.listdir(RESEARCH_DIR) if f.endswith(".md")] if os.path.isdir(RESEARCH_DIR) else []
        if files:
            files.sort(key=lambda x: os.path.getmtime(os.path.join(RESEARCH_DIR, x)), reverse=True)
            _load_report(files[0])

        vault.after(100, vault.lift)

    def _quick(self, cmd):
        if cmd == "__research_vault__":
            topic = self.entry.get().strip()
            self._open_research_vault(initial_topic=topic)
            return
        if cmd == "__lock__":
            self._lock_ui()
            return
        if self.is_locked:
            self._lock_ui()
            return
        if cmd == "__clear__":
            self.root.after(0, lambda: (
                self.log.configure(state="normal"),
                self.log.delete("1.0", "end"),
                self.log.configure(state="disabled")
            ))
            return
        if cmd == "__search_prompt__":
            q = self.entry.get().strip()
            if not q:
                self._append("System", "Type your search query in the bottom input box first.")
                return
            cmd = "search " + q
        if cmd == "__research__":
            topic = self.entry.get().strip()
            self._open_research_vault(initial_topic=topic)
            if topic:
                self._append("System", f"Opening Research Vault for: '{topic}'")
            return
        if cmd == "__open_app_dialog__":
            self._append("System", "Type or say 'open [app]' (e.g. 'open notepad', 'open vs code', 'open calculator').")
            self.entry.delete(0, "end")
            self.entry.insert(0, "open ")
            self.entry.focus_set()
            return
        self._append("You", cmd)
        self._add_recent_event(cmd)
        threading.Thread(target=self._process, args=(cmd,), daemon=True).start()

    def _send(self):
        if self.is_locked:
            self._lock_ui()
            return
        txt = self.entry.get().strip()
        if not txt:
            return
        self.entry.delete(0, "end")
        self._append("You", txt)
        self._add_recent_event(txt)
        threading.Thread(target=self._process, args=(txt,), daemon=True).start()

    def _process(self, text, is_voice=False):
        if self.is_locked:
            self.root.after(0, self._lock_ui)
            return
        try:
            r = self.engine.respond(text, is_voice=is_voice)
            if r == "__LOCK__":
                self.root.after(0, self._lock_ui)
            elif r:
                if isinstance(r, tuple):
                    disp = r[0]
                    spk = r[1] if len(r) > 1 else r[0]
                    self.engine.speak(disp, spoken_text=spk)
                else:
                    self.engine.speak(r)
        except Exception as e:
            self._append("System", "Error: " + str(e))

    def _voice(self):
        if self.is_locked:
            self.root.after(0, self._lock_ui)
            return
        def _work():
            self.root.after(0, lambda: (
                self.mic_btn.configure(fg_color=self.RED, text_color="#fff"),
                self.listen_pill.configure(text="🎙  Listening...", fg_color="#3d1414", text_color=self.RED, border_color=self.RED),
                self.status_dot.configure(text="● LISTENING", text_color=self.YELLOW, border_color=self.YELLOW),
            ))
            self.root.after(0, self._start_wave)
            text = self.engine.listen()
            self.root.after(0, self._stop_wave)
            self.root.after(0, lambda: (
                self.mic_btn.configure(fg_color="#201a08", text_color=self.GOLD_BRIGHT),
                self.listen_pill.configure(text="🎙  Tap to Speak", fg_color="#201a08", text_color=self.GOLD_BRIGHT, border_color=self.GOLD_ACCENT),
                self.status_dot.configure(text="● ONLINE", text_color=self.PURPLE_ACCENT, border_color=self.PURPLE_ACCENT),
            ))
            if text:
                self._append("You (Voice)", text)
                self._add_recent_event(text)
                self._process(text, is_voice=True)
            else:
                self._append("System", "Could not hear anything. Please try again.")
        threading.Thread(target=_work, daemon=True).start()

    # ── System Tray ────────────────────────────────────────────────────────────
    def _setup_tray(self):
        if not TRAY_AVAILABLE:
            return
        try:
            icon_img = _make_tray_icon()
            if not icon_img:
                return
            menu = pystray.Menu(
                pystray.MenuItem("Show Raphael", self.show_from_tray, default=True),
                pystray.MenuItem("System Status", lambda icon, item: self._quick("system status")),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self.exit_app),
            )
            self.tray = pystray.Icon("Raphael", icon_img, "Raphael AI — Celestial Edge", menu)
            threading.Thread(target=self.tray.run, daemon=True).start()
        except Exception as e:
            print("[Tray]", str(e))

    def hide_window_sync(self):
        done = threading.Event()
        def _do():
            try:
                self.root.withdraw()
            finally:
                done.set()
        self.root.after(0, _do)
        done.wait(timeout=2.0)

    def show_window_sync(self):
        done = threading.Event()
        def _do():
            try:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
            finally:
                done.set()
        self.root.after(0, _do)
        done.wait(timeout=2.0)

    def hide_to_tray(self):
        self.root.withdraw()

    def show_from_tray(self, icon=None, item=None):
        def _show():
            try:
                self.root.deiconify()
                self.root.state("normal")
                if IS_WINDOWS:
                    import ctypes
                    user32 = ctypes.windll.user32
                    kernel32 = ctypes.windll.kernel32
                    self.root.lift()
                    self.root.attributes("-topmost", True)
                    self.root.after(300, lambda: self.root.attributes("-topmost", False))
                    self.root.focus_force()
                    hwnd = user32.FindWindowW(None, "Raphael AI - Celestial Edge") or user32.FindWindowW(None, "Raphael AI — Celestial Edge")
                    if not hwnd:
                        try:
                            hwnd = int(self.root.wm_frame(), 16)
                        except Exception:
                            hwnd = None
                    if hwnd:
                        fore_hwnd = user32.GetForegroundWindow()
                        cur_thread = kernel32.GetCurrentThreadId()
                        fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None)
                        if cur_thread != fore_thread and fore_thread != 0:
                            user32.AttachThreadInput(cur_thread, fore_thread, True)
                            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                            user32.SetForegroundWindow(hwnd)
                            user32.BringWindowToTop(hwnd)
                            user32.AttachThreadInput(cur_thread, fore_thread, False)
                        else:
                            user32.ShowWindow(hwnd, 9)
                            user32.SetForegroundWindow(hwnd)
                            user32.BringWindowToTop(hwnd)

                self.root.attributes("-topmost", True)
                self.root.update_idletasks()
                self.root.attributes("-topmost", False)
                self.root.lift()
                self.root.focus_force()
                if hasattr(self, "entry"):
                    self.entry.focus_set()
            except Exception as e:
                print("[Show Window Error]", e)
        self.root.after(0, _show)

    def exit_app(self, icon=None, item=None):
        try:
            self.tray.stop()
        except Exception:
            pass
        try:
            self.root.after(0, self.root.destroy)
        except Exception:
            pass
        os._exit(0)

    def run(self):
        self.root.mainloop()


