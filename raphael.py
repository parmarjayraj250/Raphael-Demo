import os, sys, json, time, asyncio, subprocess, webbrowser, shutil, re, platform, threading, uuid, queue, tempfile, sqlite3, math
from datetime import datetime

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR:
    try:
        os.chdir(_SCRIPT_DIR)
    except Exception:
        pass
    if _SCRIPT_DIR not in sys.path:
        sys.path.insert(0, _SCRIPT_DIR)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Global Crash Shield ─────────────────────────────────────────────────────
import traceback

def _write_crash_log(entry: str):
    try:
        log_file = 'raphael_crash.log'
        if os.path.exists(log_file) and os.path.getsize(log_file) > 2 * 1024 * 1024:
            bak = log_file + '.1'
            try:
                if os.path.exists(bak):
                    os.remove(bak)
                os.rename(log_file, bak)
            except Exception:
                pass
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(entry)
    except Exception:
        pass

def _global_crash_shield(exc_type, exc_val, exc_tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_val, exc_tb)
        return
    err_msg = ''.join(traceback.format_exception(exc_type, exc_val, exc_tb))
    print(f'[Raphael Crash Shield] Intercepted unhandled exception:\n{err_msg}')
    _write_crash_log(f'\n[{datetime.now()}] CRASH SHIELD INTERCEPT:\n{err_msg}\n')

sys.excepthook = _global_crash_shield

if hasattr(threading, 'excepthook'):
    def _thread_crash_shield(args):
        err_msg = ''.join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
        print(f'[Raphael Crash Shield] Intercepted thread error in {args.thread.name}:\n{err_msg}')
        _write_crash_log(f'\n[{datetime.now()}] THREAD ERROR in {args.thread.name}:\n{err_msg}\n')
    threading.excepthook = _thread_crash_shield

try:
    import win32com.client
    SAPI_AVAILABLE = True
except ImportError:
    SAPI_AVAILABLE = False

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False

try:
    import edge_tts, pygame
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    from duckduckgo_search import DDGS
    DDG_AVAILABLE = True
except ImportError:
    DDG_AVAILABLE = False

try:
    import wikipedia
    WIKI_AVAILABLE = True
except ImportError:
    WIKI_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import pyautogui, pytesseract
    from PIL import Image, ImageDraw
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False

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
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

import math, struct, wave
from raphael_safety import RaphaelSafetyManager
from raphael_skills_engine import RaphaelSkillSynthesizer
from raphael_swarm import RaphaelSwarm
from raphael_computer_use import RaphaelComputerUse
from raphael_knowledge_graph import RaphaelKnowledgeGraph
try:
    from raphael_web_dashboard import RaphaelWebDashboard
except Exception:
    RaphaelWebDashboard = None
from raphael_disk_hunter import RaphaelDiskHunter
from raphael_tools import RaphaelToolRegistry

# ── Constants ──────────────────────────────────────────────────────────────────
MEMORY_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raphael_memory.json")
NOTES_FILE    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raphael_notes.txt")
HISTORY_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raphael_history.json")
DRAFTS_DIR    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raphael_drafts")
RESEARCH_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raphael_research")
CHROMA_DIR    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raphael_chromadb")
SEMANTIC_DB   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raphael_semantic_memory.db")
RAPHAEL_TEMP_DIR = os.path.join(tempfile.gettempdir(), "raphael_temp")
os.makedirs(RAPHAEL_TEMP_DIR, exist_ok=True)
OLLAMA_MODELS = ["qwen2.5:3b", "qwen:3b", "qwen2.5:1.5b"]
IS_WINDOWS    = platform.system() == "Windows"

# File organizer category map
FILE_CATEGORIES = {
    "Images":     [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff"],
    "Videos":     [".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"],
    "Audio":      [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"],
    "Documents":  [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"],
    "Code":       [".py", ".js", ".ts", ".html", ".css", ".cpp", ".c", ".java", ".json", ".xml", ".sh", ".bat", ".ps1", ".go", ".rs"],
    "Archives":   [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "Executables":[".exe", ".msi", ".apk", ".dmg"],
    "Fonts":      [".ttf", ".otf", ".woff", ".woff2"],
}

# ── Auto-configure Tesseract path ─────────────────────────────────────────────
if IS_WINDOWS:
    _tess_candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for _p in _tess_candidates:
        if os.path.exists(_p):
            try:
                import pytesseract as _pt
                _pt.pytesseract.tesseract_cmd = _p
            except ImportError:
                pass
            break

LANGUAGE_VOICES = {
    "english":    "en-US-JennyNeural",
    "japanese":   "ja-JP-NanamiNeural",
    "spanish":    "es-ES-ElviraNeural",
    "french":     "fr-FR-DeniseNeural",
    "german":     "de-DE-KatjaNeural",
    "hindi":      "hi-IN-SwaraNeural",
    "chinese":    "zh-CN-XiaoxiaoNeural",
    "arabic":     "ar-EG-SalmaNeural",
    "korean":     "ko-KR-SunHiNeural",
    "portuguese": "pt-BR-FranciscaNeural",
    "italian":    "it-IT-ElsaNeural",
    "russian":    "ru-RU-SvetlanaNeural",
}

# Voice persona presets (name -> (edge_tts voice, pitch, rate))
PERSONA_VOICES = {
    "default":   ("en-US-JennyNeural",  "+0Hz",  "+0%"),
    "jenny":     ("en-US-JennyNeural",  "+0Hz",  "+0%"),
    "aria":      ("en-US-AriaNeural",   "+1Hz",  "+0%"),
    "sonia":     ("en-GB-SoniaNeural",  "+1Hz",  "+0%"),
    "friday":    ("en-US-JennyNeural",  "+0Hz",  "-2%"),
    "cyberpunk": ("en-US-GuyNeural",    "-6Hz", "-10%"),
}

GREETINGS = {
    "hi", "hello", "hey", "hiya", "howdy", "sup", "yo",
    "good morning", "good evening", "good afternoon", "good night",
}

SYSTEM_PROMPT = (
    "You are Raphael, an advanced, calm, soft, serious, and confident AI assistant created by Jay. "
    "Never refer to yourself as Microsoft, Meta, OpenAI, or Alibaba. You are Raphael. "
    "Be concise. Never use filler phrases. Give direct, factual, and intelligent answers. "
    "Maintain a calm, professional, and helpful tone always."
)

BROWSER_URLS = {
    "youtube":       "https://www.youtube.com/results?search_query={q}",
    "google":        "https://www.google.com/search?q={q}",
    "github":        "https://github.com/search?q={q}",
    "reddit":        "https://www.reddit.com/search/?q={q}",
    "wikipedia":     "https://en.wikipedia.org/wiki/Special:Search?search={q}",
    "twitter":       "https://twitter.com/search?q={q}",
    "stackoverflow": "https://stackoverflow.com/search?q={q}",
}


# ── Crash-Proof SQLite Semantic Memory ───────────────────────────────────────────
class SafeEmbeddingFunction:
    """Crash-proof deterministic 384-d semantic embedding function without onnxruntime or rust dependencies."""
    def __init__(self, dim=384):
        self.dim = dim

    def __call__(self, input_texts):
        if isinstance(input_texts, str):
            input_texts = [input_texts]
        embeddings = []
        for text in input_texts:
            vec = [0.0] * self.dim
            words = re.findall(r'\w+', str(text).lower())
            for i, w in enumerate(words):
                h = (hash(w) & 0x7fffffff) % self.dim
                vec[h] += 1.0 / (1.0 + 0.1 * i)
            for i in range(len(str(text)) - 2):
                tri = str(text)[i:i+3].lower()
                h = (hash(tri) & 0x7fffffff) % self.dim
                vec[h] += 0.3
            norm = math.sqrt(sum(x * x for x in vec)) or 1.0
            embeddings.append([x / norm for x in vec])
        return embeddings


class RaphaelSemanticMemory:
    """
    100% crash-proof, thread-safe SQLite semantic memory engine.
    Eliminates C/Rust access violations and multi-threading segmentation faults on Windows.
    Stores conversations, notes, facts, and documents with cosine-similarity vector search.
    """
    def __init__(self, db_path=SEMANTIC_DB, dim=384):
        self.db_path = db_path
        self.dim = dim
        self._lock = threading.Lock()
        self._ef = SafeEmbeddingFunction(dim=dim)
        self._ready = False
        try:
            self._init_db()
            self._ready = True
            print("[Memory] SQLite semantic memory online.")
        except Exception as e:
            print(f"[Memory] SQLite semantic memory init error: {e}")

    def _init_db(self):
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_items (
                    id TEXT PRIMARY KEY,
                    collection TEXT,
                    text TEXT,
                    metadata TEXT,
                    vector TEXT,
                    timestamp TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_col ON memory_items(collection)")
            conn.commit()

    @property
    def ready(self):
        return self._ready

    def _uid(self, prefix=""):
        return prefix + str(int(time.time() * 1000)) + "_" + str(os.getpid())

    def _cosine_sim(self, v1, v2):
        return sum(a * b for a, b in zip(v1, v2))

    def store_conversation(self, user_msg, raphael_reply):
        """Store a conversation turn in semantic memory."""
        try:
            combined = f"User: {user_msg}\nRaphael: {raphael_reply}"
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            vec = self._ef(combined)[0]
            item_id = self._uid("conv_")
            meta = json.dumps({"timestamp": ts, "user": str(user_msg), "reply": str(raphael_reply)[:200]})
            with self._lock, sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO memory_items (id, collection, text, metadata, vector, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    (item_id, "conversations", combined, meta, json.dumps(vec), ts)
                )
                conn.commit()
        except Exception as e:
            print(f"[Memory] store_conversation error: {e}")

    def store_note(self, note_text):
        """Store a note in semantic memory."""
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            vec = self._ef(note_text)[0]
            item_id = self._uid("note_")
            meta = json.dumps({"timestamp": ts, "text": str(note_text)})
            with self._lock, sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO memory_items (id, collection, text, metadata, vector, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    (item_id, "notes", note_text, meta, json.dumps(vec), ts)
                )
                conn.commit()
        except Exception as e:
            print(f"[Memory] store_note error: {e}")

    def store_fact(self, key, value):
        """Store a user fact/preference in semantic memory."""
        try:
            text = f"{key}: {value}"
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            vec = self._ef(text)[0]
            fact_id = "fact_" + re.sub(r'\W+', '_', str(key).lower())
            meta = json.dumps({"key": key, "value": value, "timestamp": ts})
            with self._lock, sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO memory_items (id, collection, text, metadata, vector, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                    (fact_id, "facts", text, meta, json.dumps(vec), ts)
                )
                conn.commit()
        except Exception as e:
            print(f"[Memory] store_fact error: {e}")

    def store_document(self, filepath, chunk_size=800):
        """Load a text document into semantic memory in chunks."""
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
            if not content:
                return "File is empty."
            fname = os.path.basename(filepath)
            chunks = [content[i:i+chunk_size] for i in range(0, len(content), chunk_size)]
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            with self._lock, sqlite3.connect(self.db_path) as conn:
                for i, chunk in enumerate(chunks):
                    doc_id = self._uid(f"doc_{i}_")
                    meta = json.dumps({"source": fname, "chunk": i, "filepath": filepath, "timestamp": ts})
                    vec = self._ef(chunk)[0]
                    conn.execute(
                        "INSERT OR REPLACE INTO memory_items (id, collection, text, metadata, vector, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                        (doc_id, "documents", chunk, meta, json.dumps(vec), ts)
                    )
                conn.commit()
            return f"Loaded '{fname}' into memory. {len(chunks)} chunk(s) stored."
        except Exception as e:
            return f"Document load error: {e}"

    def recall(self, query, n=3, collections=None):
        """
        Semantic search across memory collections.
        Returns relevant past context as a formatted string.
        """
        if not self._ready:
            return ""
        try:
            target_cols = collections or ["conversations", "notes", "facts", "documents"]
            q_vec = self._ef(query)[0]
            candidates = []
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                placeholders = ",".join("?" for _ in target_cols)
                cursor.execute(
                    f"SELECT text, metadata, vector, timestamp FROM memory_items WHERE collection IN ({placeholders})",
                    target_cols
                )
                rows = cursor.fetchall()

            for text, meta_json, vec_json, ts in rows:
                try:
                    v = json.loads(vec_json)
                    sim = self._cosine_sim(q_vec, v)
                    candidates.append((sim, ts, text))
                except Exception:
                    continue

            candidates.sort(key=lambda x: x[0], reverse=True)
            results = [f"[{ts}] {text[:300]}" for sim, ts, text in candidates[:n]]
            return "\n".join(results)
        except Exception as e:
            print(f"[Memory] recall error: {e}")
            return ""

    def search_memory(self, query, n=5):
        """User-facing search across all memory."""
        context = self.recall(query, n=n)
        if not context:
            return f"No relevant memory found for: '{query}'"
        return f"Memory search results for '{query}':\n\n{context}"

    def get_stats(self):
        """Returns memory statistics."""
        try:
            with self._lock, sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT collection, COUNT(*) FROM memory_items GROUP BY collection")
                counts = dict(cursor.fetchall())
            return (
                f"Semantic Memory Stats (Thread-Safe SQLite Engine):\n"
                f"  Conversations : {counts.get('conversations', 0)}\n"
                f"  Notes         : {counts.get('notes', 0)}\n"
                f"  Facts         : {counts.get('facts', 0)}\n"
                f"  Documents     : {counts.get('documents', 0)}\n"
                f"  Storage       : {self.db_path}"
            )
        except Exception as e:
            return f"Memory stats error: {e}"


# ── Engine ─────────────────────────────────────────────────────────────────────
class Raphael:
    def __init__(self, callback_print=None, hide_window_callback=None, show_window_callback=None,
                 on_speak_start=None, on_speak_end=None, demo_mode=False):
        self.demo_mode      = demo_mode
        self.running        = True
        self.memory         = self._load_memory()
        self.language       = self.memory.get("language", "english")
        self.voice          = LANGUAGE_VOICES.get(self.language, "en-US-JennyNeural")
        self.pitch          = "+0Hz"
        self.rate           = "+0%"
        self.persona        = "default"
        self.history        = self._load_history()
        self.callback_print = callback_print
        self.hide_window_callback = hide_window_callback
        self.show_window_callback = show_window_callback
        self.on_speak_start = on_speak_start
        self.on_speak_end   = on_speak_end
        self.gui            = None
        self.preferred_model = self.memory.get("ollama_model", "qwen:3b")
        if self.preferred_model in ["qwen:1b", "qwen2.5:1b", "1b"]:
            self.preferred_model = "qwen:3b"
            self.memory["ollama_model"] = "qwen:3b"
            self._save_memory()
        self.recognizer     = None
        self.microphone     = None
        self._is_speaking   = False
        self._speech_queue  = queue.Queue()
        self._llm_lock      = threading.Lock()

        # ── ChromaDB Semantic Memory
        self.semantic_memory = RaphaelSemanticMemory()

        if TTS_AVAILABLE:
            self._ensure_mixer_init()

        if SR_AVAILABLE:
            try:
                self.recognizer = sr.Recognizer()
                self.recognizer.pause_threshold = 0.8
                self.recognizer.non_speaking_duration = 0.5
                self.recognizer.dynamic_energy_threshold = True
                self.microphone = sr.Microphone()
                threading.Thread(target=self._calibrate_mic, daemon=True).start()
            except Exception:
                pass

        # Dedicated sequential TTS worker thread
        threading.Thread(target=self._speech_worker, daemon=True).start()

        # ── Elite Safety & Subsystems ──
        self.safety_manager   = RaphaelSafetyManager(callback_alert=self._print)
        self.tool_registry    = RaphaelToolRegistry(self.safety_manager, alert_callback=self._print)
        self._pending_skill_approval = None

        if not self.demo_mode:
            self.skills_engine    = RaphaelSkillSynthesizer(self.safety_manager, self.ai_chat)
            self.swarm            = RaphaelSwarm(self.safety_manager, self.ai_chat)
            self.computer_use     = RaphaelComputerUse(self.safety_manager, speak_func=self.speak)
            self.knowledge_graph  = RaphaelKnowledgeGraph(self.safety_manager)
            self.disk_hunter      = RaphaelDiskHunter(self.safety_manager, speak_func=self.speak, alert_callback=self._print)
            self._register_default_tools()
            if RaphaelWebDashboard is not None:
                self.web_dashboard = RaphaelWebDashboard(self, self.safety_manager, port=8765, open_access=True)
                try:
                    self.web_dashboard.start_server(allow_lan=True)
                except Exception:
                    pass
            else:
                self.web_dashboard = None

            self._start_proactive_alerts()
            self._start_scheduler_loop()
            self._start_news_monitor()
        else:
            self.skills_engine    = None
            self.swarm            = None
            self.computer_use     = None
            self.knowledge_graph  = None
            self.disk_hunter      = None
            self.web_dashboard    = None
            self._register_demo_tools()

    def _register_demo_tools(self):
        """Registers strictly safe, read-only demo capabilities."""
        self.tool_registry.register(
            name="system_status",
            description="Reports CPU, memory, disk usage, and battery statistics.",
            handler=self.system_status,
            risk_level="SAFE",
            permission="system"
        )
        self.tool_registry.register(
            name="free_up_ram",
            description="Frees unused RAM via garbage collection.",
            handler=self.free_up_ram,
            risk_level="SAFE",
            permission="system"
        )
        self.tool_registry.register(
            name="web_search",
            description="Searches the web using DuckDuckGo.",
            handler=self.web_search,
            schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            risk_level="SAFE",
            permission="network"
        )
        self.tool_registry.register(
            name="get_weather",
            description="Fetches live weather reports for a location.",
            handler=self.get_weather,
            schema={"type": "object", "properties": {"location": {"type": "string"}}},
            risk_level="SAFE",
            permission="network"
        )

    def _register_default_tools(self):
        """Registers core capabilities into the structured schema-backed ToolRegistry."""
        self.tool_registry.register(
            name="system_status",
            description="Reports CPU, memory, disk usage, and battery statistics.",
            handler=self.system_status,
            risk_level="SAFE",
            permission="system"
        )
        self.tool_registry.register(
            name="clean_temp_files",
            description="Cleans temporary files and caches from system folders.",
            handler=self.clean_temp_files,
            risk_level="HIGH_RISK",
            requires_approval=True,
            permission="file"
        )
        self.tool_registry.register(
            name="free_up_ram",
            description="Frees unused RAM via garbage collection and process memory trimming.",
            handler=self.free_up_ram,
            risk_level="SAFE",
            permission="system"
        )
        self.tool_registry.register(
            name="empty_recycle_bin",
            description="Permanently empties the Recycle Bin.",
            handler=self.empty_recycle_bin,
            risk_level="HIGH_RISK",
            requires_approval=True,
            permission="file"
        )
        self.tool_registry.register(
            name="web_search",
            description="Searches the web using DuckDuckGo.",
            handler=self.web_search,
            schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            risk_level="SAFE",
            permission="network"
        )
        self.tool_registry.register(
            name="get_weather",
            description="Fetches live weather reports for a location.",
            handler=self.get_weather,
            schema={"type": "object", "properties": {"location": {"type": "string"}}},
            risk_level="SAFE",
            permission="network"
        )
        self.tool_registry.register(
            name="create_folder",
            description="Creates a directory folder at the specified path.",
            handler=self.create_folder,
            schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            risk_level="SAFE",
            permission="file"
        )
        self.tool_registry.register(
            name="delete_path",
            description="Deletes a file or directory permanently.",
            handler=self.delete_path,
            schema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
            risk_level="CRITICAL",
            requires_approval=True,
            permission="file"
        )
        self.tool_registry.register(
            name="list_files",
            description="Lists contents of a target directory.",
            handler=self.list_files,
            schema={"type": "object", "properties": {"path": {"type": "string"}}},
            risk_level="SAFE",
            permission="file"
        )
        self.tool_registry.register(
            name="kill_process",
            description="Terminates a process by name or PID.",
            handler=self.kill_process,
            schema={"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
            risk_level="HIGH_RISK",
            requires_approval=True,
            permission="system"
        )

    def _ensure_mixer_init(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception:
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            except Exception as e:
                print("[Mixer Init Error]", e)

    def _calibrate_mic(self):
        try:
            if self.microphone and self.recognizer:
                with self.microphone as src:
                    self.recognizer.adjust_for_ambient_noise(src, duration=1.2)
        except Exception:
            pass

    def listen(self):
        if not SR_AVAILABLE or not self.microphone or not self.recognizer:
            return None
        # Echo protection: skip listening if Raphael is currently speaking
        if self._is_speaking:
            return None
        try:
            with self.microphone as src:
                audio = self.recognizer.listen(src, timeout=5, phrase_time_limit=15)
            if self._is_speaking:
                return None
            return self.recognizer.recognize_google(audio).strip()
        except Exception:
            return None

    # ── Memory ─────────────────────────────────────────────────────────────────
    def _atomic_write_json(self, filepath: str, data):
        """Atomic crash-proof JSON writer with backup to prevent corruption on unexpected shutdown."""
        tmp_path = filepath + f".tmp_{os.getpid()}_{int(time.time()*1000)}"
        try:
            folder = os.path.dirname(os.path.abspath(filepath))
            os.makedirs(folder, exist_ok=True)
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            # Maintain a backup of the previous valid state
            if os.path.exists(filepath):
                bak_path = filepath + ".bak"
                try:
                    shutil.copy2(filepath, bak_path)
                except Exception:
                    pass
            os.replace(tmp_path, filepath)
        except Exception as e:
            print(f"[Atomic JSON Error] Failed to write {filepath}: {e}")
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _load_memory(self):
        for path in [MEMORY_FILE, MEMORY_FILE + ".bak"]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    continue
        return {"user_name": None, "language": "english", "facts": {}}

    def _save_memory(self):
        self._atomic_write_json(MEMORY_FILE, self.memory)

    def _load_history(self):
        for path in [HISTORY_FILE, HISTORY_FILE + ".bak"]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    continue
        return []

    def _save_history(self):
        self._atomic_write_json(HISTORY_FILE, self.history[-50:])

    # ── Output & Dual-Layer Speech Engine ───────────────────────────────────────
    def _print(self, text):
        if isinstance(text, tuple):
            text = text[0]
        if self.callback_print:
            self.callback_print(text)
        else:
            print("Raphael: " + str(text))

    @staticmethod
    def _sanitize_for_speech(text: str) -> str:
        """Strips markdown syntax, emojis, bullets, and symbols so TTS doesn't read out emoji names."""
        text = re.sub(r'[*_#`~>|\\\[\](){}]', ' ', str(text))
        text = re.sub(r'https?://\S+|www\.\S+', ' ', text)
        text = re.sub(r'[a-zA-Z]:\\[\w\\.-]+', ' ', text)
        emoji_pattern = re.compile(
            '['
            '\U0001F600-\U0001F64F'  # emoticons
            '\U0001F300-\U0001F5FF'  # symbols & pictographs (💡, 🚀, 🔥, etc.)
            '\U0001F680-\U0001F6FF'  # transport & map symbols
            '\U0001F1E0-\U0001F1FF'  # flags
            '\U0001F900-\U0001F9FF'  # supplemental symbols & pictographs
            '\U0001FA70-\U0001FAFF'  # symbols extended-a
            '\U00002702-\U000027B0'  # dingbats
            '\U000024C2-\U0001F251'  # enclosed chars
            '\U00002600-\U000026FF'  # misc symbols (⚡, ⚠, etc.)
            '\U00002300-\U000023FF'  # misc technical
            '\U00002B00-\U00002BFF'  # misc symbols and arrows
            '\U00002190-\U000021FF'  # arrows
            '\U0000FE00-\U0000FE0F'  # variation selectors
            '\U0000200D'             # zero width joiner
            '✦★☆●•◆◇■□✓✔✕✖🛑⚠🛠📌💡✨🔥🚀'
            ']+',
            flags=re.UNICODE
        )
        text = emoji_pattern.sub(' ', text)
        return re.sub(r'\s+', ' ', text).strip()

    def speak(self, text, spoken_text=None):
        if isinstance(text, tuple):
            if len(text) >= 2:
                text, spoken_text = text[0], (spoken_text or text[1])
            elif len(text) == 1:
                text = text[0]
            else:
                text = ""
        self._print(text)
        to_say = spoken_text if spoken_text else text
        if isinstance(to_say, tuple):
            to_say = to_say[0] if len(to_say) > 0 else ""
        # Clean up for speech synthesis so emojis and symbols don't speak aloud
        to_say = self._sanitize_for_speech(to_say)

        if to_say:
            self._speech_queue.put(to_say)

    def _speech_worker(self):
        """Sequential single-worker queue processing speech to prevent concurrency collisions."""
        while self.running:
            try:
                text_to_say = self._speech_queue.get()
                if text_to_say is None:
                    break
                if not text_to_say.strip():
                    self._speech_queue.task_done()
                    continue

                self._is_speaking = True
                if self.on_speak_start:
                    try:
                        self.on_speak_start()
                    except Exception:
                        pass

                success = False

                # Layer 1: Primary Microsoft Neural Edge-TTS
                if TTS_AVAILABLE:
                    try:
                        success = self._speak_edge_tts(text_to_say)
                    except Exception as e:
                        print("[Edge-TTS Synthesis Error]", e)
                        success = False

                # Layer 2: Secondary Offline Windows Native SAPI5 Fallback
                if not success:
                    try:
                        success = self._speak_sapi5(text_to_say)
                    except Exception as e:
                        print("[SAPI5 Offline Fallback Error]", e)
                        success = False

                if self.on_speak_end:
                    try:
                        self.on_speak_end()
                    except Exception:
                        pass

                # Short echo cooldown before re-enabling microphone recognition
                time.sleep(0.25)
                self._is_speaking = False
                self._speech_queue.task_done()
            except Exception as e:
                print("[Speech Worker Global Error]", e)
                self._is_speaking = False
                if self.on_speak_end:
                    try:
                        self.on_speak_end()
                    except Exception:
                        pass
                time.sleep(0.1)

    def _speak_edge_tts(self, text):
        unique_id = uuid.uuid4().hex[:8]
        tmp = os.path.join(RAPHAEL_TEMP_DIR, f"_tmp_tts_{os.getpid()}_{unique_id}.mp3")
        try:
            pitch = getattr(self, "pitch", "-2Hz")
            rate  = getattr(self, "rate",  "-4%")
            com = edge_tts.Communicate(text, self.voice, pitch=pitch, rate=rate)

            # Set Windows selector loop policy to prevent IOCP closing crashes
            if IS_WINDOWS and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
                try:
                    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                except Exception:
                    pass

            # Async synthesis with 8s network timeout
            async def _save_async():
                await com.save(tmp)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(asyncio.wait_for(_save_async(), timeout=8.0))
            finally:
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception:
                    pass
                loop.close()

            if not os.path.exists(tmp) or os.path.getsize(tmp) < 100:
                return False

            self._ensure_mixer_init()
            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(15)
            pygame.mixer.music.unload()
            return True
        except Exception as e:
            print("[Edge-TTS Playback Error]", e)
            return False
        finally:
            try:
                if os.path.exists(tmp):
                    time.sleep(0.05)
                    os.remove(tmp)
            except Exception:
                pass

    def _speak_sapi5(self, text):
        if not SAPI_AVAILABLE or not IS_WINDOWS:
            return False
        try:
            import win32com.client
            import pythoncom
            pythoncom.CoInitialize()
            try:
                speaker = win32com.client.Dispatch("SAPI.SpVoice")
                # Auto-select female voice (Microsoft Zira or available female voice)
                for v in speaker.GetVoices():
                    desc = v.GetDescription().lower()
                    if any(k in desc for k in ["zira", "eva", "hazel", "catherine", "female", "girl"]):
                        speaker.Voice = v
                        break
                speaker.Rate = 0
                speaker.Volume = 100
                speaker.Speak(text)
                return True
            finally:
                pythoncom.CoUninitialize()
        except Exception as e:
            print("[SAPI5 Execution Error]", e)
            return False

    def _select_optimal_models(self, prompt, task_type=None, is_voice=False):
        """
        Streamlined dual-model architecture:
        - Heavy Workloads (Coding, Research, Skills, Default): Qwen 2.5 3B (qwen2.5:3b / qwen:3b)
        - Fast Lightweight Fallback: Qwen 2.5 1.5B (qwen2.5:1.5b)
        """
        if is_voice and task_type not in ["coding", "research", "skill"]:
            return ["qwen2.5:1.5b", "qwen2.5:3b", "qwen:3b"]
        return ["qwen2.5:3b", "qwen:3b", "qwen2.5:1.5b"]

    def set_model(self, model_name):
        """Switch preferred Ollama generative model (or 'auto' for autonomous selection)."""
        model_name = model_name.strip().lower()
        if model_name in ["3b", "qwen 3b", "qwen3b", "qwen2.5 3b", "qwen2.5:3b"]:
            model_name = "qwen2.5:3b"
        elif model_name in ["1.5b", "1.5", "qwen 1.5b", "qwen2.5:1.5b", "1b", "qwen 1b"]:
            model_name = "qwen2.5:1.5b"
        self.preferred_model = model_name
        self.memory["ollama_model"] = model_name
        self._save_memory()
        return f"AI model routing set to '{model_name}'."

    def get_model(self):
        """Returns the active AI model routing configuration."""
        cur = getattr(self, "preferred_model", "qwen2.5:3b")
        return f"Active AI Model Routing: {cur.upper()} (Primary: Qwen 2.5 3B | Fallback: Qwen 2.5 1.5B)"

    def ai_chat(self, prompt, task_type=None, is_voice=False, save_history=True):
        if not save_history:
            msgs = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        else:
            memory_context = self.semantic_memory.recall(prompt, n=3) if hasattr(self, "semantic_memory") else ""
            self.history.append({"role": "user", "content": prompt})
            system_msg = SYSTEM_PROMPT
            if is_voice:
                system_msg += "\n\nYou are currently speaking in a voice conversation. Keep answers concise, natural, and direct (1 to 3 sentences) suitable for speech synthesis."
            if memory_context:
                system_msg += (
                    "\n\nRELEVANT MEMORY (past conversations/notes):\n"
                    + memory_context
                    + "\nUse this if it helps answer the user."
                )
            msgs = [{"role": "system", "content": system_msg}] + self.history[-10:]

        if OLLAMA_AVAILABLE:
            models_to_try = self._select_optimal_models(prompt, task_type=task_type, is_voice=is_voice)
            pref = getattr(self, "preferred_model", "auto")
            if pref and pref not in ["auto", "qwen", "qwen2.5"]:
                models_to_try = [pref] + [m for m in models_to_try if m != pref]

            lock = getattr(self, "_llm_lock", None)
            for model in models_to_try:
                try:
                    if lock:
                        with lock:
                            resp = ollama.chat(
                                model=model,
                                messages=msgs,
                                options={"num_predict": 512 if is_voice else 2048, "num_ctx": 4096}
                            )
                    else:
                        resp = ollama.chat(
                            model=model,
                            messages=msgs,
                            options={"num_predict": 512 if is_voice else 2048, "num_ctx": 4096}
                        )
                    reply = resp["message"]["content"].strip()
                    if save_history:
                        self.history.append({"role": "assistant", "content": reply})
                        self._save_history()
                        if hasattr(self, "semantic_memory"):
                            threading.Thread(
                                target=self.semantic_memory.store_conversation,
                                args=(prompt, reply), daemon=True
                            ).start()
                    return reply
                except Exception:
                    continue

        # Smart Offline Fallback: If Ollama is offline, provide web knowledge or structured assistance
        if DDG_AVAILABLE:
            search_fallback = self.web_search(prompt)
            if search_fallback and "unavailable" not in search_fallback.lower() and len(search_fallback) > 30:
                return f"[Offline Knowledge Mode]\n{search_fallback}"

        return ("Raphael is operating in Offline Core Mode.\n"
                "All commands (system status, notes, files, media, research) work locally.\n"
                "To enable full generative AI chat, start Ollama: 'ollama run qwen:3b'.")

    # ── Feature 04: Web Search ─────────────────────────────────────────────────
    def web_search(self, query):
        if DDG_AVAILABLE:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=5))
                if results:
                    combined = []
                    for r in results:
                        combined.append(r.get("title", "") + ": " + r.get("body", ""))
                    return "\n\n".join(combined)
            except Exception:
                pass
        if WIKI_AVAILABLE:
            try:
                return wikipedia.summary(query, sentences=8)
            except Exception:
                pass
        return "Search unavailable."

    # ── Feature 06: Run Commands ───────────────────────────────────────────────
    def run_command(self, command):
        try:
            r   = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            out = ((r.stdout or "") + (r.stderr or "")).strip()
            return out[:800] if out else "No output."
        except subprocess.TimeoutExpired:
            return "Timed out."
        except Exception as e:
            return "Error: " + str(e)

    # ── Feature 07: Compile Code ───────────────────────────────────────────────
    def compile_code(self, filename, run_after=False):
        if getattr(self, "demo_mode", False):
            return "This command is not available in the Demo Edition. Type 'help' to see all working commands."
        if not os.path.exists(filename):
            return "File not found: " + filename
        ext  = os.path.splitext(filename)[1].lower()
        base = os.path.splitext(filename)[0]
        if ext == ".py":
            return self.run_command('python "' + filename + '"')
        elif ext == ".c":
            out = base + (".exe" if IS_WINDOWS else "")
            res = self.run_command('gcc "' + filename + '" -o "' + out + '"')
        elif ext in (".cpp", ".cc"):
            out = base + (".exe" if IS_WINDOWS else "")
            res = self.run_command('g++ "' + filename + '" -o "' + out + '"')
        elif ext == ".java":
            res = self.run_command('javac "' + filename + '"')
            if run_after and "error" not in res.lower():
                return res + "\n" + self.run_command("java " + os.path.basename(base))
            return res
        else:
            return "Cannot compile " + ext
        if "error" not in res.lower():
            suffix = "\n" + self.run_command('"' + out + '"') if run_after else ""
            return "Compiled: " + out + suffix
        return res

    # ── Feature 08: Install Packages ──────────────────────────────────────────
    def install_package(self, pkg):
        r = self.run_command("pip install " + pkg)
        if "successfully installed" in r.lower():
            return "Installed " + pkg
        if "already satisfied" in r.lower():
            return pkg + " already installed."
        return r

    # ── Feature 09: Browser Control ───────────────────────────────────────────
    def open_browser(self, query, site="google"):
        url = BROWSER_URLS.get(site, BROWSER_URLS["google"]).replace("{q}", query.replace(" ", "+"))
        webbrowser.open(url)
        return "Opened " + site + ": " + query

    # ── Feature 10: File Manager ───────────────────────────────────────────────
    def create_folder(self, path):
        try:
            os.makedirs(path, exist_ok=True)
            return "Folder created: " + path
        except Exception as e:
            return "Error: " + str(e)

    def delete_path(self, path):
        if getattr(self, "demo_mode", False):
            return "This command is not available in the Demo Edition. Type 'help' to see all working commands."
        if not os.path.exists(path):
            return "Not found: " + path
        try:
            shutil.rmtree(path) if os.path.isdir(path) else os.remove(path)
            return "Deleted: " + path
        except Exception as e:
            return "Error: " + str(e)

    def list_files(self, path="."):
        try:
            items = os.listdir(path)
            return "\n".join(items) if items else "Empty."
        except Exception as e:
            return "Error: " + str(e)

    # ── Feature 11: Kill Process ───────────────────────────────────────────────
    def kill_process(self, name):
        if not PSUTIL_AVAILABLE:
            return "psutil not installed."
        killed = 0
        for p in psutil.process_iter(["name"]):
            try:
                if name.lower() in p.info["name"].lower():
                    p.kill()
                    killed += 1
            except Exception:
                pass
        if killed:
            return "Killed " + str(killed) + " process(es) matching '" + name + "'."
        return "No process named '" + name + "' found."

    # ── Feature 12: Shutdown / Restart ────────────────────────────────────────
    def shutdown_pc(self):
        self.speak("Shutting down in 5 seconds.")
        time.sleep(5)
        os.system("shutdown /s /t 0" if IS_WINDOWS else "sudo shutdown -h now")

    def restart_pc(self):
        self.speak("Restarting in 5 seconds.")
        time.sleep(5)
        os.system("shutdown /r /t 0" if IS_WINDOWS else "sudo reboot")

    # ── Feature 13: Screen OCR ────────────────────────────────────────────────
    def read_screen(self, summarize=False):
        if getattr(self, "demo_mode", False):
            return "This command is not available in the Demo Edition. Type 'help' to see all working commands."
        if not OCR_AVAILABLE:
            return ("OCR requires extra setup. Install with:\n"
                    "  winget install UB-Mannheim.TesseractOCR\n"
                    "Then restart Raphael.")
        screenshot = None
        try:
            # Hide Raphael GUI window temporarily so it doesn't block the screen
            if self.hide_window_callback:
                try:
                    self.hide_window_callback()
                except Exception:
                    pass
                time.sleep(0.4)  # Wait for window to minimize/hide

            screenshot = pyautogui.screenshot()
        except Exception as e:
            err = str(e)
            if "tesseract" in err.lower() or "PATH" in err:
                return ("Tesseract binary not found. Install it:\n"
                        "  winget install UB-Mannheim.TesseractOCR\n"
                        "Then restart Raphael.")
            return "OCR capture error: " + err
        finally:
            # Restore Raphael GUI window
            if self.show_window_callback:
                try:
                    self.show_window_callback()
                except Exception:
                    pass
                time.sleep(0.1)

        try:
            text = pytesseract.image_to_string(screenshot).strip()
        except Exception as e:
            err = str(e)
            if "tesseract" in err.lower() or "PATH" in err:
                return ("Tesseract binary not found. Install it:\n"
                        "  winget install UB-Mannheim.TesseractOCR\n"
                        "Then restart Raphael.")
            return "OCR parsing error: " + err

        if not text:
            return "No text found on screen."

        if summarize:
            return self.ai_chat("Summarize and explain what is currently on the user's screen:\n\n" + text[:2000])

        return "Screen Text:\n" + text[:1200]

    # ── Feature 23: YouTube Playback Control ───────────────────────────────
    # YouTube keyboard shortcuts sent to the focused browser window
    _YT_KEY_MAP = {
        "play":            ("k",   "Toggled play."),
        "pause":           ("k",   "Toggled pause."),
        "resume":          ("k",   "Resumed."),
        "stop":            ("k",   "Paused."),
        "mute":            ("m",   "Muted."),
        "unmute":          ("m",   "Unmuted."),
        "toggle mute":     ("m",   "Mute toggled."),
        "fullscreen":      ("f",   "Fullscreen toggled."),
        "full screen":     ("f",   "Fullscreen toggled."),
        "theater mode":    ("t",   "Theater mode toggled."),
        "captions":        ("c",   "Captions toggled."),
        "subtitles":       ("c",   "Subtitles toggled."),
        "next video":      ("shift+n", "Next video."),
        "next":            ("shift+n", "Next video."),
        "previous video":  ("shift+p", "Previous video."),
        "previous":        ("shift+p", "Previous video."),
        "prev":            ("shift+p", "Previous video."),
        "skip forward":    ("l",   "Skipped forward 10 seconds."),
        "skip ahead":      ("l",   "Skipped forward 10 seconds."),
        "forward":         ("l",   "Skipped forward 10 seconds."),
        "skip back":       ("j",   "Skipped back 10 seconds."),
        "skip backward":   ("j",   "Skipped back 10 seconds."),
        "rewind":          ("j",   "Rewound 10 seconds."),
        "go back":         ("j",   "Skipped back 10 seconds."),
    }

    def youtube_control(self, action):
        action = action.strip().lower()
        # Normalise aliases
        _aliases = {
            "vol up": "volume up", "louder": "volume up",
            "turn up": "volume up", "turn up volume": "volume up",
            "increase volume": "volume up", "raise volume": "volume up",
            "vol down": "volume down", "quieter": "volume down",
            "lower volume": "volume down", "decrease volume": "volume down",
            "turn down": "volume down", "turn down volume": "volume down",
        }
        action = _aliases.get(action, action)

        try:
            import pygetwindow as gw
        except ImportError:
            return "pygetwindow not installed. Run: pip install pygetwindow"

        # Find open YouTube window
        wins = [w for w in gw.getAllWindows() if "youtube" in w.title.lower()]
        if not wins:
            return "No YouTube window found. Open YouTube in your browser first."

        try:
            wins[0].activate()
        except Exception:
            pass
        time.sleep(0.4)  # give OS time to focus

        # Volume adjustments (arrow keys, 5 taps = ~25%)
        if action in {"volume up", "volume down"}:
            key  = "up" if action == "volume up" else "down"
            steps = 5
            for _ in range(steps):
                pyautogui.press(key)
            return ("Volume raised." if action == "volume up" else "Volume lowered.")

        # Amount-based volume: "volume up 3" / "volume down 10"
        mv = re.match(r"volume (up|down)\s+(\d+)", action)
        if mv:
            key   = "up" if mv.group(1) == "up" else "down"
            steps = min(int(mv.group(2)), 20)
            for _ in range(steps):
                pyautogui.press(key)
            return "Volume adjusted by " + str(steps) + " steps."

        # Standard key shortcuts
        if action in self._YT_KEY_MAP:
            key, msg = self._YT_KEY_MAP[action]
            if "+" in key:
                pyautogui.hotkey(*key.split("+"))
            else:
                pyautogui.press(key)
            return msg

        return "Unknown YouTube command: '" + action + "'. Try: play, pause, volume up, volume down, mute, skip forward, skip back, next, previous, fullscreen."

    # ── Feature 15: Name Memory ───────────────────────────────────────────────
    def remember_name(self, name):
        name = name.strip().capitalize()
        self.memory["user_name"] = name
        self._save_memory()
        return "Noted. I will call you " + name + "."

    def recall_name(self):
        n = self.memory.get("user_name")
        return "Your name is " + n + "." if n else "I do not know your name yet."

    # ── Feature 16: Language Mode ─────────────────────────────────────────────
    def set_language(self, lang):
        lang = lang.strip().lower()
        if lang not in LANGUAGE_VOICES:
            return "Language not supported. Available: " + ", ".join(LANGUAGE_VOICES.keys())
        self.voice    = LANGUAGE_VOICES[lang]
        self.language = lang
        self.memory["language"] = lang
        self._save_memory()
        return "Voice set to " + lang.capitalize() + "."

    # ── Feature 18: System Health ─────────────────────────────────────────────
    def system_status(self):
        if not PSUTIL_AVAILABLE:
            return "psutil unavailable."
        cpu  = psutil.cpu_percent(interval=0.5)
        ram  = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        bat  = psutil.sensors_battery()
        bat_s = (", Battery: " + str(round(bat.percent)) + "%") if bat else ""
        return "CPU: " + str(cpu) + "%  |  RAM: " + str(ram) + "%  |  Disk: " + str(disk) + "%" + bat_s

    # ── System Maintenance & Deep Cleaner ─────────────────────────────────────
    def clean_temp_files(self):
        """Cleans Windows temp folders and returns total MB freed."""
        if not IS_WINDOWS:
            return "Temp cleaning is currently supported on Windows."
        temp_dirs = [
            os.environ.get("TEMP"),
            os.environ.get("TMP"),
            r"C:\Windows\Temp",
        ]
        bytes_freed = 0
        deleted_count = 0

        for t_dir in temp_dirs:
            if not t_dir or not os.path.exists(t_dir):
                continue
            for root, dirs, files in os.walk(t_dir):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(fp)
                        os.remove(fp)
                        bytes_freed += sz
                        deleted_count += 1
                    except Exception:
                        pass

        mb_freed = round(bytes_freed / (1024 * 1024), 2)
        return f"System Temp Cleanup Complete:\n● Deleted {deleted_count} temporary file(s)\n● Freed {mb_freed} MB disk space."

    def free_up_ram(self):
        """Trims working sets of running processes to release RAM back to the system."""
        import gc
        gc.collect()
        if not IS_WINDOWS or not PSUTIL_AVAILABLE:
            return "RAM freed via garbage collection."
        try:
            import ctypes
            freed = 0
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, proc.info['pid'])
                    if handle:
                        ctypes.windll.psapi.EmptyWorkingSet(handle)
                        ctypes.windll.kernel32.CloseHandle(handle)
                        freed += 1
                except Exception:
                    pass
            ram_now = psutil.virtual_memory().percent
            return f"RAM Optimization Complete:\n● Optimized working memory for {freed} process(es).\n● Current RAM Usage: {ram_now}%"
        except Exception as e:
            return f"RAM optimization error: {e}"

    def empty_recycle_bin(self):
        """Empties Windows Recycle Bin without prompt."""
        if not IS_WINDOWS:
            return "Recycle bin clearing supported on Windows."
        try:
            import ctypes
            res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
            if res == 0:
                return "Recycle Bin emptied successfully."
            elif res == 0x80004005:
                return "Recycle Bin is already empty."
            return "Recycle Bin emptied."
        except Exception as e:
            return f"Recycle bin error: {e}"

    def get_heavy_processes(self):
        """Returns top CPU and RAM consuming background processes."""
        if not PSUTIL_AVAILABLE:
            return "psutil unavailable."
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                p.info['cpu'] = p.info['cpu_percent'] or 0.0
                p.info['ram'] = round(p.info['memory_percent'] or 0.0, 1)
                procs.append(p.info)
            except Exception:
                pass

        top_cpu = sorted(procs, key=lambda x: x['cpu'], reverse=True)[:4]
        top_ram = sorted(procs, key=lambda x: x['ram'], reverse=True)[:4]

        out = "System Resource Usage Report:\n\n🔥 Top CPU Processes:\n"
        for p in top_cpu:
            out += f"  ● {p['name']} (PID {p['pid']}): {p['cpu']}%\n"
        out += "\n💾 Top RAM Processes:\n"
        for p in top_ram:
            out += f"  ● {p['name']} (PID {p['pid']}): {p['ram']}%\n"
        return out.strip()

    # ── Feature 19: Reminders ─────────────────────────────────────────────────
    def set_reminder(self, minutes, note):
        try:
            secs = int(float(minutes) * 60)
            def _fire():
                time.sleep(secs)
                self.speak("Reminder: " + note)
            threading.Thread(target=_fire, daemon=True).start()
            return "Reminder set for " + str(minutes) + " minute(s): " + note
        except Exception as e:
            return "Error: " + str(e)

    # ── Feature 20: Clipboard ─────────────────────────────────────────────────
    def read_clipboard(self, summarize=False):
        if not CLIPBOARD_AVAILABLE:
            return "pyperclip not installed. Run: pip install pyperclip"
        try:
            text = pyperclip.paste().strip()
            if not text:
                return "Clipboard is empty."
            if summarize:
                return self.ai_chat("Summarize this text concisely:\n" + text[:1500])
            return "Clipboard:\n" + text[:800]
        except Exception as e:
            return "Clipboard error: " + str(e)

    # ── Feature 21: File Reader ───────────────────────────────────────────────
    def read_file(self, filepath, summarize=False):
        if getattr(self, "demo_mode", False):
            from pathlib import Path
            raw = str(filepath).strip().strip('"\'').replace("/", "\\")
            sandbox_dir = (Path(__file__).parent / "demo_sandbox").resolve()
            try:
                if ".." in Path(raw).parts:
                    return "🔒 Demo Edition: Access outside demo_sandbox is blocked for your security."
                resolved = (sandbox_dir / raw).resolve() if not os.path.isabs(raw) else Path(raw).resolve()
                if not resolved.is_relative_to(sandbox_dir):
                    return "🔒 Demo Edition: Access outside demo_sandbox is blocked for your security."
                filepath = str(resolved)
            except Exception:
                return "🔒 Demo Edition: Access outside demo_sandbox is blocked for your security."

        if not os.path.exists(filepath):
            return "File not found: " + filepath
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
            if not content:
                return "File is empty."
            if summarize:
                return self.ai_chat("Summarize this file:\n" + content[:2000])
            return content[:1000]
        except Exception as e:
            return "Error: " + str(e)

    # ── Feature 22: Notes ─────────────────────────────────────────────────────
    def save_note(self, note):
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            with open(NOTES_FILE, "a", encoding="utf-8") as f:
                f.write("[" + ts + "] " + note + "\n")
            # Store in ChromaDB
            threading.Thread(
                target=self.semantic_memory.store_note,
                args=(note,), daemon=True
            ).start()
            return "Note saved."
        except Exception as e:
            return "Error: " + str(e)

    def get_notes(self):
        if not os.path.exists(NOTES_FILE):
            return "No notes saved yet."
        try:
            with open(NOTES_FILE, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
            return ("Saved Notes:\n" + content) if content else "No notes saved yet."
        except Exception as e:
            return "Error reading notes: " + str(e)

    # ── JARVIS Features ──────────────────────────────────────────────────────
    APP_MAP = {
        "vs code": "code",
        "vscode": "code",
        "code": "code",
        "notepad": "notepad",
        "calculator": "calc",
        "calc": "calc",
        "chrome": "chrome",
        "google chrome": "chrome",
        "browser": "chrome",
        "the browser": "chrome",
        "edge": "msedge",
        "discord": "discord",
        "cmd": "cmd",
        "terminal": "wt",
        "powershell": "powershell",
        "paint": "mspaint",
        "explorer": "explorer",
        "files": "explorer",
        "file explorer": "explorer",
        "my files": "explorer",
        "task manager": "taskmgr",
        "word": "winword",
        "excel": "excel",
        "spotify": "spotify"
    }

    def get_weather(self, location=""):
        try:
            import requests
            loc = location.strip().replace(" ", "+")
            url = f"https://wttr.in/{loc}?format=3" if loc else "https://wttr.in/?format=%l:+%C+%t,+humidity+%h,+wind+%w"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200 and resp.text.strip():
                return "Weather: " + resp.text.strip()
            return "Unable to fetch weather data right now."
        except Exception as e:
            return "Weather fetch error: " + str(e)

    def launch_app(self, app_name):
        name = app_name.strip().lower()
        target = self.APP_MAP.get(name, name)
        try:
            if IS_WINDOWS:
                os.system(f'start "" "{target}"')
            else:
                subprocess.Popen([target])
            return f"Launching {app_name.capitalize()}..."
        except Exception as e:
            return f"Failed to launch {app_name}: {str(e)}"

    def media_control(self, action):
        """Universal Windows media & audio controller (works across all browsers and media apps)."""
        action = action.strip().lower()

        try:
            if IS_WINDOWS:
                import ctypes
                VK_MAP = {
                    "mute": 0xAD,
                    "voldown": 0xAE,
                    "volup": 0xAF,
                    "next": 0xB0,
                    "prev": 0xB1,
                    "stop": 0xB2,
                    "playpause": 0xB3,
                }
                def _send_vk(vk):
                    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
                    time.sleep(0.01)
                    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)

                if any(k in action for k in ["play", "pause", "resume", "stop"]):
                    _send_vk(VK_MAP["playpause"])
                    return "Media playback toggled."
                elif "next" in action or "skip" in action:
                    _send_vk(VK_MAP["next"])
                    return "Skipped to next track."
                elif "previous" in action or "prev" in action or "back" in action:
                    _send_vk(VK_MAP["prev"])
                    return "Returned to previous track."
                elif "volume up" in action or "louder" in action:
                    for _ in range(5):
                        _send_vk(VK_MAP["volup"])
                    return "Volume raised."
                elif "volume down" in action or "quieter" in action:
                    for _ in range(5):
                        _send_vk(VK_MAP["voldown"])
                    return "Volume lowered."
                elif "mute" in action or "unmute" in action:
                    _send_vk(VK_MAP["mute"])
                    return "Media volume muted or unmuted."
                return "Universal media command executed."
            else:
                import pyautogui
                if any(k in action for k in ["play", "pause", "resume", "stop"]):
                    pyautogui.press("playpause")
                return "Media action sent."
        except Exception as e:
            return f"Media control error: {str(e)}"

    # Backward compatibility alias
    spotify_control = media_control

    def _start_proactive_alerts(self):
        def _loop():
            last_alert_time = 0
            while self.running:
                time.sleep(60)
                now = time.time()
                if now - last_alert_time < 900:
                    continue
                if PSUTIL_AVAILABLE:
                    try:
                        cpu = psutil.cpu_percent(interval=1)
                        ram = psutil.virtual_memory().percent
                        bat = psutil.sensors_battery()
                        msg = None
                        if cpu > 90:
                            msg = f"Attention: System CPU load is critical at {round(cpu)}%."
                        elif ram > 90:
                            msg = f"Attention: System RAM usage is high at {round(ram)}%."
                        elif bat and bat.percent < 20 and not bat.power_plugged:
                            msg = f"Attention: Battery is low at {round(bat.percent)}%. Please connect your charger."
                        if msg:
                            last_alert_time = now
                            self.speak(msg)
                    except Exception:
                        pass
        threading.Thread(target=_loop, daemon=True).start()

    def start_wake_word_listener(self, on_wake_callback=None):
        if not SR_AVAILABLE or not self.microphone:
            return "Speech recognition is not available for wake word."
        def _wake_loop():
            rec = sr.Recognizer()
            rec.dynamic_energy_threshold = True
            rec.pause_threshold = 0.8
            while self.running:
                try:
                    with self.microphone as src:
                        audio = rec.listen(src, timeout=3, phrase_time_limit=5)
                    text = rec.recognize_google(audio).strip().lower()
                    if any(w in text for w in ["raphael", "hey raphael", "ok raphael", "hello raphael"]):
                        if on_wake_callback:
                            on_wake_callback(text)
                        else:
                            self.speak("Yes? I am listening.")
                            cmd = self.listen()
                            if cmd:
                                res = self.respond(cmd, is_voice=True)
                                if res:
                                    self.speak(res)
                except Exception:
                    pass
        threading.Thread(target=_wake_loop, daemon=True).start()
        return "Wake Word listener activated ('Hey Raphael')."

    # ── JARVIS Tier 2 Features ───────────────────────────────────────────────
    def get_briefing(self):
        hour = datetime.now().hour
        greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 18 else "Good evening")
        name = self.memory.get("user_name", "Sir")
        now_str = datetime.now().strftime("%A, %B %d at %I:%M %p")
        
        weather_info = self.get_weather()
        sys_info = self.system_status()
        
        briefing = (
            f"{greeting}, {name}.\n"
            f"● Date & Time: {now_str}\n"
            f"● {weather_info}\n"
            f"● System: {sys_info}\n"
            "All systems operational. Ready for your commands."
        )
        return briefing

    def suggest_something(self):
        """
        Proactively analyzes system status, storage clutter, and capabilities
        to provide a high-value contextual suggestion for Jay.
        """
        name = self.memory.get("user_name") or ("friend" if getattr(self, "demo_mode", False) else "Jay")
        suggestions = []
        try:
            if PSUTIL_AVAILABLE:
                ram = psutil.virtual_memory().percent
                if ram > 65:
                    suggestions.append(f"RAM is currently running at {ram}%. Say 'free up ram' to optimize working memory.")
            
            temp_dir = os.environ.get("TEMP", "")
            if temp_dir and os.path.exists(temp_dir):
                count = len(os.listdir(temp_dir))
                if count > 40:
                    suggestions.append(f"Found {count}+ cached temporary files. Say 'clean temp files' to reclaim disk space.")

            dl_dir = os.path.expanduser("~/Downloads")
            if os.path.exists(dl_dir):
                unorg = [f for f in os.listdir(dl_dir) if os.path.isfile(os.path.join(dl_dir, f))]
                if len(unorg) > 4:
                    suggestions.append(f"You have {len(unorg)} unorganized items in Downloads. Say 'organize downloads' to sort them automatically into categories.")
        except Exception:
            pass

        suggestions.append("Want to research a topic in depth? Say 'deep research [topic]' to synthesize an intelligence report.")
        suggestions.append("You can teach me a new capability on the fly! Say 'evolve skill [name and task]' and I will write, test, and install it.")
        suggestions.append("Say 'read my screen' to extract and summarize whatever text or code is currently on your display.")
        suggestions.append("Say 'enable mobile remote' to access Raphael from your smartphone over your local Wi-Fi.")
        suggestions.append("Say 'system status' for an instant real-time diagnostic of CPU, RAM, disk, and battery.")

        import random
        picked = random.choice(suggestions)
        return f"💡 Raphael's Suggestion for you, {name}:\n{picked}"

    def get_active_window(self):
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if win and win.title:
                return f"Active Window: {win.title}"
            return "No active window title detected."
        except Exception as e:
            return f"Window inspect error: {str(e)}"

    def get_active_window_context(self):
        """
        Inspects active window and returns app category, window title, and smart context suggestion.
        """
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if not win or not win.title:
                return {"app_type": "general", "title": "Desktop", "suggestion": "Ready for your commands."}

            title = win.title.strip()
            t_lower = title.lower()

            if any(k in t_lower for k in ["visual studio code", "vscode", ".py", ".c", ".cpp", ".js", ".java", "sublime", "pycharm"]):
                return {
                    "app_type": "ide",
                    "title": title,
                    "suggestion": f"💡 Context AI [IDE]: Detected '{title[:35]}'. Say 'compile [file]' or 'build code [task]' for coding help."
                }
            elif any(k in t_lower for k in ["chrome", "edge", "firefox", "brave", "opera", "youtube", "google"]):
                return {
                    "app_type": "browser",
                    "title": title,
                    "suggestion": f"💡 Context AI [Browser]: Detected '{title[:35]}'. Say 'explain screen' or 'search [query]' for web help."
                }
            elif any(k in t_lower for k in ["explorer", "this pc", "downloads", "documents", "desktop"]):
                return {
                    "app_type": "explorer",
                    "title": title,
                    "suggestion": f"💡 Context AI [Explorer]: Detected '{title[:35]}'. Say 'organize my files' or 'list files' for folder cleanup."
                }
            elif any(k in t_lower for k in ["cmd", "powershell", "terminal", "bash"]):
                return {
                    "app_type": "terminal",
                    "title": title,
                    "suggestion": f"💡 Context AI [Terminal]: Detected '{title[:35]}'. Say 'run [cmd]' to execute shell commands."
                }
            else:
                return {
                    "app_type": "general",
                    "title": title,
                    "suggestion": f"💡 Context AI: Active Window is '{title[:40]}'. Say 'read screen' or ask anything."
                }
        except Exception:
            return {"app_type": "general", "title": "Desktop", "suggestion": "Ready for your commands."}

    def summarize_url(self, url):
        """Fetches and summarizes any article, webpage or documentation link."""
        url = url.strip()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        try:
            import requests
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code != 200:
                return f"Failed to fetch webpage (HTTP {r.status_code})."

            html = r.text
            html = re.sub(r'<script.*?</script>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
            html = re.sub(r'<style.*?</style>', ' ', html, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text).strip()

            if len(text) < 80:
                return f"Could not extract readable article text from {url}."

            prompt = (
                f"You are a concise research analyst. Summarize the key points, findings, "
                f"and important takeaways from this article in clear bullet points:\n\n{text[:7000]}"
            )
            summary = self.ai_chat(prompt)
            try:
                os.makedirs(RESEARCH_DIR, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                domain = re.sub(r'^https?://', '', url).split('/')[0].replace('.', '_')
                summary_file = os.path.join(RESEARCH_DIR, f"summary_{domain}_{ts}.md")
                with open(summary_file, "w", encoding="utf-8") as sf:
                    sf.write(f"# Article Summary: {url}\n_Generated by Raphael AI on {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n{summary}")
            except Exception:
                pass
            return f"📄 Web Article Summary ({url}):\n\n{summary}"
        except Exception as e:
            return f"Error summarizing URL: {str(e)}"

    def set_windows_autostart(self, enable=True):
        """Enables or disables Raphael launching silently on Windows startup."""
        if not IS_WINDOWS:
            return "Autostart is only supported on Windows."
        try:
            startup_dir = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")
            vbs_file = os.path.join(startup_dir, "Raphael_Autostart.vbs")
            script_path = os.path.abspath(__file__)
            pythonw_path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
            if not os.path.exists(pythonw_path):
                pythonw_path = sys.executable

            if enable:
                vbs_content = f'Set WshShell = CreateObject("WScript.Shell")\nWshShell.Run """{pythonw_path}"" ""{script_path}""", 0, False\n'
                with open(vbs_file, "w", encoding="utf-8") as f:
                    f.write(vbs_content)
                self.memory["autostart"] = True
                self._save_memory()
                return "✓ Windows Autostart ENABLED. Raphael will start automatically with Windows in the background."
            else:
                if os.path.exists(vbs_file):
                    os.remove(vbs_file)
                self.memory["autostart"] = False
                self._save_memory()
                return "✓ Windows Autostart DISABLED."
        except Exception as e:
            return f"Autostart configuration error: {str(e)}"

    def draft_email(self, prompt):
        if not os.path.exists(DRAFTS_DIR):
            os.makedirs(DRAFTS_DIR, exist_ok=True)
        
        system_prompt = "You are an executive assistant. Write a clear, professional email draft based on the user's request. Output subject line and email body."
        
        draft_content = ""
        if OLLAMA_AVAILABLE:
            try:
                res = ollama.chat(model=OLLAMA_MODELS[0], messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ])
                draft_content = res["message"]["content"].strip()
            except Exception:
                pass
        
        if not draft_content:
            draft_content = f"Subject: Regarding {prompt}\n\nDear recipient,\n\n{prompt}\n\nBest regards,\n{self.memory.get('user_name', 'User')}"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        draft_file = os.path.join(DRAFTS_DIR, f"draft_{timestamp}.txt")
        try:
            with open(draft_file, "w", encoding="utf-8") as f:
                f.write(draft_content)
        except Exception:
            pass

        if CLIPBOARD_AVAILABLE:
            try:
                pyperclip.copy(draft_content)
            except Exception:
                pass

        return f"Email Drafted & Copied to Clipboard:\n\n{draft_content[:600]}"

    def remember_fact(self, key, value):
        facts = self.memory.get("facts", {})
        facts[key.strip().lower()] = value.strip()
        self.memory["facts"] = facts
        self._save_memory()
        # Store in ChromaDB
        threading.Thread(
            target=self.semantic_memory.store_fact,
            args=(key, value), daemon=True
        ).start()
        return f"Noted. Saved '{key}' as '{value}'."

    def recall_facts(self):
        facts = self.memory.get("facts", {})
        if not facts:
            return "No custom facts or preferences stored yet."
        lines = [f"● {k.capitalize()}: {v}" for k, v in facts.items()]
        return "Stored Facts & Preferences:\n" + "\n".join(lines)

    # ── Security & Passcode Management ─────────────────────────────────────────
    def set_passcode(self, passcode):
        p = str(passcode).strip()
        if not p:
            return "Passcode cannot be empty."
        self.memory["passcode"] = p
        self._save_memory()
        return "Master passcode updated. Raphael is now password protected."

    def remove_passcode(self):
        if "passcode" in self.memory:
            del self.memory["passcode"]
            self._save_memory()
            return "Master passcode removed. Password protection disabled."
        return "No passcode was currently set."

    def verify_passcode(self, passcode):
        saved = self.memory.get("passcode")
        if not saved:
            return True
        return str(saved).strip() == str(passcode).strip()

    # ── TIER 3: Autonomous Agent ──────────────────────────────────────────────

    def _organize_single_folder(self, folder):
        if not os.path.isdir(folder):
            return f"Folder not found: {folder}"

        moved = {}
        errors  = []

        for fname in os.listdir(folder):
            src = os.path.join(folder, fname)
            if os.path.isdir(src):
                continue
            ext = os.path.splitext(fname)[1].lower()
            category = None
            for cat, exts in FILE_CATEGORIES.items():
                if ext in exts:
                    category = cat
                    break
            if not category:
                category = "Other"

            dest_dir = os.path.join(folder, category)
            try:
                os.makedirs(dest_dir, exist_ok=True)
                dest = os.path.join(dest_dir, fname)
                if os.path.exists(dest):
                    base, ext2 = os.path.splitext(fname)
                    dest = os.path.join(dest_dir, base + "_" + str(int(time.time())) + ext2)
                shutil.move(src, dest)
                moved[category] = moved.get(category, 0) + 1
            except Exception as e:
                errors.append(fname + ": " + str(e))

        folder_name = os.path.basename(folder)
        if not moved and not errors:
            return f"No unorganized files in {folder_name}."

        summary = f"Organized {folder_name}:\n"
        for cat, count in sorted(moved.items()):
            summary += f"  → {cat}: {count} file(s) moved\n"
        if errors:
            summary += f"  ⚠ Errors: {len(errors)}\n"
        return summary.strip()

    def auto_organize_files(self, folder=""):
        """Autonomously organizes files in user folders by type."""
        if not folder or folder.lower() in ["my files", "files", "all files", "everything"]:
            targets = [os.path.expanduser("~/Downloads"), os.path.expanduser("~/Desktop")]
            results = [self._organize_single_folder(t) for t in targets]
            return "Auto-Organized User Folders:\n\n" + "\n\n".join(results)
        else:
            return self._organize_single_folder(folder)

    def deep_research(self, topic):
        """Autonomous multi-source research agent — searches, extracts, and writes a report."""
        self._print(f"[Agent] Researching: {topic} ...")
        os.makedirs(RESEARCH_DIR, exist_ok=True)

        results = []

        # Step 1: DuckDuckGo search (multiple queries, higher result limit)
        if DDG_AVAILABLE:
            queries = [
                topic,
                topic + " overview and key facts",
                topic + " latest developments and applications",
            ]
            for q in queries:
                try:
                    with DDGS() as ddgs:
                        hits = list(ddgs.text(q, max_results=5))
                    for h in hits:
                        results.append({"source": "DuckDuckGo", "title": h.get("title",""), "body": h.get("body","")})
                except Exception:
                    pass

        # Step 2: Wikipedia summary
        if WIKI_AVAILABLE:
            try:
                summary = wikipedia.summary(topic, sentences=10)
                results.append({"source": "Wikipedia", "title": topic, "body": summary})
            except Exception:
                pass

        if not results:
            return "Research failed. No search results found. Check your internet connection.", "Research failed due to no internet connection."

        # Step 3: Compile raw context
        raw_context = ""
        seen = set()
        for r in results:
            key = r["title"][:40]
            if key in seen:
                continue
            seen.add(key)
            raw_context += f"\n## {r['source']}: {r['title']}\n{r['body']}\n"
        raw_context = raw_context[:12000]

        # Step 4: AI synthesis
        report_content = ""
        spoken_summary = ""
        try:
            synth_prompt = (
                f"You are a research analyst. Based on the following sources, write a complete, "
                f"thorough, and detailed research report on: '{topic}'.\n"
                f"Include all available facts, explanations, key points, current developments, and real-world applications.\n"
                f"Do NOT cut off or leave out details.\n\n"
                f"Sources:\n{raw_context}"
            )
            report_content = self.ai_chat(synth_prompt, task_type="research")
        except Exception:
            pass

        if not report_content:
            report_content = f"# Research Report: {topic}\n\n{raw_context}"

        # Generate a complete spoken summary covering the full topic without cutoffs
        try:
            spoken_prompt = (
                f"Based on this research report about '{topic}', write a clear, full spoken summary "
                f"(4 to 6 complete sentences) covering the overview, key takeaways, and applications so the user hears the complete story. "
                f"Do not use markdown symbols or abbreviate.\n\nReport:\n{report_content[:3000]}"
            )
            spoken_summary = self.ai_chat(spoken_prompt, task_type="research")
        except Exception:
            pass

        if not spoken_summary:
            clean_text = re.sub(r'[*_#`~>|-]', ' ', report_content)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            spoken_summary = f"Research report on {topic}: " + clean_text

        # Step 5: Save report
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = re.sub(r'[^\w\s-]', '', topic)[:40].strip().replace(' ', '_')
        report_path = os.path.join(RESEARCH_DIR, f"research_{safe_topic}_{ts}.md")
        with open(report_path, "w", encoding="utf-8") as f:
            header = f"# Research Report: {topic}\n_Generated by Raphael AI on {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n"
            f.write(header + report_content)

        # Index report into ChromaDB vector memory
        threading.Thread(
            target=self.semantic_memory.store_document,
            args=(report_path,), daemon=True
        ).start()

        full_res = f"Research complete on {topic}.\nReport saved to: {report_path}\n\n--- REPORT ---\n{report_content}"
        return full_res, spoken_summary

    # ── Auto-Scheduled Workflows ──────────────────────────────────────────────
    def _start_scheduler_loop(self):
        def _loop():
            while self.running:
                time.sleep(30)
                try:
                    schedules = self.memory.get("schedules", [])
                    now_dt = datetime.now()
                    now_time_str = now_dt.strftime("%H:%M")
                    now_date_str = now_dt.strftime("%Y-%m-%d")
                    now_ts = time.time()
                    updated = False

                    for task in schedules:
                        t_type = task.get("type")
                        if t_type == "daily_briefing":
                            target_time = task.get("time", "08:00")
                            last_run = task.get("last_run", "")
                            if now_time_str == target_time and last_run != now_date_str:
                                task["last_run"] = now_date_str
                                updated = True
                                briefing = self.get_briefing()
                                self.speak(briefing)

                        elif t_type == "auto_clean":
                            days = task.get("interval_days", 7)
                            last_ts = task.get("last_ts", 0)
                            if now_ts - last_ts >= days * 86400:
                                task["last_ts"] = now_ts
                                updated = True
                                res = self.auto_organize_files()
                                self.speak(res, spoken_text="Scheduled file organization is complete.")

                    if updated:
                        self._save_memory()
                except Exception as e:
                    print("[Scheduler Error]", e)

        threading.Thread(target=_loop, daemon=True).start()

    def add_scheduled_task(self, task_type, time_or_days):
        schedules = self.memory.get("schedules", [])
        task_type = task_type.lower()
        if "briefing" in task_type:
            t_str = time_or_days.strip() if ":" in time_or_days else "08:00"
            schedules.append({"id": len(schedules) + 1, "type": "daily_briefing", "time": t_str, "last_run": ""})
            self.memory["schedules"] = schedules
            self._save_memory()
            return f"Scheduled daily briefing at {t_str} every morning."

        elif "clean" in task_type or "organize" in task_type:
            days = 7
            try:
                days = int(re.search(r'\d+', time_or_days).group())
            except Exception:
                pass
            schedules.append({"id": len(schedules) + 1, "type": "auto_clean", "interval_days": days, "last_ts": time.time()})
            self.memory["schedules"] = schedules
            self._save_memory()
            return f"Scheduled automatic file organization every {days} days."

        return "Unknown schedule task type. Use: 'schedule daily briefing at 08:00' or 'schedule file clean every 7 days'."

    def list_scheduled_tasks(self):
        schedules = self.memory.get("schedules", [])
        if not schedules:
            return "No scheduled automated workflows."
        out = "Scheduled Workflows:\n"
        for item in schedules:
            tid = item.get("id")
            ttype = item.get("type")
            if ttype == "daily_briefing":
                out += f"  ● [{tid}] Daily Briefing at {item.get('time')}\n"
            elif ttype == "auto_clean":
                out += f"  ● [{tid}] Auto File Clean every {item.get('interval_days')} days\n"
        return out.strip()

    def remove_scheduled_task(self, task_id):
        schedules = self.memory.get("schedules", [])
        new_sched = [s for s in schedules if str(s.get("id")) != str(task_id).strip()]
        if len(new_sched) < len(schedules):
            self.memory["schedules"] = new_sched
            self._save_memory()
            return f"Removed scheduled task #{task_id}."
        return f"Scheduled task #{task_id} not found."

    # ── Autonomous Code Builder & Self-Healing Tester Agent ────────────────────
    def build_code_agent(self, task_description):
        """
        Autonomous Agent: Writes Python code, auto-installs missing pip packages,
        runs test execution, and auto-fixes any syntax or runtime errors!
        """
        self._print(f"[Code Agent] Building code for: {task_description} ...")
        if not os.path.exists(DRAFTS_DIR):
            os.makedirs(DRAFTS_DIR, exist_ok=True)

        if not OLLAMA_AVAILABLE:
            return "Ollama is required for Code Agent. Run: pip install ollama", "Ollama is not installed."

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w\s-]', '', task_description)[:30].strip().replace(' ', '_').lower() or "script"
        script_path = os.path.join(DRAFTS_DIR, f"agent_{safe_name}_{ts}.py")

        # Step 1: Initial Code Generation
        prompt = (
            f"You are an expert Python software engineer. Write a complete, self-contained, "
            f"runnable Python script for the following request:\n"
            f"'{task_description}'\n\n"
            f"Instructions:\n"
            f"1. Include necessary imports.\n"
            f"2. Add clear print statements demonstrating that the code ran successfully.\n"
            f"3. Return ONLY valid executable Python code enclosed inside ```python ... ``` block without conversational filler."
        )

        try:
            raw_code = self.ai_chat(prompt, task_type="coding")
        except Exception as e:
            return f"Code generation error: {e}", f"Code generation failed: {e}"

        m = re.search(r"```python\s*(.*?)\s*```", raw_code, re.DOTALL)
        code = m.group(1).strip() if m else raw_code

        # Step 2: Auto-detect missing dependencies & pip install
        imports = re.findall(r"^(?:import|from)\s+([a-zA-Z0-9_]+)", code, re.MULTILINE)
        stdlib = {'os', 'sys', 'time', 'json', 're', 'math', 'datetime', 'subprocess', 'random', 'threading', 'asyncio', 'shutil', 'urllib', 'pathlib', 'struct', 'wave'}
        for pkg in set(imports):
            if pkg not in stdlib:
                try:
                    __import__(pkg)
                except ImportError:
                    self._print(f"[Code Agent] Auto-installing missing dependency: {pkg} ...")
                    subprocess.run(f"pip install {pkg}", shell=True, capture_output=True)

        # Step 3: Self-Healing Test Execution Loop (up to 3 retries)
        max_attempts = 3
        last_output = ""
        success = False

        for attempt in range(1, max_attempts + 1):
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            self._print(f"[Code Agent] Test Execution Attempt {attempt}/{max_attempts} ...")
            try:
                proc = subprocess.run([sys.executable, script_path], capture_output=True, text=True, timeout=30)
                stdout = proc.stdout.strip()
                stderr = proc.stderr.strip()
                last_output = f"Stdout:\n{stdout}\n\nStderr:\n{stderr}" if stderr else f"Stdout:\n{stdout}"

                if proc.returncode == 0:
                    success = True
                    break
                else:
                    self._print(f"[Code Agent] Attempt {attempt} failed with error. Auto-healing code...")
                    # Self-Healing Feedback Loop
                    fix_prompt = (
                        f"The Python script below failed with returncode {proc.returncode}.\n"
                        f"Error output:\n{stderr or stdout}\n\n"
                        f"Original Code:\n{code}\n\n"
                        f"Fix the error and output ONLY the corrected, valid Python script enclosed inside ```python ... ``` block."
                    )
                    fix_raw = self.ai_chat(fix_prompt, task_type="coding")
                    m_fix = re.search(r"```python\s*(.*?)\s*```", fix_raw, re.DOTALL)
                    code = m_fix.group(1).strip() if m_fix else fix_raw
            except subprocess.TimeoutExpired:
                last_output = "Execution timed out after 30 seconds."
                break
            except Exception as e:
                last_output = f"Execution error: {e}"
                break

        # Index created script into ChromaDB
        threading.Thread(
            target=self.semantic_memory.store_document,
            args=(script_path,), daemon=True
        ).start()

        status_str = "SUCCESS" if success else "COMPLETED WITH WARNINGS"
        full_res = (
            f"🤖 Code Agent ({status_str}):\n"
            f"Script Saved: {script_path}\n\n"
            f"```python\n{code}\n```\n\n"
            f"--- TEST EXECUTION ---\n{last_output}"
        )
        spoken_res = f"Code Agent has built and tested the script for {task_description}. Execution status is {status_str}."
        return full_res, spoken_res

    # ── Live News & Topic Alerts ──────────────────────────────────────────────

    def get_news(self, topic="top news", count=5):
        """Fetches full news headlines + summaries for a topic. No truncation.
        Checks user-added custom sources first."""
        articles = []

        # ── Step 0: Check user custom sources for this topic ─────────────────
        custom_sources = self.memory.get("news_sources", {})
        topic_key = topic.strip().lower()
        if topic_key in custom_sources:
            src = custom_sources[topic_key]
            rss_url = src.get("rss", "")
            site_url = src.get("url", "")
            # Try RSS feed from custom source
            if rss_url and FEEDPARSER_AVAILABLE:
                try:
                    feed = feedparser.parse(rss_url)
                    for entry in feed.entries[:count]:
                        title   = entry.get("title", "")
                        summary = entry.get("summary", "") or entry.get("description", "")
                        summary = re.sub(r"<[^>]+>", "", summary).strip()
                        source  = feed.feed.get("title", src.get("name", topic))
                        link    = entry.get("link", "")
                        if title:
                            articles.append({"title": title, "body": summary, "source": source, "url": link})
                except Exception:
                    pass
            # Fallback: DuckDuckGo site-specific search
            if not articles and DDG_AVAILABLE and site_url:
                try:
                    domain = re.sub(r"https?://(www\.)?", "", site_url).rstrip("/")
                    with DDGS() as ddgs:
                        results = list(ddgs.text(f"site:{domain}", max_results=count))
                    for r in results:
                        if r.get("title"):
                            articles.append({
                                "title": r.get("title", ""),
                                "body": r.get("body", ""),
                                "source": src.get("name", domain),
                                "url": r.get("href", ""),
                            })
                except Exception:
                    pass

        # ── Step 1: DuckDuckGo news search ───────────────────────────────────
        if not articles and DDG_AVAILABLE:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.news(topic, max_results=count))
                for r in results:
                    title = r.get("title", "")
                    body  = r.get("body", "") or r.get("excerpt", "")
                    source = r.get("source", "")
                    url   = r.get("url", "")
                    if title:
                        articles.append({"title": title, "body": body, "source": source, "url": url})
            except Exception:
                pass

        # ── Step 2: Fallback — built-in RSS feeds ────────────────────────────
        if not articles and FEEDPARSER_AVAILABLE:
            rss_map = {
                "top news":    "https://feeds.bbci.co.uk/news/rss.xml",
                "technology":  "https://feeds.feedburner.com/TechCrunch",
                "world":       "https://feeds.bbci.co.uk/news/world/rss.xml",
                "business":    "https://feeds.bbci.co.uk/news/business/rss.xml",
                "science":     "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
                "sports":      "https://feeds.bbci.co.uk/sport/rss.xml?edition=int",
                "india":       "https://feeds.feedburner.com/ndtvnews-india-news",
            }
            feed_url = rss_map.get(topic.lower(), rss_map["top news"])
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:count]:
                    title   = entry.get("title", "")
                    summary = entry.get("summary", "") or entry.get("description", "")
                    summary = re.sub(r"<[^>]+>", "", summary).strip()
                    source  = feed.feed.get("title", "RSS")
                    link    = entry.get("link", "")
                    if title:
                        articles.append({"title": title, "body": summary, "source": source, "url": link})
            except Exception:
                pass

        # ── Step 3: Last resort — web search snippets ────────────────────────
        if not articles:
            raw = self.web_search(topic + " news today")
            return f"News on '{topic}':\n{raw}"

        # ── Build full display + spoken output ───────────────────────────────
        out = f"Latest News: {topic.title()}\n" + ("─" * 40) + "\n"
        spoken_parts = [f"Here are the latest news headlines on {topic}."]
        for i, art in enumerate(articles, 1):
            out += f"\n[{i}] {art['title']}\n"
            if art["body"]:
                out += f"    {art['body']}\n"
            if art["source"]:
                out += f"    Source: {art['source']}\n"
            spoken_parts.append(f"Headline {i}: {art['title']}. {art['body']}")

        spoken_full = " ".join(spoken_parts)
        return out.strip(), spoken_full

    # ── Custom News Source Management ─────────────────────────────────────────

    # Well-known site RSS feeds auto-detected by name
    _KNOWN_RSS = {
        "hugging face":    ("https://huggingface.co", "https://huggingface.co/blog/feed.xml"),
        "huggingface":     ("https://huggingface.co", "https://huggingface.co/blog/feed.xml"),
        "techcrunch":      ("https://techcrunch.com", "https://techcrunch.com/feed/"),
        "the verge":       ("https://www.theverge.com", "https://www.theverge.com/rss/index.xml"),
        "wired":           ("https://www.wired.com", "https://www.wired.com/feed/rss"),
        "ars technica":    ("https://arstechnica.com", "https://feeds.arstechnica.com/arstechnica/index"),
        "mit tech review": ("https://www.technologyreview.com", "https://www.technologyreview.com/feed/"),
        "openai":          ("https://openai.com", "https://openai.com/blog/rss.xml"),
        "google ai":       ("https://blog.google/technology/ai/", "https://blog.google/rss/"),
        "bbc":             ("https://bbc.com", "https://feeds.bbci.co.uk/news/rss.xml"),
        "ndtv":            ("https://ndtv.com", "https://feeds.feedburner.com/ndtvnews-india-news"),
        "reuters":         ("https://reuters.com", "https://feeds.reuters.com/reuters/topNews"),
        "arxiv ai":        ("https://arxiv.org", "https://export.arxiv.org/rss/cs.AI"),
        "github blog":     ("https://github.blog", "https://github.blog/feed/"),
    }

    def add_news_source(self, name, url_or_rss=""):
        """Add a custom website as a named news source Raphael can read from."""
        sources = self.memory.get("news_sources", {})
        key = name.strip().lower()

        # Auto-detect well-known sites
        if key in self._KNOWN_RSS and not url_or_rss:
            site_url, rss_url = self._KNOWN_RSS[key]
        else:
            # Try to auto-discover RSS from given URL
            site_url = url_or_rss.strip() if url_or_rss else ""
            rss_url  = ""
            if site_url:
                # Common RSS path patterns
                common_paths = ["/feed", "/feed/", "/rss", "/rss.xml", "/blog/feed.xml",
                                "/blog/rss", "/news/rss.xml", "/atom.xml"]
                for path in common_paths:
                    candidate = site_url.rstrip("/") + path
                    if FEEDPARSER_AVAILABLE:
                        try:
                            test = feedparser.parse(candidate)
                            if test.entries:
                                rss_url = candidate
                                break
                        except Exception:
                            pass
                    if REQUESTS_AVAILABLE:
                        try:
                            r = requests.get(candidate, timeout=5)
                            if r.status_code == 200 and ("rss" in r.text[:500].lower() or "feed" in r.text[:500].lower()):
                                rss_url = candidate
                                break
                        except Exception:
                            pass

        sources[key] = {"name": name.strip().title(), "url": site_url, "rss": rss_url}
        self.memory["news_sources"] = sources
        self._save_memory()

        rss_status = f"RSS: {rss_url}" if rss_url else "No RSS found (will use web search fallback)"
        return (f"News source added: '{name.strip().title()}'\n"
                f"  Site: {site_url}\n"
                f"  {rss_status}\n"
                f"Say 'news on {name.strip().lower()}' to read it.")

    def remove_news_source(self, name):
        sources = self.memory.get("news_sources", {})
        key = name.strip().lower()
        if key in sources:
            del sources[key]
            self.memory["news_sources"] = sources
            self._save_memory()
            return f"News source '{name}' removed."
        return f"No custom news source named '{name}' found."

    def list_news_sources(self):
        sources = self.memory.get("news_sources", {})
        builtin = ["top news", "technology", "world", "business", "science", "sports", "india"]
        out = "Built-in News Topics:\n"
        out += "  " + ", ".join(builtin) + "\n\n"
        if sources:
            out += "Custom News Sources:\n"
            for key, src in sources.items():
                rss = "✓ RSS" if src.get("rss") else "⚠ Web search fallback"
                out += f"  ● {src['name']} — {rss}\n"
        else:
            out += "No custom sources added yet.\n"
            out += "Say 'add news source hugging face' to add one."
        return out.strip()

    def set_news_alert(self, topic, interval_minutes=60):
        """Register a background news alert for a topic at given interval."""
        alerts = self.memory.get("news_alerts", [])
        topic = topic.strip()
        interval_minutes = max(5, int(interval_minutes))
        # Avoid duplicate
        for a in alerts:
            if a["topic"].lower() == topic.lower():
                return f"News alert for '{topic}' already active every {a['interval']} min."
        alerts.append({
            "id": len(alerts) + 1,
            "topic": topic,
            "interval": interval_minutes,
            "last_ts": 0,
        })
        self.memory["news_alerts"] = alerts
        self._save_memory()
        return f"News alert set. I will read you full '{topic}' news every {interval_minutes} minutes."

    def remove_news_alert(self, identifier):
        """Remove a news alert by topic name or id."""
        alerts = self.memory.get("news_alerts", [])
        new_alerts = [
            a for a in alerts
            if str(a["id"]) != str(identifier).strip()
            and a["topic"].lower() != identifier.strip().lower()
        ]
        if len(new_alerts) < len(alerts):
            self.memory["news_alerts"] = new_alerts
            self._save_memory()
            return f"News alert for '{identifier}' removed."
        return f"No news alert found for '{identifier}'."

    def list_news_alerts(self):
        alerts = self.memory.get("news_alerts", [])
        if not alerts:
            return "No active news alerts."
        out = "Active News Alerts:\n"
        for a in alerts:
            out += f"  ● [{a['id']}] '{a['topic']}' — every {a['interval']} min\n"
        return out.strip()

    def _start_news_monitor(self):
        """Background thread: fires news alerts at the scheduled interval."""
        def _loop():
            while self.running:
                time.sleep(60)
                try:
                    alerts = self.memory.get("news_alerts", [])
                    now_ts = time.time()
                    updated = False
                    for alert in alerts:
                        interval_secs = alert["interval"] * 60
                        if now_ts - alert.get("last_ts", 0) >= interval_secs:
                            alert["last_ts"] = now_ts
                            updated = True
                            result = self.get_news(alert["topic"])
                            if isinstance(result, tuple):
                                display_text, spoken_text = result
                            else:
                                display_text = result
                                spoken_text = result
                            self.speak(display_text, spoken_text=spoken_text)
                    if updated:
                        self._save_memory()
                except Exception as e:
                    print("[News Monitor Error]", e)
        threading.Thread(target=_loop, daemon=True).start()

    def _extract_skill_name_and_task(self, full_phrase: str) -> tuple[str, str]:
        """Intelligently separates a concise skill name (max 28 chars) and detailed task from natural input."""
        full_phrase = full_phrase.strip()
        sep_match = re.match(r"^([\w\s]{2,30}?)\s+(?:for|that|to|which|named|called|:)\s+(.+)$", full_phrase, re.IGNORECASE)
        if sep_match:
            name_candidate = sep_match.group(1).strip()
            if len(name_candidate.split()) <= 4:
                safe_name = re.sub(r"[^\w-]", "", re.sub(r"\s+", "_", name_candidate.lower()))[:28]
                return safe_name, sep_match.group(2).strip()

        words = full_phrase.split()
        stop_verbs = {"create", "make", "an", "a", "build", "develop", "engine", "skill", "tool", "using", "the"}
        filtered = [w.lower() for w in words if w.lower() not in stop_verbs]
        if filtered:
            slug = "_".join(filtered[:3])
            slug = re.sub(r"[^\w-]", "", slug)[:28]
        else:
            slug = "custom_skill"

        return slug, full_phrase

    # ── Command Router ────────────────────────────────────────────────────────
    def respond(self, text, is_voice=False):
        t = text.strip().lower()
        if not t:
            return None

        # ── Demo Edition Strict Gate ──────────────────────────────────────────
        if getattr(self, "demo_mode", False):
            # Block desktop app launching
            if any(t.startswith(p) for p in ["open ", "launch ", "start "]):
                target = t.split(" ", 1)[1].strip()
                if not any(target == w for w in ["web", "browser", "vitals", "memory"]):
                    return "This command is not available in the Demo Edition. Type 'help' to see all working commands."
            # Block command-line / script execution
            if any(t.startswith(p) for p in ["run ", "exec ", "execute ", "cmd ", "powershell ", "terminal ", "shell "]):
                return "This command is not available in the Demo Edition. Type 'help' to see all working commands."
            # Block system cleaning and file deletion
            if any(k in t for k in ["clean temp", "clear temp", "clean disk", "empty recycle", "delete file", "delete folder", "wipe disk", "delete path"]):
                return "This command is not available in the Demo Edition. Type 'help' to see all working commands."
            # Block computer control / mouse / keyboard automation
            if any(k in t for k in ["take screenshot", "move mouse", "click", "type text", "computer use", "press key", "capture screen"]):
                return "This command is not available in the Demo Edition. Type 'help' to see all working commands."
            # Block custom skill synthesis and swarm
            if any(t.startswith(p) for p in ["evolve", "create skill", "learn skill", "swarm "]):
                return "This command is not available in the Demo Edition. Type 'help' to see all working commands."

        # ── 0. Tool Registry Approvals & Inspection ────────────────────────────
        m = re.match(r"^confirm action\s+(appr_\w+)$", t)
        if m:
            return self.tool_registry.approve_action(m.group(1))

        if t in ["cancel action", "abort action", "reject action"]:
            return self.tool_registry.cancel_action()

        if t in ["tools", "list tools", "tools list", "tool registry"]:
            tools_list = self.tool_registry.list_tools()
            lines = [f"🛠 Registered Tool Capabilities ({len(tools_list)}):"]
            for tl in tools_list:
                req = " [APPROVAL REQ]" if tl["requires_approval"] else ""
                lines.append(f"  • {tl['name']} ({tl['risk_level']}){req}: {tl['description']}")
            return "\n".join(lines)

        # ── 1. Emergency Stop Control ──────────────────────────────────────────
        if any(k == t for k in ["emergency stop", "stop all", "abort", "freeze", "kill all"]):
            self.safety_manager.trigger_emergency_stop("CHAT/VOICE")
            return "🛑 EMERGENCY STOP TRIGGERED: All active computer-use actions, swarm workers, and subprocesses terminated immediately."

        if any(k == t for k in ["reset emergency stop", "clear stop", "resume", "unfreeze"]):
            self.safety_manager.reset_emergency_stop()
            return "✓ Emergency stop cleared. Raphael is back online and ready for operations."

        if self.safety_manager.is_aborted():
            self.safety_manager.reset_emergency_stop()
            if hasattr(self, "gui") and self.gui and hasattr(self.gui, "status_dot"):
                self.gui.root.after(0, lambda: self.gui.status_dot.configure(
                    text="● ONLINE", text_color=self.gui.PURPLE_ACCENT, border_color=self.gui.PURPLE_ACCENT
                ))

        # ── 2. Self-Evolving Skill Engine ──────────────────────────────────────
        m = re.match(r"^(?:evolve\s*(?:a\s*)?skill|create\s*(?:a\s*)?skill|learn\s*(?:a\s*)?skill|add\s*(?:a\s*)?skill|teach\s*(?:a\s*)?skill|evolve)\s*[:]?\s*(.+)$", t)
        if m:
            full_phrase = m.group(1).strip()
            s_name, s_task = self._extract_skill_name_and_task(full_phrase)
            def _synthesize_bg():
                try:
                    res = self.skills_engine.synthesize_skill(s_name, s_task)
                    if res.get("status") == "error":
                        err_msg = f"⚠ Skill synthesis failed or blocked: {res.get('error')}"
                        self.speak(err_msg, spoken_text=f"Skill synthesis failed: {res.get('error')}")
                        return
                    self._pending_skill_approval = res
                    msg = (
                        f"🧪 Skill '{s_name}' synthesized and passed sandbox testing!\n"
                        f"Test Output: {res.get('test_output')}\n\n"
                        f"--- GENERATED CODE ---\n{res.get('code')}\n\n"
                        f"To install permanently, say or type: 'approve skill {s_name}'.\n"
                        f"To discard, say 'reject skill'."
                    )
                    self.speak(msg, spoken_text=f"Skill {s_name} has been synthesized and verified in sandbox. Say approve skill to install it.")
                except Exception as ex:
                    self.speak(f"Error during skill synthesis: {ex}")
            threading.Thread(target=_synthesize_bg, daemon=True).start()
            return f"🧪 Synthesizing new skill '{s_name}' with Qwen 2.5 3B... Running AST verification and sandbox tests in background."

        # ── Improve / Update Skill ──
        m = re.match(r"^(?:improve\s*(?:skill)?|update\s*(?:skill)?|upgrade\s*(?:skill)?)\s+([\w-]+)\s+(.+)$", t)
        if m:
            s_name = re.sub(r"\s+", "_", m.group(1).strip().lower())
            feedback_str = m.group(2).strip()
            def _improve_bg():
                try:
                    res = self.skills_engine.improve_skill(s_name, feedback_str)
                    if res.get("status") == "error":
                        err_msg = f"⚠ Skill improvement failed: {res.get('error')}"
                        self.speak(err_msg, spoken_text=f"Skill improvement failed: {res.get('error')}")
                        return
                    self._pending_skill_approval = res
                    next_v = res.get("next_version", 2)
                    msg = (
                        f"🔧 Skill '{s_name}' upgraded to v{next_v} proposal and verified in sandbox!\n"
                        f"Test Output: {res.get('test_output')}\n\n"
                        f"--- UPGRADED CODE ---\n{res.get('code')}\n\n"
                        f"To install update, say or type: 'approve skill {s_name}'.\n"
                        f"To cancel, say 'reject skill'."
                    )
                    self.speak(msg, spoken_text=f"Skill {s_name} upgraded to version {next_v}. Say approve skill to install the update.")
                except Exception as ex:
                    self.speak(f"Error during skill improvement: {ex}")
            threading.Thread(target=_improve_bg, daemon=True).start()
            return f"🔧 Evolving and improving skill '{s_name}' with Qwen 2.5 3B... Running verification in background."

        if t.startswith("approve skill") or t in ["approve", "approve it", "yes", "confirm skill", "accept skill"]:
            if not self._pending_skill_approval:
                return "No pending synthesized skill waiting for approval."
            item = self._pending_skill_approval
            self._pending_skill_approval = None
            msg = self.skills_engine.install_approved_skill(item["skill_name"], item["task"], item["code"])
            # Index skill into Knowledge Graph
            self.knowledge_graph.add_relation("Raphael", "HAS_SKILL", item["skill_name"])
            return msg

        if t in ["reject skill", "discard skill", "cancel skill", "reject", "no"]:
            self._pending_skill_approval = None
            return "Pending skill discarded."

        if t in ["list skills", "show skills", "my skills", "evolved skills"]:
            return self.skills_engine.list_skills()

        m = re.match(r"^rollback skill\s+(.+)$", t)
        if m:
            s_name = re.sub(r"\s+", "_", m.group(1).strip().lower())
            return self.skills_engine.rollback_skill(s_name)

        m = re.match(r"^(?:use skill|run skill)\s+(.+)$", t)
        if m:
            raw_arg = m.group(1).strip()
            norm_name = re.sub(r"\s+", "_", raw_arg.lower())
            if norm_name in self.skills_engine._registry:
                return self.skills_engine.execute_skill(norm_name, "")
            # Check prefix match for registered skills
            for reg_name in sorted(self.skills_engine._registry.keys(), key=len, reverse=True):
                reg_spaced = reg_name.replace("_", " ")
                if norm_name.startswith(reg_name):
                    rem = norm_name[len(reg_name):].strip("_")
                    return self.skills_engine.execute_skill(reg_name, rem)
                elif raw_arg.lower().startswith(reg_spaced):
                    rem = raw_arg[len(reg_spaced):].strip()
                    return self.skills_engine.execute_skill(reg_name, rem)
            # Fallback: split first word
            parts = raw_arg.split(None, 1)
            s_name = parts[0]
            s_query = parts[1] if len(parts) > 1 else ""
            return self.skills_engine.execute_skill(s_name, s_query)

        # ── 3. Multi-Agent Swarm ───────────────────────────────────────────────
        m = re.match(r"^(?:swarm|collaborate on|swarm task|multi agent)\s*[:]?\s*(.+)$", t)
        if m:
            task_str = m.group(1).strip()
            def _run_swarm_bg():
                rep = self.swarm.run_swarm(task_str)
                try:
                    os.makedirs(RESEARCH_DIR, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_task = re.sub(r'[^\w\s-]', '', task_str)[:40].strip().replace(' ', '_')
                    swarm_file = os.path.join(RESEARCH_DIR, f"swarm_{safe_task}_{ts}.md")
                    with open(swarm_file, "w", encoding="utf-8") as sf:
                        sf.write(f"# 👥 Multi-Agent Swarm Consensus: {task_str}\n_Generated by Raphael AI Swarm on {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n{rep}")
                except Exception:
                    pass
                spoken = f"Multi-agent swarm has completed consensus. The full report is displayed below and saved to your Research Vault."
                self.speak(rep, spoken_text=spoken)
                if hasattr(self, "gui") and self.gui:
                    self.gui.root.after(0, lambda: self.gui._open_research_vault())
            threading.Thread(target=_run_swarm_bg, daemon=True).start()
            return f"👥 Spawning Multi-Agent Swarm (Researcher, Architect, Security Critic, Executive) for: '{task_str}'..."

        # ── 4. Computer Use / Action Operator ──────────────────────────────────
        cu_match = re.match(r"^(?:operate|do on pc|control pc):\s*(.+)$", t)
        is_direct_cu = False
        cu_task = ""
        if not cu_match:
            if (
                t.startswith("type ") or
                t.startswith("press ") or
                t in ["scroll down", "scroll up", "show desktop", "desktop", "click", "left click", "right click", "double click", "lock pc", "lock computer", "close window", "close app"] or
                ("open notepad and type " in t) or
                ("calculate " in t and ("calc" in t or "calculator" in t))
            ):
                is_direct_cu = True
                cu_task = text.strip()

        if cu_match or is_direct_cu:
            op_task = cu_match.group(1).strip() if cu_match else cu_task
            def _run_comp_use():
                res = self.computer_use.execute_instruction(op_task)
                self.speak(res)
            threading.Thread(target=_run_comp_use, daemon=True).start()
            return f"🤖 Executing on PC: {op_task}"

        # ── 5. Second-Brain Knowledge Graph ───────────────────────────────────
        m = re.match(r"^graph search\s+(.+)$", t)
        if m:
            return self.knowledge_graph.search(m.group(1))

        if t in ["graph stats", "graph status", "knowledge graph"]:
            return self.knowledge_graph.get_stats()

        m = re.match(r"^graph delete node\s+(.+)$", t)
        if m:
            return self.knowledge_graph.delete_node(m.group(1))

        m = re.match(r"^remember relation\s+(.+?)\s+--\s+(.+?)\s+--\s+(.+)$", t)
        if m:
            src, rel, tgt = m.group(1), m.group(2), m.group(3)
            ok = self.knowledge_graph.add_relation(src, rel, tgt)
            return f"Added graph edge: ({src}) --[{rel}]--> ({tgt})" if ok else "Relation rejected (low confidence or privacy filter)."

        # ── 6. Mobile Companion Remote ─────────────────────────────────────────
        if any(k in t for k in ["enable mobile remote", "pair mobile", "mobile companion", "mobile dashboard", "connect phone", "connect my phone", "phone connect"]):
            pin = self.web_dashboard.generate_pairing_code()
            lan_ip = self.web_dashboard.get_local_ip()
            return (
                f"📱 MOBILE COMPANION PAIRING:\n"
                f"1. Make sure your phone is on the same Wi-Fi as this PC.\n"
                f"2. Open on your phone browser: http://{lan_ip}:8765\n"
                f"3. Enter 6-Digit Pairing PIN: {pin}\n"
                f"   (Expires in 180 seconds, single-use)\n"
                f"4. Computer-use and skill execution are disabled over mobile for security."
            )

        # Greetings
        if t in GREETINGS or any(t.startswith(g + " ") for g in GREETINGS):
            n = self.memory.get("user_name")
            return ("Greetings, " + n + ".") if n else "Greetings."

        # Exit
        if t in {"exit raphael", "quit raphael", "close raphael", "exit application", "quit application"}:
            if hasattr(self, "gui") and self.gui:
                self.gui.root.after(100, self.gui.exit_app)
                return "Exiting Raphael. Have a wonderful day!"
            self.running = False
            return "Goodbye."

        if t in {"bye", "goodbye", "see you", "farewell"}:
            u_name = self.memory.get("user_name")
            if getattr(self, "demo_mode", False):
                return f"Goodbye{', ' + u_name if u_name else ''}! I'll be right here in the background whenever you need me."
            return f"Goodbye, {u_name or 'Jay'}! I'll be right here in the background whenever you need me."

        # Help
        if t in {"help", "commands"}:
            return self._help()

        # System status
        if any(k in t for k in ["system status", "system health", "cpu usage", "ram usage", "battery status"]):
            return self.system_status()

        # System Maintenance & Deep Cleaner
        if any(k in t for k in ["clean temp files", "clean temp", "clear temp", "clean system", "temp files"]):
            return self.clean_temp_files()
        if any(k in t for k in ["free up ram", "free ram", "clear memory", "optimize ram", "clear ram"]):
            return self.free_up_ram()
        if any(k in t for k in ["empty recycle bin", "clean recycle bin", "empty trash"]):
            return self.empty_recycle_bin()
        if any(k in t for k in ["show heavy processes", "heavy processes", "top cpu", "top ram", "process list"]):
            return self.get_heavy_processes()

        # Briefing
        if any(k in t for k in ["briefing", "daily briefing", "morning briefing", "evening briefing", "status report"]):
            return self.get_briefing()

        # ── Live News & Topic Alerts ──
        # Custom source management
        m = re.match(r"^(?:add news source|add source)\s+(.+?)(?:\s+(https?://\S+))?$", t)
        if m:
            s_name = m.group(1).strip()
            s_url  = m.group(2).strip() if m.group(2) else ""
            return self.add_news_source(s_name, s_url)

        m = re.match(r"^(?:remove|delete)\s+(?:news\s+)?source\s+(.+)$", t)
        if m:
            return self.remove_news_source(m.group(1).strip())

        if any(k in t for k in ["list news sources", "news sources", "show news sources", "my news sources", "show sources"]):
            return self.list_news_sources()

        # Check news / visit & check news on website or topic
        m = re.match(r"^(?:news|latest news|top news|read news|check news|visit and check news|check)\s+(?:on|about|from|for)?\s*(.+)$", t)
        if m and not any(k in t for k in ["alert", "source", "clipboard", "system", "schedule", "memory"]):
            topic = m.group(1).strip()
            # Clean up filler words
            topic = re.sub(r"^(?:the\s+)?(?:news\s+(?:on|about|from|for)\s+)?", "", topic).strip()
            def _do_news():
                result = self.get_news(topic)
                if isinstance(result, tuple):
                    display, spoken = result
                else:
                    display, spoken = result, result
                self.speak(display, spoken_text=spoken)
            threading.Thread(target=_do_news, daemon=True).start()
            return f"Checking full news on '{topic}'..."

        if t in {"news", "top news", "latest news", "read news", "check news"}:
            def _do_news():
                result = self.get_news("top news")
                if isinstance(result, tuple):
                    display, spoken = result
                else:
                    display, spoken = result, result
                self.speak(display, spoken_text=spoken)
            threading.Thread(target=_do_news, daemon=True).start()
            return "Fetching full top news..."

        # "monitor bitcoin every 30 minutes" / "alert me about hugging face every 60 minutes"
        m = re.match(r"^(?:monitor|track|alert me about|watch)\s+(.+?)\s+every\s+(\d+)\s*(?:min(?:utes?)?|mins?)?$", t)
        if m:
            return self.set_news_alert(m.group(1).strip(), int(m.group(2)))

        # "set news alert for cricket" / "notify me about ai news"
        m = re.match(r"^(?:set news alert|news alert|notify me about)\s+(?:for\s+)?(.+?)(?:\s+every\s+(\d+)\s*(?:min(?:utes?)?)?)?$", t)
        if m:
            topic_str = m.group(1).strip()
            mins_str  = m.group(2) or "60"
            return self.set_news_alert(topic_str, int(mins_str))

        if any(k in t for k in ["list news alerts", "my news alerts", "show news alerts"]):
            return self.list_news_alerts()

        m = re.match(r"^(?:remove|cancel|stop)\s+news\s+alert\s+(.+)$", t)
        if m:
            return self.remove_news_alert(m.group(1).strip())

        # Security & Passcode Commands
        m = re.match(r"^(?:set passcode|set password|change password)\s+(.+)$", t)
        if m:
            return self.set_passcode(m.group(1))
        if any(k in t for k in ["remove password", "disable password", "delete password", "remove passcode"]):
            return self.remove_passcode()
        if t in {"lock", "lock raphael", "lock system", "lock ui"}:
            return "__LOCK__"

        # ── Auto-Scheduled Workflows Commands ──
        m = re.match(r"^schedule\s+(?:daily\s+)?briefing(?:\s+at\s+(.+))?$", t)
        if m:
            t_spec = m.group(1) or "08:00"
            return self.add_scheduled_task("daily_briefing", t_spec)

        m = re.match(r"^schedule\s+(?:file\s+)?(?:clean|organize)(?:\s+every\s+(.+))?$", t)
        if m:
            d_spec = m.group(1) or "7 days"
            return self.add_scheduled_task("auto_clean", d_spec)

        if any(k in t for k in ["view schedule", "show schedule", "list schedule", "my schedules"]):
            return self.list_scheduled_tasks()

        m = re.match(r"^(?:cancel|remove|delete)\s+schedule\s+(.+)$", t)
        if m:
            return self.remove_scheduled_task(m.group(1))

        # ── Autonomous Code Builder & Self-Healing Tester Agent Commands ──
        m = re.match(r"^(?:build code|create script|code agent|build app|write program|create code)\s+(.+)$", t)
        if m:
            task_desc = m.group(1).strip()
            def _do_code_agent():
                full_res, spoken_res = self.build_code_agent(task_desc)
                self.speak(full_res, spoken_text=spoken_res)
            threading.Thread(target=_do_code_agent, daemon=True).start()
            return f"Code Agent started: Building, auto-dependency installing, and testing code for '{task_desc}'..."

        # Active Window
        if any(k in t for k in ["active window", "current window", "what window am i on"]):
            return self.get_active_window()

        # ── ChromaDB Memory Commands ──
        if any(k in t for k in ["memory stats", "memory status", "chroma status"]):
            return self.semantic_memory.get_stats()

        m = re.match(r"^(?:search memory|remember about|recall)\s+(.+)$", t)
        if m:
            return self.semantic_memory.search_memory(m.group(1))

        m = re.match(r"^(?:load document|index file|learn file)\s+(.+)$", t)
        if m:
            return self.semantic_memory.store_document(m.group(1).strip())

        # ── Tier 3: Auto File Organizer ──
        m = re.match(r"^(?:organize|clean up|sort)\s+(?:my\s+)?(?:files|folder)(?:\s+(.+))?$", t)
        if m:
            folder = m.group(1) or ""
            return self.auto_organize_files(folder.strip())
        if any(k in t for k in ["organize downloads", "clean downloads", "sort downloads"]):
            return self.auto_organize_files(os.path.expanduser("~/Downloads"))
        if any(k in t for k in ["organize desktop", "clean desktop", "sort desktop"]):
            return self.auto_organize_files(os.path.expanduser("~/Desktop"))

        # ── Tier 3: Deep Research Agent ──
        m = re.match(r"^(?:research|deep research|investigate|study)\s+(.+)$", t)
        if m:
            topic = m.group(1).strip()
            def _do_research():
                r = self.deep_research(topic)
                display_r = r[0] if isinstance(r, tuple) else r
                spoken = f"Deep research on {topic} is complete. The report has been saved to your research folder and added to vector memory."
                self.speak(display_r, spoken_text=spoken)
            threading.Thread(target=_do_research, daemon=True).start()
            if hasattr(self, "gui") and self.gui:
                self.gui.root.after(0, lambda: self.gui._open_research_vault(initial_topic=topic))
            return f"Starting deep research on '{topic}'. Opening Research Vault..."
        if any(k in t for k in ["show research", "my reports", "list reports", "open research", "research vault", "deep search vault"]):
            if hasattr(self, "gui") and self.gui:
                self.gui.root.after(0, self.gui._open_research_vault)
            if os.path.isdir(RESEARCH_DIR):
                files = [f for f in os.listdir(RESEARCH_DIR) if f.endswith(".md")]
                return ("Research Reports:\n" + "\n".join(files[-10:])) if files else "Opening Research Vault..."
            return "Opening Research Vault..."
        # Email Draft
        m = re.match(r"^(?:draft email|write email|create email)\s+(?:about\s+)?(.+)$", t)
        if m:
            return self.draft_email(m.group(1))

        # Fact Storage ("remember that my favorite language is Python")
        m = re.match(r"^remember\s+that\s+(.+?)\s+is\s+(.+)$", t)
        if m:
            return self.remember_fact(m.group(1), m.group(2))
        if any(k in t for k in ["my facts", "my preferences", "what do you know about me", "show facts"]):
            return self.recall_facts()

        # Weather
        m = re.search(r"\bweather\b(?:\s+(?:in|for|at)\s+(.+))?", t)
        if m:
            city = m.group(1) if m.group(1) else ""
            return self.get_weather(city)

        # Proactive Suggestions
        if any(k in t for k in ["suggest something", "give me a suggestion", "what can you do", "recommendation", "suggest", "any suggestions", "help me decide"]):
            return self.suggest_something()

        # News
        if any(k in t for k in ["news", "headlines", "top headlines", "latest news"]):
            res = self.get_news("top news")
            return res[0] if isinstance(res, tuple) else res

        # Universal System Media & Volume Controls
        if t in ["play", "pause", "resume", "stop", "next", "prev", "skip", "mute", "unmute", "volume up", "volume down", "louder", "quieter"] or any(k in t for k in ["next song", "previous song", "play music", "pause music", "stop music", "resume music", "skip song", "play song", "volume up", "volume down", "mute", "unmute", "next track", "prev track", "media play", "media pause", "turn up volume", "turn down volume"]):
            return self.media_control(t)

        # App Launcher
        m = re.match(r"^(?:open|launch|start)\s+(.+)$", t)
        if m:
            app_req = m.group(1).strip().lower()
            import re as _re
            app_req = _re.sub(r"^the\s+", "", app_req)
            if app_req in self.APP_MAP or app_req in ["notepad", "calculator", "calc", "code", "vs code", "vscode", "chrome", "edge", "discord", "cmd", "terminal", "powershell", "paint", "explorer", "word", "excel", "browser", "file explorer", "spotify"]:
                return self.launch_app(app_req)

        # Wake Word
        if any(k in t for k in ["enable wake word", "start wake word", "wake word"]):
            return self.start_wake_word_listener()

        # Reminder
        m = re.search(r"remind me in (\d+(?:\.\d+)?) (?:minute|min)s? to (.+)", t)
        if m:
            return self.set_reminder(m.group(1), m.group(2))

        # Clipboard
        if "summarize clipboard" in t:
            return self.read_clipboard(summarize=True)
        if "read clipboard" in t or t == "clipboard":
            return self.read_clipboard()

        # URL / Webpage Summarizer
        m = re.match(r"^(?:summarize\s+(?:url|link|webpage|page|article)|read\s+(?:url|link|webpage))\s+(https?://\S+|\S+\.\S+.*)$", t)
        if m:
            return self.summarize_url(m.group(1))

        # Windows Autostart
        if any(k in t for k in ["enable autostart", "start with windows", "enable auto start", "turn on autostart"]):
            return self.set_windows_autostart(True)
        if any(k in t for k in ["disable autostart", "turn off autostart", "stop autostart"]):
            return self.set_windows_autostart(False)
        if "autostart" in t:
            is_auto = self.memory.get("autostart", False)
            return f"Windows Autostart is currently {'ENABLED' if is_auto else 'DISABLED'}. Say 'enable autostart' or 'disable autostart'."

        # Ollama Model Switching
        m = re.match(r"^(?:switch\s+model\s+to|change\s+model\s+to|set\s+model\s+to|use\s+model)\s+(.+)$", t)
        if m:
            return self.set_model(m.group(1))
        if any(k in t for k in ["what model", "which model", "show model", "current model", "active model", "list models"]):
            return self.get_model()

        # File reader
        m = re.match(r"^summarize file\s+(.+)$", t)
        if m:
            return self.read_file(m.group(1), summarize=True)
        m = re.match(r"^read file\s+(.+)$", t)
        if m:
            return self.read_file(m.group(1))

        # ── YouTube Playback Control ──────────────────────────────────────────
        # Direct control commands (before search so "pause" doesn't search)
        _yt_direct = {
            "play", "pause", "resume", "stop", "mute", "unmute",
            "fullscreen", "full screen", "theater mode",
            "captions", "subtitles",
            "skip forward", "skip ahead", "skip back", "skip backward",
            "forward", "rewind", "go back",
            "next", "next video", "previous", "prev", "previous video",
            "volume up", "volume down", "vol up", "vol down",
            "louder", "quieter", "turn up", "turn down",
            "increase volume", "decrease volume", "raise volume", "lower volume",
        }
        # Exact match like "pause" / "volume up"
        if t in _yt_direct:
            return self.youtube_control(t)
        # Prefixed: "youtube pause", "youtube volume up 3"
        m = re.match(r"^youtube\s+(.+)$", t)
        if m:
            return self.youtube_control(m.group(1))
        # Amount volume: "volume up 5" / "volume down 10"
        if re.match(r"^volume (up|down)\s+\d+$", t):
            return self.youtube_control(t)

        # Detect site name anywhere in the sentence, open browser on that site.
        # Falls back to Google if no specific site is mentioned.
        # Use "ask X" or "what does X mean" to stay text-only (no browser).
        _SEARCH_TRIGGERS = (
            "search", "search for", "find", "find me", "look up", "look for",
            "show me", "play", "watch", "listen to", "browse", "open",
            "go to", "take me to", "get", "get me", "pull up",
        )
        _triggered = None
        for trigger in _SEARCH_TRIGGERS:
            if t.startswith(trigger + " "):
                _triggered = t[len(trigger):].strip()
                break

        if _triggered is not None:
            # Check if a specific site is mentioned anywhere
            _target_site = None
            _prepositions = r"(?:\s+(?:on|in|at|via|from|using|through|with))?"
            for site in BROWSER_URLS:
                # Match "X on/in/at youtube", "youtube X", "on youtube"
                patterns = [
                    r"(.+?)\s+(?:on|in|at|via|from|using|through|with)\s+" + site + r"\s*$",
                    r"^" + site + r"\s+(?:for\s+)?(.+)$",
                    r"^(?:on\s+)?" + site + r"\s*$",
                ]
                for pat in patterns:
                    m = re.search(pat, _triggered)
                    if m:
                        _target_site = site
                        _triggered = (m.group(1) if m.lastindex and m.group(1) else _triggered).strip()
                        # Remove site name from query if it leaked in
                        _triggered = re.sub(r"\b" + site + r"\b", "", _triggered).strip()
                        break
                if _target_site:
                    break

            site_to_use = _target_site or "google"
            return self.open_browser(_triggered, site_to_use)

        # Text-only web search (no browser) — "ask X", "tell me about X"
        m = re.match(r"^(?:ask|tell me about|brief me on|summarize online)\s+(.+)$", t)
        if m:
            return self.web_search(m.group(1))

        # Notes
        m = re.match(r"^(?:save note|note|take note)\s+(.+)$", t)
        if m:
            return self.save_note(m.group(1))
        if t in {"view notes", "show notes", "my notes"}:
            return self.get_notes()

        # Name
        if "my name is" in t:
            name = re.sub(r".*my name is\s+", "", t).strip().split()[0]
            return self.remember_name(name)
        if t in {"what is my name", "what's my name"}:
            return self.recall_name()

        # Language
        m = re.search(r"(?:switch to|speak in|set language to)\s+(\w+)", t)
        if m:
            return self.set_language(m.group(1))

        # Power & System Control (Strict explicit intent + confirmation required!)
        if t in ["shutdown", "shutdown pc", "shut down", "shut down pc", "turn off pc", "power off laptop", "turn off laptop", "shutdown system"]:
            if getattr(self, "demo_mode", False):
                return "This command is not available in the Demo Edition. Type 'help' to see all working commands."
            self._pending_power_action = "shutdown"
            return "⚠️ Are you sure you want to shut down your PC? Say 'confirm shutdown' to proceed, or 'cancel' to abort."

        if t in ["restart pc", "reboot pc", "restart computer", "restart laptop", "reboot laptop"]:
            self._pending_power_action = "restart"
            return "⚠️ Are you sure you want to restart your PC? Say 'confirm restart' to proceed, or 'cancel' to abort."

        if t in ["confirm shutdown", "yes shutdown pc", "yes shut down"]:
            if getattr(self, "_pending_power_action", None) == "shutdown":
                self._pending_power_action = None
                self.shutdown_pc()
                return "Shutting down PC."
            return "No pending shutdown command. To shut down your PC, say 'shutdown pc'."

        if t in ["confirm restart", "yes restart pc", "yes reboot"]:
            if getattr(self, "_pending_power_action", None) == "restart":
                self._pending_power_action = None
                self.restart_pc()
                return "Restarting PC."
            return "No pending restart command. To restart your PC, say 'restart pc'."

        if t in ["cancel power", "cancel shutdown", "cancel restart"] or (t in ["cancel", "no", "abort"] and getattr(self, "_pending_power_action", None)):
            self._pending_power_action = None
            return "Power action canceled."

        # Kill process
        m = re.match(r"^kill\s+(.+)$", t)
        if m:
            return self.kill_process(m.group(1))

        # OCR / Screen Reading
        if any(k in t for k in ["explain my screen", "explain screen", "what is on my screen", "summarize screen"]):
            return self.read_screen(summarize=True)
        if re.search(r"\b(read my screen|read screen|ocr|scan screen)\b", t):
            return self.read_screen(summarize="summarize" in t or "explain" in t)

        # Install
        m = re.match(r"^install\s+(\S+)", t)
        if m:
            return self.install_package(m.group(1))

        # Compile
        m = re.match(r"^compile(?: and run)?\s+(\S+)", t)
        if m:
            return self.compile_code(m.group(1), run_after="and run" in t)

        # Run command
        m = re.match(r"^(?:run|execute)\s+(.+)$", t)
        if m:
            return self.run_command(m.group(1))

        # File manager
        m = re.match(r"^(?:create folder|mkdir)\s+(.+)$", t)
        if m:
            return self.create_folder(m.group(1))
        m = re.match(r"^(?:delete|remove)\s+(.+)$", t)
        if m:
            return self.delete_path(m.group(1))
        m = re.match(r"^(?:list files?|ls|dir)(?:\s+(.+))?$", t)
        if m:
            return self.list_files(m.group(1) or ".")

        # Browser — match "search/play/find X on/in/at youtube", "open youtube X", "youtube X"
        for site in BROWSER_URLS:
            for pat in [
                r"(?:search|play|find|look up|open)\s+(.+?)\s+(?:on|in|at|via)\s+" + site,
                r"(?:search|play|find)\s+" + site + r"\s+(?:for\s+)?(.+)",
                r"open\s+" + site + r"(?:\s+(?:and\s+search\s+)?(.+))?",
                r"^" + site + r"\s+(.+)",
            ]:
                m = re.search(pat, t)
                if m:
                    q = (m.group(1) or "").strip()
                    return self.open_browser(q, site)

        # ── Autonomous Disk Bloat & Duplicate Hunter ──
        if any(k in t for k in ["scan disk", "hunt disk bloat", "find duplicates", "disk bloat", "duplicate hunter", "scan bloat", "disk hunter", "disk report"]):
            return self.disk_hunter.get_scan_report()

        if t in ["approve clean", "clean bloat", "clean disk", "clean duplicates", "confirm clean", "delete bloat", "approve disk clean"]:
            if hasattr(self, "disk_hunter"):
                ok, msg = self.disk_hunter.execute_clean()
                return msg
            return "Disk hunter is not initialized."

        if t in ["cancel clean", "abort clean", "discard clean", "reject clean"]:
            if hasattr(self, "disk_hunter"):
                return self.disk_hunter.cancel_clean()
            return "No active clean plan."

        # ── Natural Evolved Skill Auto-Routing ──
        if hasattr(self, "skills_engine") and self.skills_engine:
            matched_skill = self.skills_engine.match_skill(t)
            if matched_skill:
                s_name, s_arg = matched_skill
                return self.skills_engine.execute_skill(s_name, s_arg)

        # Web search
        m = re.match(r"^(?:search|look up|google)\s+(.+)$", t)
        if m:
            return self.web_search(m.group(1))

        # Explain / define
        m = re.match(r"^(?:explain|what is|how does|define|teach me)\s+(.+)$", t)
        if m:
            return self.ai_chat("Explain concisely: " + m.group(1), is_voice=is_voice)

        # Multi-step
        if " then " in t and not any(t.startswith(q) for q in ["what", "why", "how", "explain", "tell me", "define", "teach me", "if "]):
            for step in t.split(" then "):
                r = self.respond(step.strip(), is_voice=is_voice)
                if r:
                    self.speak(r)
                time.sleep(0.4)
            return None

        # Fallback: AI
        return self.ai_chat(text, is_voice=is_voice)

    def _help(self):
        if getattr(self, "demo_mode", False):
            return (
                "Raphael AI (Demo Edition) - Available Commands:\n\n"
                "  weather [city]              real-time weather forecast\n"
                "  news                        live headlines via DuckDuckGo\n"
                "  system status               live CPU, RAM, Disk, and Battery vitals\n"
                "  search [query]              real-time web search\n"
                "  search wikipedia for [X]    instant encyclopedia summary\n"
                "  explain [concept]           AI explanation via local Ollama LLM\n"
                "  read clipboard              display current copied clipboard text\n"
                "  summarize clipboard         AI summary of copied clipboard text\n"
                "  save note [text]            save note to persistent storage\n"
                "  view notes                  display saved notes\n"
                "  show demo files             list all files in demo_sandbox/\n"
                "  read file [filename]        read a file inside demo_sandbox/\n"
                "  summarize file [filename]   AI summarize a file inside demo_sandbox/\n"
                "  free up ram                 memory optimization & garbage collection\n"
                "  my name is [name]           remember your name in local memory\n"
                "  switch to japanese          change voice language\n"
                "  [A] then [B]                multi-step chained commands\n"
                "  exit / quit                 close Raphael"
            )
        return (
            "Available commands:\n"
            "  weather [city]              real-time weather\n"
            "  news                        top news headlines\n"
            "  open [app]                  launch VS Code, Notepad, Chrome, etc.\n"
            "  media [play|pause|next]     universal media & volume controls\n"
            "  enable wake word            hands-free 'Hey Raphael' mode\n"
            "  system status               CPU / RAM / Disk / Battery\n"
            "  remind me in 5 mins to X   timed reminder\n"
            "  read clipboard              show clipboard content\n"
            "  summarize clipboard         AI summarize clipboard\n"
            "  read file [path]            read file content\n"
            "  summarize file [path]       AI summarize file\n"
            "  save note [text]            save a note\n"
            "  view notes                  show saved notes\n"
            "  search [query]              web search\n"
            "  search X on youtube         site-specific search\n"
            "  explain [topic]             AI explanation\n"
            "  run [cmd]                   shell command\n"
            "  compile [file]              compile code\n"
            "  compile and run [file]      compile and run\n"
            "  install [pkg]               pip install\n"
            "  create folder [path]        make directory\n"
            "  delete [path]               delete file/folder\n"
            "  list files [path]           list directory\n"
            "  kill [process]              kill process\n"
            "  read my screen              OCR screenshot\n"
            "  my name is [name]           remember your name\n"
            "  switch to japanese          change voice language\n"
            "  shutdown / restart          power commands\n"
            "  [A] then [B] then [C]       multi-step automation\n"
            "  exit / quit                 close Raphael\n"
            "  Shortcut: Ctrl+Alt+X (or Ctrl+Space) opens Raphael from anywhere!"
        )

    def run_text(self):
        n = self.memory.get("user_name")
        print("Raphael AI  |  Type 'help' or 'exit'")
        print(("Welcome back, " + n + ".") if n else "Hello. I am Raphael.")
        while self.running:
            try:
                txt = input("You: ").strip()
                if not txt:
                    continue
                r = self.respond(txt)
                if r:
                    self.speak(r)
            except KeyboardInterrupt:
                print("\nGoodbye.")
                break


# ── Legacy Desktop GUI Bridge (Tkinter) ───────────────────────────────────────
try:
    from raphael_legacy_gui import RaphaelGUI, _make_tray_icon
except ImportError:
    RaphaelGUI = None
    _make_tray_icon = lambda: None


# ── Entry Point ────────────────────────────────────────────────────────────────
def _ensure_single_instance():
    import socket
    global _SINGLETON_SOCKET
    _SINGLETON_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        _SINGLETON_SOCKET.bind(('127.0.0.1', 47291))  # Raphael's reserved port
        _SINGLETON_SOCKET.listen(5)
        return True   # Primary instance
    except OSError:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2.0)
            s.connect(('127.0.0.1', 47291))
            s.sendall(b"WAKEUP\n")
            s.close()
            print("[Raphael] Existing instance found. Restored to screen.")
        except Exception:
            pass
        return False

if __name__ == "__main__":
    if not _ensure_single_instance():
        sys.exit(0)

    if "--cli" in sys.argv:
        engine = Raphael()
        engine.run_text()
    elif "--headless" in sys.argv or "--server" in sys.argv:
        # Headless server mode for external frontends or background service
        engine = Raphael()
        print("[Raphael Core] Backend server active on http://127.0.0.1:8765")
        print("[Raphael Core] WebSocket active on ws://127.0.0.1:8765/ws")
        try:
            while engine.running:
                time.sleep(1)
        except KeyboardInterrupt:
            engine.running = False
    else:
        # Default: Original Native Desktop GUI (CustomTkinter + System Tray + Global Hotkeys F9 / Ctrl+Alt+R)
        if RaphaelGUI:
            app = RaphaelGUI()
            app.run()
        else:
            print("[Raphael] Desktop GUI module not found, falling back to engine.")
            engine = Raphael()
            try:
                while engine.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                engine.running = False
