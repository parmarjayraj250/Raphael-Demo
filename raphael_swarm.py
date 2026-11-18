import time, threading, psutil
from concurrent.futures import ThreadPoolExecutor, as_completed

class RaphaelSwarm:
    """
    Dynamic Resource-Bounded Multi-Agent Swarm with Cross-Checking Consensus:
    - Scales 2-4 concurrent agents based on live RAM pressure
    - Cooperative cancellation via safety_manager.is_aborted()
    - Researcher + Architect + Security Critic + Cross-Checking Executive
    """
    def __init__(self, safety_manager, ai_chat_func):
        self.safety_manager = safety_manager
        self.ai_chat_func   = ai_chat_func

    def _get_optimal_concurrency(self) -> int:
        """Dynamically calculates max concurrent sub-agents based on available RAM."""
        try:
            mem = psutil.virtual_memory()
            if mem.percent > 85 or mem.available < 2.5 * (1024 ** 3):
                return 2  # Throttled under high memory pressure
            elif mem.percent > 70:
                return 3
            return 4      # Optimal concurrency
        except Exception:
            return 2

    def run_swarm(self, task: str) -> str:
        """Executes the multi-agent parallel swarm with cross-checking executive synthesis."""
        if self.safety_manager.is_aborted():
            return "🛑 Swarm execution canceled by Emergency Stop."

        max_workers = self._get_optimal_concurrency()
        self.safety_manager.log_audit("SWARM", f"START: {task[:50]}", "INFO", True, f"Workers: {max_workers}")

        subagent_outputs = {}

        def _researcher_task():
            if self.safety_manager.is_aborted():
                return None
            prompt = (
                f"You are the RESEARCHER AGENT in a multi-agent swarm.\n"
                f"Investigate the technical foundation, key requirements, algorithms, and state-of-the-art methods for:\n"
                f"'{task}'\n"
                f"Provide concise, factual technical bullet points and reference principles."
            )
            try:
                out = self.ai_chat_func(prompt, task_type="research", save_history=False)
            except TypeError:
                out = self.ai_chat_func(prompt, task_type="research")
            return ("researcher", out)

        def _architect_task():
            if self.safety_manager.is_aborted():
                return None
            prompt = (
                f"You are the SOFTWARE ARCHITECT AGENT in a multi-agent swarm.\n"
                f"Design the structural components, data flow, interface signatures, and implementation architecture for:\n"
                f"'{task}'\n"
                f"Provide clean modular specifications and step-by-step technical blueprints."
            )
            try:
                out = self.ai_chat_func(prompt, task_type="coding", save_history=False)
            except TypeError:
                out = self.ai_chat_func(prompt, task_type="coding")
            return ("architect", out)

        def _critic_task():
            if self.safety_manager.is_aborted():
                return None
            prompt = (
                f"You are the SECURITY & QA CRITIC AGENT in a multi-agent swarm.\n"
                f"Audit potential edge cases, vulnerabilities, race conditions, memory leaks, and failure modes for:\n"
                f"'{task}'\n"
                f"List critical risks and specific defensive safeguards needed."
            )
            try:
                out = self.ai_chat_func(prompt, task_type="coding", save_history=False)
            except TypeError:
                out = self.ai_chat_func(prompt, task_type="coding")
            return ("critic", out)

        tasks = [_researcher_task, _architect_task, _critic_task]

        # Concurrently execute sub-agents with dynamic resource bounding
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_agent = {executor.submit(fn): fn for fn in tasks}
            for future in as_completed(future_to_agent):
                if self.safety_manager.is_aborted():
                    return "🛑 Swarm execution canceled immediately by Emergency Stop."
                try:
                    res = future.result(timeout=120.0)
                    if res:
                        role, content = res
                        subagent_outputs[role] = content
                except Exception as e:
                    self.safety_manager.log_audit("SWARM_WORKER", "ERROR", "WARN", False, str(e))

        if self.safety_manager.is_aborted():
            return "🛑 Swarm execution halted by Emergency Stop."

        # Executive Agent Cross-Checking Synthesis
        executive_prompt = (
            f"You are the RAPHAEL EXECUTIVE AGENT.\n"
            f"Synthesize the findings of your specialized sub-agents on the task: '{task}'.\n\n"
            f"--- RESEARCHER FINDINGS ---\n{subagent_outputs.get('researcher', 'N/A')}\n\n"
            f"--- ARCHITECT BLUEPRINT ---\n{subagent_outputs.get('architect', 'N/A')}\n\n"
            f"--- SECURITY CRITIC RISKS ---\n{subagent_outputs.get('critic', 'N/A')}\n\n"
            f"Instructions:\n"
            f"1. Identify any key disagreements or conflicts between the Architect and the Security Critic.\n"
            f"2. Resolve the conflicts with defensive engineering.\n"
            f"3. Provide the unified, finalized master solution."
        )

        try:
            final_report = self.ai_chat_func(executive_prompt, task_type="research", save_history=False)
        except TypeError:
            final_report = self.ai_chat_func(executive_prompt, task_type="research")
        self.safety_manager.log_audit("SWARM", f"COMPLETE: {task[:50]}", "INFO", True, "Consensus reached")
        return f"👥 RAPHAEL MULTI-AGENT SWARM CONSENSUS:\n\n{final_report}"