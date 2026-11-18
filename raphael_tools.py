import os, sys, re, json, time, shutil, subprocess
from typing import Callable, Any, Dict, List, Optional
from datetime import datetime

class ToolDefinition:
    """Represents a registered capability with metadata, permission tier, and validation schema."""
    def __init__(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
        schema: Optional[Dict[str, Any]] = None,
        risk_level: str = "SAFE",
        requires_approval: bool = False,
        permission: str = "system"
    ):
        self.name = name.lower()
        self.description = description
        self.handler = handler
        self.schema = schema or {"type": "object", "properties": {}}
        self.risk_level = risk_level.upper()
        self.requires_approval = requires_approval
        self.permission = permission

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.schema,
            "risk_level": self.risk_level,
            "requires_approval": self.requires_approval,
            "permission": self.permission
        }


class RaphaelToolRegistry:
    """
    Centralized, schema-backed Tool Registry for Raphael.
    Enforces permissions, safety classification, audit logging, and human approval gates.
    """
    def __init__(self, safety_manager, alert_callback: Optional[Callable[[str], None]] = None):
        self.safety_manager = safety_manager
        self.alert_callback = alert_callback or (lambda text: print(f"[Tool Alert] {text}"))
        self._tools: Dict[str, ToolDefinition] = {}
        self._pending_approvals: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        name: str,
        description: str,
        handler: Callable[..., Any],
        schema: Optional[Dict[str, Any]] = None,
        risk_level: str = "SAFE",
        requires_approval: bool = False,
        permission: str = "system"
    ) -> ToolDefinition:
        """Registers a new tool into the registry."""
        tool = ToolDefinition(
            name=name,
            description=description,
            handler=handler,
            schema=schema,
            risk_level=risk_level,
            requires_approval=requires_approval,
            permission=permission
        )
        self._tools[tool.name] = tool
        return tool

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name.lower())

    def list_tools(self) -> List[Dict[str, Any]]:
        return [tool.to_dict() for tool in self._tools.values()]

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Returns tool schemas formatted for LLM function calling."""
        schemas = []
        for tool in self._tools.values():
            schemas.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.schema
                }
            })
        return schemas

    def execute(self, tool_name: str, kwargs: Optional[Dict[str, Any]] = None, approved: bool = False) -> Any:
        """
        Executes a registered tool through the mandatory safety and audit pipeline:
        1. Checks tool existence
        2. Checks emergency stop abort state
        3. Enforces approval gate if high risk / destructive
        4. Logs structured audit record
        5. Executes handler and catches runtime exceptions
        """
        kwargs = kwargs or {}
        tool = self.get_tool(tool_name)
        if not tool:
            return f"Error: Tool '{tool_name}' is not registered."

        # 1. Emergency Stop Check
        if self.safety_manager and self.safety_manager.is_aborted():
            return "🛑 Execution blocked: Emergency stop is active. Say 'reset emergency stop' to proceed."

        # 2. Risk Evaluation
        inferred_risk = self.safety_manager.classify_risk(f"{tool_name} {json.dumps(kwargs)}") if self.safety_manager else tool.risk_level
        effective_risk = "HIGH_RISK" if (inferred_risk == "HIGH_RISK" or tool.risk_level in ["HIGH_RISK", "CRITICAL"]) else "SAFE"

        # 3. Approval Gate
        if (tool.requires_approval or effective_risk == "HIGH_RISK") and not approved:
            token = f"appr_{int(time.time()*1000)}"
            self._pending_approvals[token] = {
                "tool_name": tool_name,
                "kwargs": kwargs,
                "created_at": time.time()
            }
            if self.safety_manager:
                self.safety_manager.log_audit("TOOL_GATE", tool_name, effective_risk, False, f"Awaiting user approval for params: {kwargs}")

            return (
                f"⚠ APPROVAL REQUIRED for '{tool_name}'.\n"
                f"Action details: {kwargs}\n"
                f"Risk classification: {effective_risk}\n"
                f"To confirm and run, say or type: 'confirm action {token}' (or 'cancel action')."
            )

        # 4. Audit Log
        if self.safety_manager:
            self.safety_manager.log_audit("TOOL_EXEC", tool_name, effective_risk, True, f"Executing with params: {kwargs}")

        # 5. Handler Execution
        try:
            result = tool.handler(**kwargs)
            return result
        except TypeError as te:
            # Fallback if handler takes no arguments
            try:
                return tool.handler()
            except Exception as e:
                return f"Error executing tool '{tool_name}': {e}"
        except Exception as e:
            return f"Error executing tool '{tool_name}': {e}"

    def approve_action(self, token: str) -> Any:
        """Approves and executes a pending action."""
        token = token.strip()
        if token not in self._pending_approvals:
            return f"Invalid or expired approval token: '{token}'."
        pending = self._pending_approvals.pop(token)
        return self.execute(pending["tool_name"], pending["kwargs"], approved=True)

    def cancel_action(self, token: Optional[str] = None) -> str:
        """Cancels a pending action."""
        if token and token in self._pending_approvals:
            del self._pending_approvals[token]
            return f"Action '{token}' has been cancelled."
        count = len(self._pending_approvals)
        self._pending_approvals.clear()
        return f"All pending actions ({count}) cancelled."
