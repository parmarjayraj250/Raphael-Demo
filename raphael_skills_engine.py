import os, sys, json, time, ast, subprocess, re, shutil, tempfile, importlib.util
from datetime import datetime

SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raphael_skills")

class SkillSecurityViolation(Exception):
    pass

class RaphaelSkillSynthesizer:
    """
    Self-Evolving Skill Engine with Defense-in-Depth:
    1. AST Static Security Filter
    2. Subprocess Sandbox with sanitized clean environment and process tracking
    3. Versioned Local Registry (skill.py, manifest.json, versions/)
    4. Mandatory Human Approval Gate
    5. Dynamic LLM Execution Context (ai_chat hook in args)
    6. Intelligent Natural Auto-Routing (match_skill)
    7. Continuous Improvement & Rollback Support (improve_skill, rollback_skill)
    """
    def __init__(self, safety_manager, ai_chat_func):
        self.safety_manager = safety_manager
        self.ai_chat_func   = ai_chat_func
        self._registry      = {}
        os.makedirs(SKILLS_DIR, exist_ok=True)
        self._load_installed_skills()

    def _load_installed_skills(self):
        """Loads all previously approved and installed skills from disk into memory."""
        self._registry.clear()
        if not os.path.exists(SKILLS_DIR):
            return
        for item in os.listdir(SKILLS_DIR):
            item_dir = os.path.join(SKILLS_DIR, item)
            skill_file = os.path.join(item_dir, "skill.py")
            manifest_file = os.path.join(item_dir, "manifest.json")
            if os.path.isdir(item_dir) and os.path.exists(skill_file):
                try:
                    spec = importlib.util.spec_from_file_location(f"raphael_skill_{item}", skill_file)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    manifest = {}
                    if os.path.exists(manifest_file):
                        with open(manifest_file, "r", encoding="utf-8") as mf:
                            manifest = json.load(mf)
                    self._registry[item] = {
                        "module": mod,
                        "manifest": manifest,
                        "dir": item_dir
                    }
                except Exception as e:
                    self.safety_manager.log_audit("SKILL_LOAD", item, "ERROR", False, str(e))

    def ast_security_filter(self, code_str: str) -> bool:
        """
        AST Static Security Filter: Inspects code structure for dangerous primitives.
        Raises SkillSecurityViolation if unsafe nodes/calls are detected.
        """
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            raise SkillSecurityViolation(f"Syntax error in code: {e}")

        forbidden_calls = {
            "eval", "exec", "__import__", "compile", "breakpoint",
            "rmdir", "remove", "unlink", "rmtree"
        }
        forbidden_modules = {
            "subprocess", "socket", "http.server", "ctypes", "winreg",
            "shutil"
        }

        for node in ast.walk(tree):
            # Check for forbidden imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split('.')[0]
                    if root_mod in forbidden_modules:
                        raise SkillSecurityViolation(f"Forbidden module import: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_mod = node.module.split('.')[0]
                    if root_mod in forbidden_modules:
                        raise SkillSecurityViolation(f"Forbidden from-import: {node.module}")

            # Check for direct calls
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in forbidden_calls:
                    raise SkillSecurityViolation(f"Forbidden function call: {node.func.id}")
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in forbidden_calls:
                        raise SkillSecurityViolation(f"Forbidden attribute call: {node.func.attr}")
                    if node.func.attr in ["system", "popen", "spawn"]:
                        raise SkillSecurityViolation(f"Forbidden OS execution: {node.func.attr}")

        return True

    def run_sandbox_test(self, code_str: str, test_arg: str = "") -> tuple[bool, str]:
        """
        Executes generated code in an isolated subprocess with a sanitized environment.
        Never passes Raphael's secret environment variables or tokens.
        """
        test_script = (
            code_str + "\n\n"
            "if __name__ == '__main__':\n"
            "    import json\n"
            "    def _mock_ai(prompt):\n"
            "        return f'[Simulated AI response for: {str(prompt)[:50]}]'\n"
            f"    res = execute({{ 'query': '{test_arg}', 'input': '{test_arg}', 'text': '{test_arg}', 'principal': 1000, 'rate': 0.05, 'time': 2, 'n': 1, 'ai_chat': _mock_ai }})\n"
            "    print('__OUTPUT__:' + str(res))\n"
        )
        # Quarantine sandbox directory (isolated from workspace/repo)
        sandbox_dir = os.path.join(tempfile.gettempdir(), "raphael_skill_sandbox")
        os.makedirs(sandbox_dir, exist_ok=True)

        # Minimal clean environment (Only essential system paths, blocked user site packages & safe path)
        clean_env = {
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", r"C:\Windows"),
            "PATH": os.environ.get("PATH", ""),
            "TEMP": sandbox_dir,
            "TMP": sandbox_dir,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONSAFEPATH": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1"
        }

        proc = subprocess.Popen(
            [sys.executable, "-c", test_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=sandbox_dir,
            env=clean_env
        )
        self.safety_manager.register_subprocess(proc)

        try:
            stdout, stderr = proc.communicate(timeout=12.0)
            if proc.returncode == 0:
                out = stdout.strip()
                if "__OUTPUT__:" in out:
                    out = out.split("__OUTPUT__:")[-1].strip()
                # Detect caught-exception strings returned as output (false-positive pass)
                _error_markers = (
                    "error occurred", "traceback", "valueerror", "typeerror",
                    "nameerror", "exception", "nonetype", "must be a string",
                    "argument must be"
                )
                if any(marker in out.lower() for marker in _error_markers):
                    return False, f"Sandbox output indicates a runtime error: {out}"
                return True, out
            else:
                return False, stderr.strip() or stdout.strip()
        except subprocess.TimeoutExpired:
            proc.kill()
            return False, "Sandbox execution timed out after 12 seconds."
        except Exception as e:
            return False, f"Sandbox execution error: {e}"
        finally:
            self.safety_manager.unregister_subprocess(proc)

    def _extract_code_from_ai(self, raw_code: str) -> str:
        """Extracts clean python code from AI response blocks."""
        m = re.search(r"```(?:python)?\s*(.*?)\s*```", raw_code, re.DOTALL)
        if m:
            return m.group(1).strip()
        m = re.search(r"`python\s*(.*?)\s*`", raw_code, re.DOTALL)
        if m:
            return m.group(1).strip()
        lines = raw_code.splitlines()
        code_lines = []
        capturing = False
        for line in lines:
            if line.strip().startswith(("def ", "import ", "from ", "class ")):
                capturing = True
            if capturing:
                code_lines.append(line)
        return "\n".join(code_lines).strip() if code_lines else raw_code.strip()

    def synthesize_skill(self, skill_name: str, task_description: str) -> dict:
        """
        Full Synthesis Pipeline:
        1. AI Code generation
        2. AST security filtering
        3. Sandboxed test run
        4. Returns proposal ready for human approval
        """
        safe_name = re.sub(r'[^\w-]', '_', skill_name.strip().lower())
        prompt = (
            f"Write a self-contained, robust Python module for a skill named '{safe_name}'.\n"
            f"Task: {task_description}\n\n"
            "Requirements:\n"
            "1. Must define an entrypoint function: def execute(args: dict) -> str:\n"
            "2. Input 'args' is a dictionary: args.get('query') or args.get('input') holds the user's input string.\n"
            "3. DYNAMIC LOGIC — NEVER HARDCODE STATIC ANSWERS:\n"
            "   - If the task is computational/mathematical (e.g. conversions, math formulas, data parsing), extract numbers or arguments from query dynamically and compute the real result.\n"
            "   - If the task is educational, explanatory, or creative (e.g. Feynman technique teacher, analogy generator, summarizer), use the dynamic AI hook provided in args: `ai_chat = args.get('ai_chat')`. If ai_chat is available, construct an expert prompt and return `ai_chat(prompt)`. If not available, provide a dynamic breakdown based on the topic query.\n"
            "4. Return a clean, formatted string result. Do NOT prepend words like 'python' to the text.\n"
            "5. Do NOT use dangerous system calls, file deletions, eval, exec, or sockets.\n"
            "6. Return ONLY valid, executable Python code inside a single ```python ... ``` block."
        )

        try:
            raw_code = self.ai_chat_func(prompt, task_type="coding", save_history=False)
        except TypeError:
            raw_code = self.ai_chat_func(prompt, task_type="coding")

        code = self._extract_code_from_ai(raw_code)

        # Step 1: AST Filter
        try:
            self.ast_security_filter(code)
            self.safety_manager.log_audit("SKILL_AST", safe_name, "SAFE", True, "AST security filter passed.")
        except SkillSecurityViolation as e:
            self.safety_manager.log_audit("SKILL_AST", safe_name, "BLOCKED", False, str(e))
            return {"status": "error", "error": f"Security Violation: {e}", "code": code}

        # Step 2: Sandbox test
        test_ok, test_out = self.run_sandbox_test(code, test_arg="10")
        if not test_ok:
            self.safety_manager.log_audit("SKILL_SANDBOX", safe_name, "FAILED", False, test_out)
            return {"status": "error", "error": f"Sandbox Test Failed: {test_out}", "code": code}

        self.safety_manager.log_audit("SKILL_SANDBOX", safe_name, "PASSED", True, f"Output: {test_out[:80]}")
        return {
            "status": "ready_for_approval",
            "skill_name": safe_name,
            "task": task_description,
            "code": code,
            "test_output": test_out
        }

    def improve_skill(self, skill_name: str, feedback: str) -> dict:
        """
        Improves an existing installed skill based on user feedback and existing code.
        Generates upgraded code, verifies via AST and sandbox, and prepares for approval.
        """
        safe_name = re.sub(r'[^\w-]', '_', skill_name.strip().lower())
        if safe_name not in self._registry:
            return {"status": "error", "error": f"Skill '{safe_name}' is not installed."}

        skill_dir = os.path.join(SKILLS_DIR, safe_name)
        active_file = os.path.join(skill_dir, "skill.py")
        current_code = ""
        if os.path.exists(active_file):
            with open(active_file, "r", encoding="utf-8") as f:
                current_code = f.read()

        manifest = self._registry[safe_name].get("manifest", {})
        cur_v = manifest.get("current_version", 1)

        prompt = (
            f"You are IMPROVING an existing Python skill named '{safe_name}' (currently v{cur_v}).\n\n"
            f"Existing Code:\n```python\n{current_code}\n```\n\n"
            f"User Feedback / Required Improvement:\n{feedback}\n\n"
            "Requirements:\n"
            "1. Must define: def execute(args: dict) -> str:\n"
            "2. Input 'args' dictionary has args.get('query') or args.get('input').\n"
            "3. If the skill explains concepts or generates dynamic intelligence, utilize: `ai_chat = args.get('ai_chat')`.\n"
            "4. NEVER hardcode static answers. Process user input dynamically.\n"
            "5. Apply the feedback cleanly while preserving security rules (no eval, exec, sockets, subprocess).\n"
            "6. Output ONLY the updated executable Python code inside a ```python ... ``` block."
        )

        try:
            raw_code = self.ai_chat_func(prompt, task_type="coding", save_history=False)
        except TypeError:
            raw_code = self.ai_chat_func(prompt, task_type="coding")

        code = self._extract_code_from_ai(raw_code)

        # AST Filter
        try:
            self.ast_security_filter(code)
            self.safety_manager.log_audit("SKILL_AST", safe_name, "SAFE", True, f"AST filter passed for v{cur_v + 1}")
        except SkillSecurityViolation as e:
            self.safety_manager.log_audit("SKILL_AST", safe_name, "BLOCKED", False, str(e))
            return {"status": "error", "error": f"Security Violation: {e}", "code": code}

        # Sandbox Test
        test_ok, test_out = self.run_sandbox_test(code, test_arg="10")
        if not test_ok:
            self.safety_manager.log_audit("SKILL_SANDBOX", safe_name, "FAILED", False, test_out)
            return {"status": "error", "error": f"Sandbox Test Failed: {test_out}", "code": code}

        return {
            "status": "ready_for_approval",
            "skill_name": safe_name,
            "task": f"Improvement: {feedback}",
            "code": code,
            "test_output": test_out,
            "is_upgrade": True,
            "next_version": cur_v + 1
        }

    def install_approved_skill(self, skill_name: str, task_description: str, code_str: str) -> str:
        """
        MANDATORY HUMAN APPROVAL GATE:
        Called only after user explicitly confirms installation in the GUI.
        Maintains versioned history (versions/v{N}.py) and manifest.json.
        """
        safe_name = re.sub(r'[^\w-]', '_', skill_name.strip().lower())
        skill_dir = os.path.join(SKILLS_DIR, safe_name)
        versions_dir = os.path.join(skill_dir, "versions")
        os.makedirs(versions_dir, exist_ok=True)

        manifest_file = os.path.join(skill_dir, "manifest.json")
        version = 1
        if os.path.exists(manifest_file):
            try:
                with open(manifest_file, "r", encoding="utf-8") as mf:
                    data = json.load(mf)
                    version = data.get("current_version", 1) + 1
            except Exception:
                version = 1

        # Save snapshot into versions
        v_file = os.path.join(versions_dir, f"v{version}.py")
        with open(v_file, "w", encoding="utf-8") as vf:
            vf.write(code_str)

        # Save active skill.py
        active_file = os.path.join(skill_dir, "skill.py")
        with open(active_file, "w", encoding="utf-8") as af:
            af.write(code_str)

        # Update manifest
        manifest_data = {
            "skill_name": safe_name,
            "description": task_description,
            "current_version": version,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with open(manifest_file, "w", encoding="utf-8") as mf:
            json.dump(manifest_data, mf, indent=2)

        self._load_installed_skills()
        self.safety_manager.log_audit("SKILL_INSTALL", safe_name, "INFO", True, f"Installed v{version}")
        return f"[OK] Skill '{safe_name}' v{version} successfully verified and installed."

    def rollback_skill(self, skill_name: str) -> str:
        """Rolls back a skill to its previous version."""
        safe_name = re.sub(r'[^\w-]', '_', skill_name.strip().lower())
        skill_dir = os.path.join(SKILLS_DIR, safe_name)
        manifest_file = os.path.join(skill_dir, "manifest.json")
        versions_dir = os.path.join(skill_dir, "versions")

        if not os.path.exists(manifest_file):
            return f"Skill '{safe_name}' not found."

        with open(manifest_file, "r", encoding="utf-8") as mf:
            data = json.load(mf)

        cur_v = data.get("current_version", 1)
        if cur_v <= 1:
            return f"Skill '{safe_name}' is currently at v1. No previous version to rollback to."

        target_v = cur_v - 1
        target_file = os.path.join(versions_dir, f"v{target_v}.py")
        if not os.path.exists(target_file):
            return f"Version v{target_v} not found."

        shutil.copy(target_file, os.path.join(skill_dir, "skill.py"))
        data["current_version"] = target_v
        data["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(manifest_file, "w", encoding="utf-8") as mf:
            json.dump(data, mf, indent=2)

        self._load_installed_skills()
        self.safety_manager.log_audit("SKILL_ROLLBACK", safe_name, "INFO", True, f"Rolled back to v{target_v}")
        return f"[OK] Skill '{safe_name}' rolled back from v{cur_v} to v{target_v}."

    def execute_skill(self, skill_name: str, query: str = "") -> str:
        """Executes an installed approved skill with rich context (query + dynamic ai_chat)."""
        safe_name = re.sub(r'[^\w-]', '_', skill_name.strip().lower())
        if safe_name not in self._registry:
            return f"Skill '{safe_name}' is not installed. Use 'evolve skill {safe_name}' to synthesize it."
        mod = self._registry[safe_name]["module"]
        if not hasattr(mod, "execute"):
            return f"Skill '{safe_name}' does not have an execute() entrypoint."
        try:
            ctx = {
                "query": query,
                "input": query,
                "text": query
            }
            if hasattr(self, "ai_chat_func") and self.ai_chat_func:
                ctx["ai_chat"] = lambda prompt: self.ai_chat_func(prompt, task_type="general", save_history=False)

            res = mod.execute(ctx)
            return str(res)
        except Exception as e:
            return f"Skill execution error ({safe_name}): {e}"

    def match_skill(self, text: str) -> tuple[str, str] | None:
        """
        Intelligently detects if user query matches any registered evolved skill.
        Returns (skill_name, cleaned_query) or None.
        """
        if not self._registry or not text:
            return None
        t = text.strip().lower()

        # Check explicit command bypass
        if t.startswith(("evolve", "swarm", "operate", "search", "help", "system status")):
            return None

        # Sort registered skills by name length descending
        for name, item in sorted(self._registry.items(), key=lambda x: len(x[0]), reverse=True):
            spaced_name = name.replace("_", " ")

            # 1. Exact or spaced name in query
            if spaced_name in t:
                idx = t.find(spaced_name)
                rem = (t[:idx] + " " + t[idx + len(spaced_name):]).strip()
                rem = re.sub(r"^(?:using|with|via|in|on|explain|calculate|run|solve)\s+", "", rem, flags=re.IGNORECASE).strip()
                return (name, rem or text)

            if name in t:
                idx = t.find(name)
                rem = (t[:idx] + " " + t[idx + len(name):]).strip()
                return (name, rem or text)

            # 2. Check distinctive tokens from skill name (e.g. 'feynman', 'celsius', 'emi')
            tokens = [k for k in name.split("_") if len(k) >= 4 and k not in {"skill", "engine", "tool", "helper", "make", "create", "using"}]
            for token in tokens:
                pattern = rf"\b{re.escape(token)}\b"
                if re.search(pattern, t):
                    # Matched distinctive skill keyword
                    return (name, text)

        return None

    def list_skills(self) -> str:
        if not self._registry:
            return "No persistent skills currently registered in raphael_skills/."
        out = f"Registered Evolved Skills ({len(self._registry)} total):\n"
        for name, item in self._registry.items():
            manifest = item.get("manifest", {})
            v = manifest.get("current_version", 1)
            desc = manifest.get("description", "Custom AI tool")
            out += f"  ● {name} (v{v}) — {desc[:60]}\n"
        return out.strip()
