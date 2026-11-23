# Raphael AI — Celestial Edge (Demo Edition)

> **Safe, local AI desktop companion with native HUD, real-time web search, system vitals, and jailed sandbox.**

Raphael AI (Demo Edition) is a lightweight, safe preview of Raphael AI designed to run locally on Windows without requiring a browser or complex runtime environments.

---

## ✨ Features

- **Native CustomTkinter Desktop UI**: Celestial Edge dark theme with audio visualizer, status indicators, and sleek controls.
- **Local AI Conversations**: Fully offline, private chat powered by Ollama (`qwen2.5:3b`).
- **Real-Time Web Intelligence**: Web search via DuckDuckGo and encyclopedia lookups via Wikipedia.
- **Live System Vitals**: Real-time read-only CPU, RAM, and battery metrics.
- **Voice Feedback & Chimes**: Optional neural text-to-speech feedback and startup audio.
- **Zero Browser & Zero Electron**: Runs 100% natively on Windows.

---

## 📖 Documentation & Controls Guide

For an in-depth breakdown of every button, action chip, navigation tab, and safety jail in the UI, check out the **[Interface & Controls Guide](INTERFACE_GUIDE.md)**.

---

## 📁 Workspace Isolation (Demo Edition)

- **Dedicated Sandbox**: File operations (reading, writing, summarizing) are isolated within the `demo_sandbox/` directory.
- **100% Private**: Runs purely on local loopback (`127.0.0.1`), ensuring zero external network exposure.

---

## 🚀 Quick Start (Windows 10 / 11)

### 1. Prerequisites
- **Python 3.10+**: Download from [python.org](https://www.python.org/downloads/) *(ensure "Add Python to PATH" is checked)*.
- **Ollama**: Download from [ollama.com](https://ollama.com). Pull the model:
  ```powershell
  ollama run qwen2.5:3b
  ```

### 2. Setup
1. Clone this repository or download the ZIP:
   ```powershell
   git clone https://github.com/parmarjayraj250/Raphael-Demo.git
   cd Raphael-Demo
   ```
2. Double-click `setup_demo.bat` to install lightweight dependencies and automatically create a desktop shortcut.

### 3. Launch
- Double-click the **Raphael Demo** shortcut on your Desktop, or run:
  ```powershell
  .\run_demo.bat
  ```

---

## 💬 Things to Try

- *"What is my CPU and RAM usage?"*
- *"Search the web for the latest discoveries by the James Webb Space Telescope."*
- *"Who was Alan Turing? Look it up on Wikipedia."*
- *"Show demo files"*
- *"Write a note in my demo sandbox called ideas.txt"*

---

## 📄 License
Personal & Educational Demo — All rights reserved.
