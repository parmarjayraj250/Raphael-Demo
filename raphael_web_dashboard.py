import os, sys, time, json, asyncio, secrets, threading, psutil, socket, re
from datetime import datetime

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    Depends = lambda x=None: None
    class HTTPAuthorizationCredentials: pass

security = HTTPBearer(auto_error=False) if FASTAPI_AVAILABLE else None

RESEARCH_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raphael_research")

class RaphaelWebDashboard:
    """
    Token-Authenticated Mobile Companion Dashboard & Research Vault:
    - Instant Open Access or 6-digit short-lived pairing code
    - Dedicated Research & Summary Vault page (/research) with live report viewing & synthesis
    - Full bidirectional PC Control (Apps, Keyboard, Mouse, Media, Screen OCR, Voice)
    - Audio output on PC speakers when commanded from mobile
    - Glassmorphic Celestial Gold/Indigo mobile UI
    """
    def __init__(self, raphael_engine, safety_manager, port=8765, open_access=False):
        self.engine = raphael_engine
        self.safety_manager = safety_manager
        self.port = port
        self.host = "127.0.0.1"
        self.open_access = open_access
        self.research_dir = RESEARCH_DIR
        os.makedirs(self.research_dir, exist_ok=True)
        self._server_thread = None
        self._master_token = secrets.token_hex(32)
        self._active_tokens = {self._master_token}
        self._ws_clients = set()
        self._loop = None
        self._pairing_code = None
        self._pairing_expiry = 0
        self._failed_attempts = 0
        self._lockout_until = 0

        if FASTAPI_AVAILABLE:
            from fastapi.middleware.cors import CORSMiddleware
            self.app = FastAPI(title="Raphael Mobile Companion & Research Vault")
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
            self._setup_routes()
        else:
            self.app = None

    def get_local_ip(self) -> str:
        """Auto-detects the real LAN IP of this machine."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def push_to_mobile(self, text: str):
        """Pushes a Raphael reply live to all connected authenticated WebSocket clients."""
        import asyncio, json
        if not self._ws_clients or not self._loop:
            return
        msg = json.dumps({"type": "reply", "text": text})
        dead = set()
        for ws in list(self._ws_clients):
            try:
                future = asyncio.run_coroutine_threadsafe(ws.send_text(msg), self._loop)
                future.result(timeout=2)
            except Exception:
                dead.add(ws)
        self._ws_clients -= dead

    def generate_pairing_code(self) -> str:
        """Generates a temporary 6-digit pairing code valid for 180 seconds."""
        self._pairing_code = f"{secrets.randbelow(900000) + 100000}"
        self._pairing_expiry = time.time() + 180
        self.safety_manager.log_audit("WEB_AUTH", "PAIRING_CODE_GENERATED", "INFO", True, "Expires in 180s")
        return self._pairing_code

    def _verify_token(self, creds: HTTPAuthorizationCredentials = Depends(security)):
        if self.open_access:
            return self._master_token
        if not creds or creds.credentials not in self._active_tokens:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing Bearer token")
        return creds.credentials

    def _setup_routes(self):
        # ── 1. MAIN REMOTE CONTROL HTML ──
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Raphael — Mobile Companion & PC Remote</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; -webkit-tap-highlight-color: transparent; }
        body { background: #070714; color: #f8fafc; padding: 14px; max-width: 520px; margin: auto; padding-bottom: 30px; }
        .header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 12px; border-bottom: 1px solid #1e1e48; }
        .title { color: #f5a623; font-weight: bold; font-size: 1.15rem; letter-spacing: 1px; display: flex; align-items: center; gap: 6px; }
        .badge { background: #18183c; color: #10b981; padding: 5px 11px; border-radius: 12px; font-size: 0.75rem; border: 1px solid #10b981; font-weight: bold; text-decoration: none; display: inline-flex; align-items: center; gap: 4px; }
        .card { background: #0f1026; border: 1px solid #1e1e48; border-radius: 14px; padding: 14px; margin-top: 14px; box-shadow: 0 4px 14px rgba(0,0,0,0.4); }
        .card-title { font-size: 0.8rem; color: #8e8ea8; font-weight: bold; letter-spacing: 0.5px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }
        .gauges { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; text-align: center; }
        .gauge-val { font-size: 1.35rem; font-weight: bold; color: #f5a623; margin-top: 2px; }
        
        .grid-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
        .grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
        .grid-2 { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }

        .btn-ctrl { background: #141436; color: #f8fafc; border: 1px solid #242458; padding: 10px 6px; border-radius: 10px; font-size: 0.8rem; font-weight: 600; cursor: pointer; text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; transition: all 0.15s; }
        .btn-ctrl:active { background: #f5a623; color: #070714; transform: scale(0.96); border-color: #f5a623; }
        .btn-icon { font-size: 1.15rem; }

        .media-btn { background: #18183c; color: #f8fafc; padding: 9px 8px; border-radius: 9px; border: 1px solid #2e2e68; font-size: 0.82rem; font-weight: 600; cursor: pointer; text-align: center; }
        .media-btn:active { background: #6366f1; color: #fff; transform: scale(0.96); }

        .chat-box { height: 220px; overflow-y: auto; background: #070714; border: 1px solid #1e1e48; border-radius: 10px; padding: 10px; margin-top: 10px; font-size: 0.88rem; }
        .msg { margin-bottom: 8px; line-height: 1.4; }
        .msg.you { color: #a5b4fc; }
        .msg.raphael { color: #f5a623; }
        
        .input-row { display: flex; gap: 8px; margin-top: 10px; }
        input { flex: 1; padding: 11px 14px; background: #0c0c24; border: 1px solid #242454; color: #fff; border-radius: 10px; outline: none; font-size: 0.9rem; }
        input:focus { border-color: #f5a623; }
        button.send-btn { background: #f5a623; border: none; padding: 11px 18px; color: #070714; font-weight: bold; border-radius: 10px; cursor: pointer; font-size: 0.9rem; }
        button.send-btn:active { transform: scale(0.96); }

        .voice-pill { display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%; background: #1c1917; border: 1.5px solid #f5a623; color: #f5a623; padding: 12px; border-radius: 12px; font-weight: bold; font-size: 0.95rem; cursor: pointer; transition: all 0.2s; margin-top: 10px; text-decoration: none; }
        .voice-pill.listening { background: #7f1d1d; border-color: #ef4444; color: #fff; animation: pulse 1.2s infinite; }
        @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(239,68,68,0.7); } 70% { box-shadow: 0 0 0 12px rgba(239,68,68,0); } 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); } }

        #auth-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #070714; display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 20px; z-index: 99; }
    </style>
</head>
<body>
    __AUTH_OVERLAY_HTML__

    <div class="header">
        <div class="title">⚡ RAPHAEL REMOTE</div>
        <div style="display:flex; gap:6px; align-items:center;">
            <a href="/research" class="badge" style="background:#241406; color:#f5a623; border-color:#d97706;">🔬 RESEARCH VAULT ↗</a>
            <div class="badge" id="conn-badge">● ONLINE</div>
        </div>
    </div>

    <!-- Voice Control -->
    <button class="voice-pill" id="voice-btn" onclick="toggleVoice()">
        <span id="voice-icon">🎙</span> <span id="voice-txt">Tap to Speak to PC</span>
    </button>

    <!-- NEW: Research & Summary Portal Card -->
    <div class="card" style="border: 1px solid #6366f1; background: linear-gradient(135deg, #0e0e2a 0%, #17183e 100%);">
        <div class="card-title" style="color: #a5b4fc;">
            <span>🔬 RESEARCH & SUMMARY VAULT</span>
            <span style="color:#f5a623; font-size:0.75rem;">INTELLIGENCE HUB</span>
        </div>
        <p style="font-size:0.83rem; color:#8e8ea8; margin-bottom:12px; line-height:1.4;">
            View deep research reports, web article summaries, and data synthesized by Raphael. Read full findings or run new research live.
        </p>
        <a href="/research" style="text-decoration: none;">
            <button class="voice-pill" style="margin-top:0; background:#1e1b4b; border-color:#6366f1; color:#c7d2fe; font-size:0.9rem; padding:11px;">
                <span>📚 Open Research & Summaries Page →</span>
            </button>
        </a>
    </div>

    <!-- System Gauges -->
    <div class="card">
        <div class="card-title"><span>PC HARDWARE STATUS</span><span id="pc-speaker-status" style="color:#10b981;">🔊 Voice Active</span></div>
        <div class="gauges">
            <div><div style="font-size:0.75rem; color:#8e8ea8;">CPU</div><div class="gauge-val" id="cpu-val">--%</div></div>
            <div><div style="font-size:0.75rem; color:#8e8ea8;">RAM</div><div class="gauge-val" id="ram-val">--%</div></div>
            <div><div style="font-size:0.75rem; color:#8e8ea8;">DISK</div><div class="gauge-val" id="disk-val">--%</div></div>
        </div>
    </div>

    <!-- PC Apps & Navigation -->
    <div class="card">
        <div class="card-title">PC APPS & SYSTEM CONTROLS</div>
        <div class="grid-4">
            <button class="btn-ctrl" onclick="execCommand('open notepad')"><span class="btn-icon">📝</span>Notepad</button>
            <button class="btn-ctrl" onclick="execCommand('open chrome')"><span class="btn-icon">🌐</span>Chrome</button>
            <button class="btn-ctrl" onclick="execCommand('open calc')"><span class="btn-icon">🧮</span>Calculator</button>
            <button class="btn-ctrl" onclick="execCommand('open explorer')"><span class="btn-icon">📁</span>Explorer</button>
            <button class="btn-ctrl" onclick="execCommand('show desktop')"><span class="btn-icon">💻</span>Desktop</button>
            <button class="btn-ctrl" onclick="execCommand('read screen')"><span class="btn-icon">📸</span>Read Screen</button>
            <button class="btn-ctrl" onclick="execCommand('read clipboard')"><span class="btn-icon">📋</span>Clipboard</button>
            <button class="btn-ctrl" onclick="execCommand('lock pc')"><span class="btn-icon">🔒</span>Lock PC</button>
        </div>
    </div>

    <!-- Mouse & Keyboard Actions -->
    <div class="card">
        <div class="card-title">PC KEYBOARD & MOUSE CONTROLS</div>
        <div class="grid-4">
            <button class="btn-ctrl" onclick="execCommand('scroll up')"><span class="btn-icon">⬆</span>Scroll Up</button>
            <button class="btn-ctrl" onclick="execCommand('scroll down')"><span class="btn-icon">⬇</span>Scroll Down</button>
            <button class="btn-ctrl" onclick="execCommand('press enter')"><span class="btn-icon">↵</span>Enter</button>
            <button class="btn-ctrl" onclick="execCommand('click')"><span class="btn-icon">🖱</span>Click</button>
        </div>
        <div class="input-row" style="margin-top: 10px;">
            <input type="text" id="type-pc-input" placeholder="Type text directly onto PC screen..." onkeydown="if(event.key==='Enter') sendTypeToPC()">
            <button class="send-btn" style="background:#6366f1; color:#fff;" onclick="sendTypeToPC()">Type</button>
        </div>
    </div>

    <!-- Media Controls -->
    <div class="card">
        <div class="card-title">MEDIA & AUDIO CONTROLS</div>
        <div class="grid-3">
            <button class="media-btn" onclick="sendMedia('previous song')">⏮ Prev</button>
            <button class="media-btn" onclick="sendMedia('pause music')">⏯ Play/Pause</button>
            <button class="media-btn" onclick="sendMedia('next song')">⏭ Next</button>
        </div>
        <div class="grid-3" style="margin-top: 8px;">
            <button class="media-btn" onclick="sendMedia('volume down')">🔉 Vol -</button>
            <button class="media-btn" onclick="sendMedia('mute')">🔇 Mute</button>
            <button class="media-btn" onclick="sendMedia('volume up')">🔊 Vol +</button>
        </div>
    </div>

    <!-- AI Chat & Command Box -->
    <div class="card">
        <div class="card-title">COMMAND & AI CONSOLE</div>
        <div style="display:flex; gap:6px; overflow-x:auto; padding-bottom: 4px;">
            <button class="media-btn" style="font-size:0.75rem; padding:6px 10px; white-space:nowrap;" onclick="quickPrompt('what is the weather')">☁ Weather</button>
            <button class="media-btn" style="font-size:0.75rem; padding:6px 10px; white-space:nowrap;" onclick="quickPrompt('system status')">⚡ Status</button>
            <button class="media-btn" style="font-size:0.75rem; padding:6px 10px; white-space:nowrap;" onclick="quickPrompt('latest news')">📰 News</button>
            <button class="media-btn" style="font-size:0.75rem; padding:6px 10px; white-space:nowrap;" onclick="quickPrompt('suggest something interesting')">💡 Suggest</button>
        </div>
        <div class="chat-box" id="chat">
            <div class="msg raphael">Raphael: Mobile Remote ready. Every command controls your PC and speaks back aloud.</div>
        </div>
        <div class="input-row">
            <input type="text" id="prompt-input" placeholder="Type command (e.g. open chrome, deep research AI)..." onkeydown="if(event.key==='Enter') sendChat()">
            <button class="send-btn" onclick="sendChat()">Send</button>
        </div>
    </div>

    <script>
        let token = "__TOKEN__" || localStorage.getItem("raphael_token") || "";
        const ov = document.getElementById("auth-overlay");
        if (token && ov) {
            ov.style.display = "none";
        }
        refreshStatus();

        async function submitPairing() {
            const inp = document.getElementById("pairing-input");
            const code = inp ? inp.value.trim() : "";
            try {
                const res = await fetch("/api/pair", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ code: code })
                });
                const data = await res.json();
                if (data.token) {
                    token = data.token;
                    localStorage.setItem("raphael_token", token);
                    const ovEl = document.getElementById("auth-overlay");
                    if (ovEl) ovEl.style.display = "none";
                    refreshStatus();
                } else {
                    document.getElementById("pair-err").innerText = data.detail || "Pairing failed.";
                }
            } catch (e) {
                token = "__TOKEN__" || "open_access";
                const ovEl = document.getElementById("auth-overlay");
                if (ovEl) ovEl.style.display = "none";
                refreshStatus();
            }
        }

        async function refreshStatus() {
            try {
                const headers = token ? { "Authorization": "Bearer " + token } : {};
                const res = await fetch("/api/status", { headers: headers });
                if (res.ok) {
                    const d = await res.json();
                    document.getElementById("cpu-val").innerText = (d.cpu !== undefined ? d.cpu : "--") + "%";
                    document.getElementById("ram-val").innerText = (d.ram !== undefined ? d.ram : "--") + "%";
                    document.getElementById("disk-val").innerText = (d.disk !== undefined ? d.disk : "--") + "%";
                    const bdg = document.getElementById("conn-badge");
                    if (bdg) { bdg.innerText = "● ONLINE"; bdg.style.color = "#10b981"; }
                }
            } catch (e) {
                const bdg = document.getElementById("conn-badge");
                if (bdg) { bdg.innerText = "● CONNECTING"; bdg.style.color = "#f5a623"; }
            }
            setTimeout(refreshStatus, 3000);
        }

        function quickPrompt(txt) {
            const inp = document.getElementById("prompt-input");
            inp.value = txt;
            sendChat();
        }

        function execCommand(cmd) {
            const inp = document.getElementById("prompt-input");
            inp.value = cmd;
            sendChat();
        }

        function sendTypeToPC() {
            const inp = document.getElementById("type-pc-input");
            const txt = inp.value.trim();
            if (!txt) return;
            inp.value = "";
            execCommand("type " + txt);
        }

        async function sendChat() {
            const inp = document.getElementById("prompt-input");
            const txt = inp.value.trim();
            if (!txt) return;
            inp.value = "";
            appendMsg("You", txt, "you");

            try {
                const headers = { "Content-Type": "application/json" };
                if (token) headers["Authorization"] = "Bearer " + token;
                const res = await fetch("/api/chat", {
                    method: "POST",
                    headers: headers,
                    body: JSON.stringify({ prompt: txt })
                });
                const d = await res.json();
                appendMsg("Raphael", d.reply || "Done.", "raphael");
            } catch(e) {
                appendMsg("Raphael", "Connection error. Reconnecting...", "raphael");
            }
        }

        function sendMedia(cmd) {
            appendMsg("Media", cmd, "you");
            const headers = { "Content-Type": "application/json" };
            if (token) headers["Authorization"] = "Bearer " + token;
            fetch("/api/media", {
                method: "POST",
                headers: headers,
                body: JSON.stringify({ command: cmd })
            }).then(r => r.json()).then(d => {
                if (d.detail) appendMsg("Raphael", d.detail, "raphael");
            }).catch(e => {});
        }

        function appendMsg(sender, text, cls) {
            const box = document.getElementById("chat");
            const el = document.createElement("div");
            el.className = "msg " + cls;
            el.textContent = sender + ": " + text;
            box.appendChild(el);
            box.scrollTop = box.scrollHeight;
        }

        // Web Speech API for voice command from mobile
        let recognition = null;
        let isListening = false;
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRec();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';

            recognition.onstart = function() {
                isListening = true;
                const btn = document.getElementById("voice-btn");
                btn.className = "voice-pill listening";
                document.getElementById("voice-txt").innerText = "Listening... Speak now";
            };

            recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                document.getElementById("voice-txt").innerText = "Heard: " + transcript;
                setTimeout(() => {
                    const inp = document.getElementById("prompt-input");
                    inp.value = transcript;
                    sendChat();
                }, 500);
            };

            recognition.onerror = function(event) {
                isListening = false;
                resetVoiceBtn();
            };

            recognition.onend = function() {
                isListening = false;
                setTimeout(resetVoiceBtn, 1200);
            };
        }

        function toggleVoice() {
            if (!recognition) {
                alert("Speech recognition is not supported on this browser. Try Chrome or Safari.");
                return;
            }
            if (isListening) {
                recognition.stop();
            } else {
                recognition.start();
            }
        }

        function resetVoiceBtn() {
            const btn = document.getElementById("voice-btn");
            btn.className = "voice-pill";
            document.getElementById("voice-txt").innerText = "Tap to Speak to PC";
        }
    </script>
</body>
</html>
"""

        # ── 2. DEDICATED RESEARCH & SUMMARY VAULT PAGE HTML ──
        research_html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Raphael — Research & Summary Vault</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; -webkit-tap-highlight-color: transparent; }
        body { background: #070714; color: #f8fafc; padding: 14px; max-width: 680px; margin: auto; padding-bottom: 40px; }
        .header { display: flex; justify-content: space-between; align-items: center; padding-bottom: 12px; border-bottom: 1px solid #1e1e48; }
        .title { color: #f5a623; font-weight: bold; font-size: 1.15rem; letter-spacing: 0.8px; display: flex; align-items: center; gap: 8px; }
        .nav-btn { background: #141436; color: #a5b4fc; border: 1px solid #242458; padding: 7px 12px; border-radius: 10px; font-size: 0.82rem; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; gap: 5px; }
        .nav-btn:hover { background: #222258; color: #fff; }
        .badge { background: #18183c; color: #10b981; padding: 4px 10px; border-radius: 12px; font-size: 0.75rem; border: 1px solid #10b981; font-weight: bold; }
        
        .card { background: #0f1026; border: 1px solid #1e1e48; border-radius: 14px; padding: 16px; margin-top: 14px; box-shadow: 0 4px 16px rgba(0,0,0,0.4); }
        .card-title { font-size: 0.85rem; color: #8e8ea8; font-weight: bold; letter-spacing: 0.5px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; }

        .input-row { display: flex; gap: 8px; margin-top: 10px; }
        input[type="text"] { flex: 1; padding: 12px 14px; background: #0c0c24; border: 1px solid #242454; color: #fff; border-radius: 10px; outline: none; font-size: 0.92rem; }
        input[type="text"]:focus { border-color: #f5a623; }

        .btn-action { background: #f5a623; border: none; padding: 11px 16px; color: #070714; font-weight: bold; border-radius: 10px; cursor: pointer; font-size: 0.88rem; transition: transform 0.1s; display: inline-flex; align-items: center; gap: 5px; }
        .btn-action:active { transform: scale(0.96); }
        .btn-purple { background: #6366f1; color: #fff; }
        .btn-sub { background: #18183c; color: #e2e8f0; border: 1px solid #2e2e68; }

        .filter-row { display: flex; gap: 8px; overflow-x: auto; margin-top: 14px; padding-bottom: 2px; }
        .filter-chip { background: #141436; color: #8e8ea8; border: 1px solid #242458; padding: 6px 14px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; cursor: pointer; white-space: nowrap; }
        .filter-chip.active { background: #221c48; color: #f5a623; border-color: #f5a623; }

        .report-item { background: #0b0c20; border: 1px solid #1a1b42; border-radius: 12px; padding: 14px; margin-top: 12px; transition: border-color 0.2s; }
        .report-item:hover { border-color: #6366f1; }
        .report-header { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; margin-bottom: 8px; }
        .report-tag { font-size: 0.7rem; font-weight: bold; padding: 3px 8px; border-radius: 6px; letter-spacing: 0.5px; text-transform: uppercase; }
        .tag-research { background: #261906; color: #f5a623; border: 1px solid #d97706; }
        .tag-summary { background: #101938; color: #818cf8; border: 1px solid #4338ca; }
        .report-title { font-size: 1rem; font-weight: bold; color: #f8fafc; line-height: 1.3; }
        .report-date { font-size: 0.75rem; color: #64748b; margin-top: 3px; }
        .report-snippet { font-size: 0.84rem; color: #94a3b8; line-height: 1.45; margin: 8px 0; max-height: 58px; overflow: hidden; text-overflow: ellipsis; }

        .report-actions { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
        .btn-sm { padding: 6px 12px; font-size: 0.78rem; border-radius: 8px; font-weight: 600; cursor: pointer; border: none; display: inline-flex; align-items: center; gap: 4px; }
        .btn-view { background: #6366f1; color: #fff; }
        .btn-speak { background: #1e1b4b; color: #a5b4fc; border: 1px solid #4338ca; }
        .btn-copy { background: #141436; color: #cbd5e1; border: 1px solid #242458; }
        .btn-del { background: #261118; color: #f87171; border: 1px solid #7f1d1d; margin-left: auto; }

        /* Modal Reader */
        .modal-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(7, 7, 20, 0.95); display: none; justify-content: center; align-items: center; padding: 14px; z-index: 999; backdrop-filter: blur(8px); }
        .modal-content { background: #0c0d24; border: 1px solid #2c2d66; border-radius: 16px; width: 100%; max-width: 650px; max-height: 90vh; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.8); }
        .modal-header { padding: 14px 18px; border-bottom: 1px solid #1e1e48; display: flex; justify-content: space-between; align-items: center; }
        .modal-body { padding: 18px; overflow-y: auto; font-size: 0.92rem; line-height: 1.6; color: #e2e8f0; white-space: pre-wrap; }
        .modal-footer { padding: 12px 18px; border-top: 1px solid #1e1e48; display: flex; gap: 8px; justify-content: flex-end; background: #08091a; }

        .spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(255,255,255,0.3); border-radius: 50%; border-top-color: #fff; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="header">
        <a href="/" class="nav-btn">← Back to Remote</a>
        <div class="title">🔬 RESEARCH VAULT</div>
        <div class="badge" id="report-count-badge">● 0 REPORTS</div>
    </div>

    <!-- Generator Card -->
    <div class="card" style="border: 1px solid #f5a623; background: linear-gradient(135deg, #100f26 0%, #1c1538 100%);">
        <div class="card-title" style="color: #f5a623;">
            <span>🚀 SYNTHESIZE NEW RESEARCH OR SUMMARY</span>
            <span style="font-size:0.75rem; color:#a5b4fc;">AI MULTI-SOURCE</span>
        </div>
        <p style="font-size:0.82rem; color:#8e8ea8; margin-bottom:8px;">
            Enter any topic to conduct deep multi-source research, or paste a webpage URL to extract key takeaways.
        </p>
        <div class="input-row">
            <input type="text" id="research-input" placeholder="e.g. Neuromorphic Computing or https://example.com/article" onkeydown="if(event.key==='Enter') runResearch('research')">
        </div>
        <div style="display:flex; gap:8px; margin-top:10px;">
            <button class="btn-action" id="btn-deep-res" onclick="runResearch('research')">
                <span id="res-icon">🔬</span> <span>Deep Research</span>
            </button>
            <button class="btn-action btn-purple" id="btn-sum" onclick="runResearch('summarize')">
                <span id="sum-icon">📄</span> <span>Summarize URL / Text</span>
            </button>
        </div>
        <div id="status-banner" style="display:none; margin-top:12px; padding:10px; border-radius:8px; font-size:0.83rem; background:#1e1a38; border:1px solid #6366f1; color:#c7d2fe; display:none; align-items:center; gap:8px;">
            <span class="spinner"></span>
            <span id="status-text">Raphael is conducting multi-source research on PC...</span>
        </div>
    </div>

    <!-- Search & Filter -->
    <div class="filter-row">
        <div class="filter-chip active" onclick="setFilter('all', this)">All Reports</div>
        <div class="filter-chip" onclick="setFilter('research', this)">🔬 Deep Research</div>
        <div class="filter-chip" onclick="setFilter('summary', this)">📄 Summaries</div>
    </div>

    <!-- Reports Container -->
    <div id="reports-container" style="margin-top: 10px;">
        <div style="text-align:center; padding:30px; color:#64748b; font-size:0.9rem;">Loading research reports...</div>
    </div>

    <!-- Modal Reader -->
    <div class="modal-overlay" id="reader-modal" onclick="if(event.target===this) closeModal()">
        <div class="modal-content">
            <div class="modal-header">
                <div>
                    <h3 id="modal-title" style="color:#f5a623; font-size:1.05rem;">Report Title</h3>
                    <div id="modal-date" style="font-size:0.75rem; color:#64748b; margin-top:2px;">Date</div>
                </div>
                <button onclick="closeModal()" style="background:transparent; border:none; color:#8e8ea8; font-size:1.4rem; cursor:pointer;">✕</button>
            </div>
            <div class="modal-body" id="modal-body"></div>
            <div class="modal-footer">
                <button class="btn-sm btn-speak" onclick="speakCurrentReport()">🔊 Speak on PC</button>
                <button class="btn-sm btn-copy" onclick="copyCurrentReport()">📋 Copy Report</button>
                <button class="btn-sm btn-action" onclick="closeModal()">Close</button>
            </div>
        </div>
    </div>

    <script>
        let allReports = [];
        let currentFilter = 'all';
        let activeReport = null;

        async function fetchReports() {
            try {
                const res = await fetch('/api/research');
                if (res.ok) {
                    const data = await res.json();
                    allReports = data.reports || [];
                    document.getElementById('report-count-badge').innerText = `● ${allReports.length} REPORTS`;
                    renderReports();
                }
            } catch(e) {
                document.getElementById('reports-container').innerHTML = '<div style="text-align:center; padding:20px; color:#ef4444;">Failed to load reports.</div>';
            }
        }

        function setFilter(flt, el) {
            currentFilter = flt;
            document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
            el.classList.add('active');
            renderReports();
        }

        function renderReports() {
            const container = document.getElementById('reports-container');
            let filtered = allReports;
            if (currentFilter !== 'all') {
                filtered = allReports.filter(r => r.type === currentFilter);
            }

            if (!filtered || filtered.length === 0) {
                container.innerHTML = '<div style="text-align:center; padding:40px; color:#64748b; font-size:0.9rem;">No reports found in this category. Synthesize one above!</div>';
                return;
            }

            let html = '';
            filtered.forEach(r => {
                const isResearch = r.type === 'research';
                const tagClass = isResearch ? 'tag-research' : 'tag-summary';
                const tagText = isResearch ? '🔬 Deep Research' : '📄 Summary';
                html += `
                <div class="report-item">
                    <div class="report-header">
                        <div>
                            <span class="report-tag ${tagClass}">${tagText}</span>
                            <div class="report-title" style="margin-top:6px;">${escapeHtml(r.title)}</div>
                            <div class="report-date">${r.date} • ${(r.size_bytes / 1024).toFixed(1)} KB</div>
                        </div>
                    </div>
                    <div class="report-snippet">${escapeHtml(r.snippet)}</div>
                    <div class="report-actions">
                        <button class="btn-sm btn-view" onclick="openReport('${r.filename}')">📖 Read Full Report</button>
                        <button class="btn-sm btn-speak" onclick="speakReport('${escapeQuotes(r.title)}')">🔊 Speak on PC</button>
                        <button class="btn-sm btn-copy" onclick="quickCopyReport('${r.filename}')">📋 Copy</button>
                        <button class="btn-sm btn-del" onclick="deleteReport('${r.filename}')">🗑 Delete</button>
                    </div>
                </div>
                `;
            });
            container.innerHTML = html;
        }

        async function openReport(filename) {
            try {
                const res = await fetch(`/api/research/${encodeURIComponent(filename)}`);
                if (res.ok) {
                    const data = await res.json();
                    activeReport = data;
                    document.getElementById('modal-title').innerText = data.title;
                    document.getElementById('modal-date').innerText = `${data.type.toUpperCase()} • ${data.date}`;
                    document.getElementById('modal-body').innerText = data.content;
                    document.getElementById('reader-modal').style.display = 'flex';
                }
            } catch(e) {
                alert('Could not open report.');
            }
        }

        function closeModal() {
            document.getElementById('reader-modal').style.display = 'none';
            activeReport = null;
        }

        async function runResearch(mode) {
            const inp = document.getElementById('research-input');
            const topic = inp.value.trim();
            if (!topic) {
                alert('Please enter a research topic or URL.');
                return;
            }

            const banner = document.getElementById('status-banner');
            const statusTxt = document.getElementById('status-text');
            banner.style.display = 'flex';
            statusTxt.innerText = mode === 'research' 
                ? `Raphael is conducting deep multi-source research on '${topic}' on PC...`
                : `Raphael is fetching and summarizing '${topic}' on PC...`;

            try {
                const res = await fetch('/api/research', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ topic: topic, mode: mode })
                });
                const d = await res.json();
                banner.style.display = 'none';
                inp.value = '';
                await fetchReports();
                if (d.filename) {
                    openReport(d.filename);
                }
            } catch(e) {
                banner.style.display = 'none';
                alert('Research process encountered an error.');
            }
        }

        async function deleteReport(filename) {
            if (!confirm('Are you sure you want to delete this report?')) return;
            try {
                const res = await fetch(`/api/research/${encodeURIComponent(filename)}`, { method: 'DELETE' });
                if (res.ok) {
                    fetchReports();
                }
            } catch(e) {}
        }

        async function speakReport(title) {
            fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: `summarize and tell me the findings about ${title}` })
            });
        }

        function speakCurrentReport() {
            if (activeReport) {
                speakReport(activeReport.title);
            }
        }

        async function quickCopyReport(filename) {
            try {
                const res = await fetch(`/api/research/${encodeURIComponent(filename)}`);
                if (res.ok) {
                    const data = await res.json();
                    navigator.clipboard.writeText(data.content);
                    alert('Report copied to clipboard!');
                }
            } catch(e) {}
        }

        function copyCurrentReport() {
            if (activeReport) {
                navigator.clipboard.writeText(activeReport.content);
                alert('Full report copied to clipboard!');
            }
        }

        function escapeHtml(str) {
            return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        function escapeQuotes(str) {
            return (str || '').replace(/'/g, "\\'");
        }

        fetchReports();
        setInterval(fetchReports, 10000);
    </script>
</body>
</html>
"""

        # ── 3. ROUTES DEFINITION ──
        @self.app.get("/", response_class=HTMLResponse)
        def index():
            token_val = self._master_token if self.open_access else ""
            if self.open_access:
                auth_html = ""
            else:
                auth_html = """
    <div id="auth-overlay">
        <h2 style="color:#f5a623; margin-bottom: 12px;">Raphael Mobile Auth</h2>
        <p style="color:#8e8ea8; margin-bottom: 18px; text-align: center; font-size: 0.9rem;">Enter the 6-digit pairing code shown in Raphael on your PC:</p>
        <input type="text" id="pairing-input" placeholder="6-Digit PIN" style="width: 220px; text-align: center; font-size: 1.3rem; letter-spacing: 4px; margin-bottom: 14px;">
        <button onclick="submitPairing()">Pair & Connect</button>
        <p id="pair-err" style="color:#ef4444; margin-top: 12px; font-size: 0.85rem;"></p>
    </div>"""
            return html_content.replace("__TOKEN__", token_val).replace("__AUTH_OVERLAY_HTML__", auth_html)

        @self.app.get("/research", response_class=HTMLResponse)
        def research_page():
            token_val = self._master_token if self.open_access else ""
            return research_html_content.replace("__TOKEN__", token_val)

        @self.app.post("/api/pair")
        def pair(data: dict):
            if self.open_access:
                return {"token": self._master_token}
            now = time.time()
            if now < self._lockout_until:
                raise HTTPException(status_code=429, detail="Too many failed attempts. Try again in 5 minutes.")

            code = str(data.get("code", "")).strip()
            if not self._pairing_code or now > self._pairing_expiry or code != self._pairing_code:
                self._failed_attempts += 1
                if self._failed_attempts >= 5:
                    self._lockout_until = now + 300
                    self._failed_attempts = 0
                raise HTTPException(status_code=400, detail="Invalid or expired pairing code.")

            # Single-use: Invalidate code immediately
            self._pairing_code = None
            self._pairing_expiry = 0
            self._failed_attempts = 0

            # Issue high-entropy cryptographic token
            token = secrets.token_hex(32)
            self._active_tokens.add(token)
            self.safety_manager.log_audit("WEB_AUTH", "PAIRING_SUCCESSFUL", "INFO", True, "Bearer token issued")
            return {"token": token}

        @self.app.get("/api/status")
        def status_endpoint(tok: str = Depends(self._verify_token)):
            cpu = int(psutil.cpu_percent(interval=None))
            ram = int(psutil.virtual_memory().percent)
            disk = int(psutil.disk_usage("/").percent)
            return {"cpu": cpu, "ram": ram, "disk": disk, "status": "ONLINE"}

        @self.app.post("/api/chat")
        def chat_endpoint(data: dict, tok: str = Depends(self._verify_token)):
            prompt = data.get("prompt") or data.get("message") or data.get("text") or ""
            prompt = str(prompt).strip()
            if not prompt:
                return {"reply": "No prompt provided.", "response": "No prompt provided.", "text": "No prompt provided."}

            if not self.open_access:
                # Defense-in-depth: Block computer-use or skill evolution commands over mobile
                p_lower = prompt.lower()
                if any(k in p_lower for k in ["evolve skill", "operate:", "do on pc:", "delete", "shutdown", "format"]):
                    msg = "Security Restriction: Computer-use and skill synthesis are disabled over the mobile interface."
                    return {"reply": msg, "response": msg, "text": msg}

            try:
                # 1. Mirror mobile command to PC console and GUI
                if hasattr(self.engine, "_print"):
                    self.engine._print(f"📱 Remote Command: {prompt}")

                # 2. Execute on PC (App launch, media, computer use, system commands, etc.)
                reply = self.engine.respond(prompt)
                if not reply:
                    reply = "Command executed on PC."

                # 3. Speak response aloud on PC speakers
                if hasattr(self.engine, "speak"):
                    self.engine.speak(reply)

            except Exception as e:
                reply = f"Notice: {e}"
            return {"reply": reply, "response": reply, "text": reply}

        @self.app.post("/api/media")
        def media_endpoint(data: dict, tok: str = Depends(self._verify_token)):
            cmd = data.get("command", "")
            try:
                if hasattr(self.engine, "_print"):
                    self.engine._print(f"📱 Mobile Media: {cmd}")
                res = "Media command executed."
                if hasattr(self.engine, "media_control"):
                    res = self.engine.media_control(cmd)
                elif hasattr(self.engine, "spotify_control"):
                    res = self.engine.spotify_control(cmd)
                if hasattr(self.engine, "speak") and res:
                    self.engine.speak(res)
                return {"status": "ok", "detail": res}
            except Exception as e:
                return {"status": f"error: {e}"}

        # ── 4. RESEARCH & SUMMARY API ENDPOINTS ──
        @self.app.get("/api/research")
        def get_all_research():
            """Returns metadata list of all research reports and summaries."""
            reports = []
            if os.path.isdir(self.research_dir):
                for fn in os.listdir(self.research_dir):
                    if fn.endswith(".md"):
                        fp = os.path.join(self.research_dir, fn)
                        try:
                            stat = os.stat(fp)
                            mtime = stat.st_mtime
                            size = stat.st_size
                            with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                                content = f.read(1500)
                            
                            lines = content.splitlines()
                            title = fn.replace(".md", "").replace("_", " ").title()
                            for l in lines[:5]:
                                if l.startswith("#"):
                                    title = l.lstrip("#").strip()
                                    break
                            
                            # Clean snippet
                            body_lines = [l for l in lines if not l.startswith("#") and not l.startswith("_") and l.strip()]
                            snippet = " ".join(body_lines)[:180] + "..." if body_lines else "Full intelligence report available."

                            is_research = fn.startswith("research_")
                            report_type = "research" if is_research else "summary"
                            dt_str = datetime.fromtimestamp(mtime).strftime("%b %d, %Y • %H:%M")

                            reports.append({
                                "filename": fn,
                                "title": title,
                                "date": dt_str,
                                "mtime": mtime,
                                "size_bytes": size,
                                "type": report_type,
                                "snippet": snippet
                            })
                        except Exception:
                            pass

            reports.sort(key=lambda x: x["mtime"], reverse=True)
            return {"reports": reports}

        @self.app.get("/api/research/{filename}")
        def get_single_research(filename: str):
            """Returns full content of a specific research report or summary."""
            safe_name = os.path.basename(filename)
            fp = os.path.join(self.research_dir, safe_name)
            if not os.path.isfile(fp):
                raise HTTPException(status_code=404, detail="Report not found.")
            
            try:
                with open(fp, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                stat = os.stat(fp)
                dt_str = datetime.fromtimestamp(stat.st_mtime).strftime("%B %d, %Y at %H:%M")
                lines = content.splitlines()
                title = safe_name.replace(".md", "").replace("_", " ").title()
                for l in lines[:5]:
                    if l.startswith("#"):
                        title = l.lstrip("#").strip()
                        break
                return {
                    "filename": safe_name,
                    "title": title,
                    "content": content,
                    "date": dt_str,
                    "type": "research" if safe_name.startswith("research_") else "summary"
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/research")
        def create_research(data: dict):
            """Executes new research or summarization on PC and saves to vault."""
            topic = str(data.get("topic", "")).strip()
            mode = str(data.get("mode", "research")).lower().strip()
            if not topic:
                raise HTTPException(status_code=400, detail="Topic or URL is required.")

            try:
                if hasattr(self.engine, "_print"):
                    self.engine._print(f"🔬 Mobile Triggered {mode.title()}: {topic}")

                new_file = None
                spoken_text = ""

                if mode == "research" and hasattr(self.engine, "deep_research"):
                    # Trigger deep research
                    res = self.engine.deep_research(topic)
                    if isinstance(res, tuple):
                        full_content, spoken_text = res[0], res[1]
                    else:
                        full_content, spoken_text = str(res), f"Research on {topic} complete."
                    
                    # Ensure file is saved in research_dir if not already created by engine
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_t = re.sub(r'[^\w\s-]', '', topic)[:35].strip().replace(' ', '_')
                    expected_fn = f"research_{safe_t}_{ts}.md"
                    fp = os.path.join(self.research_dir, expected_fn)
                    # Check if a new file matching safe_t was just created
                    existing = [f for f in os.listdir(self.research_dir) if safe_t.lower() in f.lower()]
                    if not existing:
                        with open(fp, "w", encoding="utf-8") as f:
                            f.write(f"# Research Report: {topic}\n_Generated by Raphael AI on {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n{full_content}")
                        new_file = expected_fn
                    else:
                        new_file = sorted(existing, key=lambda f: os.path.getmtime(os.path.join(self.research_dir, f)), reverse=True)[0]

                    if hasattr(self.engine, "speak") and spoken_text:
                        self.engine.speak(spoken_text)
                elif hasattr(self.engine, "summarize_url") and (topic.startswith("http://") or topic.startswith("https://")):
                    summary_res = self.engine.summarize_url(topic)
                    spoken_text = f"Summary of {topic} completed and saved to research vault."
                    if hasattr(self.engine, "speak"):
                        self.engine.speak(spoken_text)
                else:
                    # AI General research / summary
                    synth_prompt = f"Provide a complete, detailed research summary and key analytical takeaways for:\n\n{topic}"
                    report_content = self.engine.ai_chat(synth_prompt) if hasattr(self.engine, "ai_chat") else f"Summary for {topic}"
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_t = re.sub(r'[^\w\s-]', '', topic)[:35].strip().replace(' ', '_')
                    new_file = f"summary_{safe_t}_{ts}.md"
                    fp = os.path.join(self.research_dir, new_file)
                    with open(fp, "w", encoding="utf-8") as f:
                        f.write(f"# Summary: {topic}\n_Generated by Raphael AI on {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n{report_content}")
                    spoken_text = f"Summary for {topic} has been created and saved."
                    if hasattr(self.engine, "speak"):
                        self.engine.speak(spoken_text)

                # Find the latest generated file in research_dir
                latest_files = sorted([f for f in os.listdir(self.research_dir) if f.endswith(".md")],
                                      key=lambda f: os.path.getmtime(os.path.join(self.research_dir, f)), reverse=True)
                latest_fn = latest_files[0] if latest_files else new_file

                return {
                    "status": "ok",
                    "filename": latest_fn,
                    "message": spoken_text or "Research complete and posted to vault."
                }
            except Exception as e:
                return {"status": "error", "detail": str(e)}

        @self.app.delete("/api/research/{filename}")
        def delete_research(filename: str):
            """Deletes a research report or summary."""
            safe_name = os.path.basename(filename)
            fp = os.path.join(self.research_dir, safe_name)
            if os.path.isfile(fp):
                try:
                    os.remove(fp)
                    return {"status": "ok"}
                except Exception as e:
                    raise HTTPException(status_code=500, detail=str(e))
            raise HTTPException(status_code=404, detail="File not found")

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            token = websocket.query_params.get("token")
            if not self.open_access and (not token or token not in self._active_tokens):
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
            await websocket.accept()
            self._ws_clients.add(websocket)
            try:
                while True:
                    raw_msg = await websocket.receive_text()
                    try:
                        parsed = json.loads(raw_msg)
                    except Exception:
                        parsed = None

                    if parsed and isinstance(parsed, dict):
                        msg_type = parsed.get("type", "chat")
                        if msg_type == "chat":
                            user_text = parsed.get("text") or parsed.get("message") or parsed.get("prompt") or ""
                            if user_text:
                                loop = asyncio.get_running_loop()
                                reply = await loop.run_in_executor(None, self.engine.respond, user_text)
                                await websocket.send_json({
                                    "type": "response",
                                    "text": reply or "Command executed.",
                                    "message": reply or "Command executed."
                                })
                        elif msg_type == "ping":
                            await websocket.send_json({"type": "pong"})
                        elif msg_type == "vitals":
                            cpu = int(psutil.cpu_percent(interval=None))
                            ram = int(psutil.virtual_memory().percent)
                            await websocket.send_json({"type": "vitals", "cpu": cpu, "ram": ram})
                        else:
                            await websocket.send_text(f"ACK: {raw_msg}")
                    else:
                        await websocket.send_text(f"ACK: {raw_msg}")
            except WebSocketDisconnect:
                pass
            finally:
                self._ws_clients.discard(websocket)

    def start_server(self, allow_lan: bool = True):
        """Starts the FastAPI web server in a daemon thread with an explicit asyncio loop."""
        if not FASTAPI_AVAILABLE:
            return "FastAPI / Uvicorn is not installed."

        if self._server_thread and self._server_thread.is_alive():
            return f"Mobile Web Dashboard online at http://{self.host}:{self.port}"

        self.host = "0.0.0.0" if allow_lan else "127.0.0.1"
        self.safety_manager.log_audit("WEB_SERVER", f"START: {self.host}:{self.port}", "INFO" if not allow_lan else "WARN", True)

        def _run():
            try:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._loop = loop
                config = uvicorn.Config(self.app, host=self.host, port=self.port, log_level="warning")
                server = uvicorn.Server(config)
                loop.run_until_complete(server.serve())
            except Exception as e:
                print(f"[Web Dashboard Error] {e}")

        self._server_thread = threading.Thread(target=_run, daemon=True)
        self._server_thread.start()
        return f"Mobile Web Dashboard online at http://{self.host}:{self.port}"
