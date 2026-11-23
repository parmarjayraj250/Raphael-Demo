# Raphael AI — Interface & Controls Guide (Demo Edition)

This guide provides a comprehensive breakdown of every button, chip, and interactive control in the **Raphael AI (Demo Edition)** interface, explaining what each feature does, how it works, and how safety guardrails protect your machine.

---

## 1. Top Header Bar

| Element | Appearance | What It Does |
|---|---|---|
| **Network Indicator** | `🌐 ONLINE` / `🚫 OFFLINE` | Real-time internet connectivity monitor. Dynamically shows `🌐 ONLINE` when internet/data is active and `🚫 OFFLINE` when disconnected. Clicking it checks connection status. |
| **Safety Badge** | `🛡 DEMO SAFE` | Highlights that the active session is running in isolated demo mode with strict deterministic guardrails. Clicking it opens the interactive help overview. |
| **Research Vault** | `🔬 RESEARCH` | Opens the Research Vault interface for synthesized multi-source intelligence reports. |
| **Window Controls** | `—` / `✕` | Minimizes to system tray or gracefully exits the application. |

---

## 2. Left Navigation Sidebar

| Button | Action / Command | Description |
|---|---|---|
| `🏠 Commands` | Primary View | Resets the conversation focus and brings up the main commands cockpit. |
| `⚙ System` | `system status` | Queries live CPU load, RAM allocation, disk capacity, and uptime. |
| `📑 Notes` | `view notes` | Displays the current notes stored in your demo session. |
| `🔍 Search` | `__search_prompt__` | Takes the query typed in the input box and runs an online search via DuckDuckGo. |
| `📁 Files` | `show demo files` | Safely lists all files residing inside the isolated `demo_sandbox/` workspace. |
| `❓ Help` | `help` | Prints the complete guide of safe commands supported by the Demo Edition. |
| `⚙ Settings` | `my facts` | Shows the local semantic memory facts known to Raphael. |

---

## 3. Quick Action Chips (Under Greeting)

Located immediately below your personalized greeting:

- **`💡 Suggest something`**: Asks the local Ollama LLM to propose creative ideas, productivity tips, or coding projects.
- **`📊 System Vitals`**: Performs an instant hardware check across CPU, RAM, and battery state.
- **`📁 Demo Sandbox`**: Inspects files inside `demo_sandbox/` without exposing any host directories.
- **`🔍 Search the web`**: Queries DuckDuckGo for live facts, current events, or documentation.
- **`🧠 Wikipedia`**: Queries Wikipedia directly for factual encyclopedic summaries (e.g., historical figures, scientific concepts).

---

## 4. Quick Command Bar

A row of 7 one-click cards for essential tasks:

1. **`☁ Weather`**: Fetches the current weather report and temperature forecast.
2. **`📁 Sandbox`**: Opens a view into the safe `demo_sandbox/` directory.
3. **`💡 AI Suggest`**: Triggers smart proactive suggestions from the model.
4. **`🔍 Search Web`**: Prompts you to search the live web.
5. **`📑 Notes`**: Views saved notes in Raphael's persistent store.
6. **`🧠 Wikipedia`**: Performs an instant encyclopedic summary of key concepts.
7. **`⚙ Free RAM`**: Runs safe Python garbage collection to optimize memory footprint.

---

## 5. Popick Command Chips

One-click command shortcuts for rapid testing:

- **`explain concept`**: Prompts the AI model to explain complex topics (e.g., *neuromorphic computing*).
- **`deep research`**: Initiates a multi-step structured research inquiry.
- **`search web`**: Triggers live web search mode.
- **`system status`**: Instant telemetry diagnostics readout.
- **`show demo files`**: Safe listing of items in the isolated workspace.
- **`summarize note`**: Reads and summarizes the current session notes.

---

## 6. Live Telemetry & Audio Visualizer

The right-hand side panels provide real-time hardware telemetry:

- **Live RAM Gauge**: Real-time progress bar tracking physical memory utilization percentage.
- **CPU & Battery**: Dynamically updated stats reflecting current operating system load.
- **Radar & Orb Visualizer**: Celestial pulse animation indicating AI processing state.
- **Equalizer**: Responds dynamically during speech synthesis and audio playback.

---

## 7. Chat Terminal, Input & File Jailing

- **Terminal Output Area**: Displays conversational turns between You and Raphael in formatted, glassmorphic bubbles.
- **Paperclip (`📎`) Attachment**:
  - Automatically defaults to the safe `demo_sandbox/` folder.
  - **Strict Sandbox Jail**: If an attempt is made to attach files from external host directories (such as `C:\Windows`, personal Documents, or user profiles), Raphael will refuse access with:
    > *🔒 Demo Edition: Only files inside the demo_sandbox folder can be attached.*
- **Microphone (`🎙`) Button**:
  - If optional speech dependencies (`SpeechRecognition` and `PyAudio`) are present and configured, records voice commands.
  - If hardware is not detected, provides an immediate, helpful message guiding you to type your query.
- **Send (`➤`) Button & Enter Key**: Submits your query to the local Ollama model.
- **Utility Buttons (`Clear`, `Copy`, `Export`)**: Allows clearing conversation history, copying the log to clipboard, or exporting the session transcript.

---

## 8. Isolated Workspace Architecture

The Demo Edition operates strictly within its designated workspace:
- **Jailed File Workspace**: File read, write, and summarize tools are strictly bound to `demo_sandbox/`.
- **Private Loopback**: Runs purely on `127.0.0.1` on local ports, communicating only with local Ollama.
