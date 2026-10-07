from dataclasses import dataclass\n\n_APPROVALS: dict[str, str] = {}
import hashlib
import json
import secrets


@dataclass(frozen=True)
class ToolPermission:
    allow_network: bool = False
    allow_filesystem: bool = False
    allow_code_execution: bool = False
    require_confirmation: bool = True


class PermissionPolicy:
    def __init__(self, permission: ToolPermission | None = None) -> None:
        self.permission = permission or ToolPermission()
        # Process-wide one-time approvals let a separate API approval request\n        # authorize the later executor instance created for the same request.\n        self._approvals = _APPROVALS

    def allowed(self, capability: str) -> bool:
        mapping = {
            "network": self.permission.allow_network,
            "filesystem": self.permission.allow_filesystem,
            "code_execution": self.permission.allow_code_execution,
        }
        return mapping.get(capability, True)

    @staticmethod
    def approval_key(tool_name: str, arguments: dict) -> str:
        payload = json.dumps(arguments, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(f"{tool_name}:{payload}".encode()).hexdigest()

    def request_approval(self, tool_name: str, arguments: dict) -> str:
        key = self.approval_key(tool_name, arguments)
        token = secrets.token_urlsafe(24)
        self._approvals[key] = token
        return token

    def approve(self, tool_name: str, arguments: dict, token: str) -> bool:
        key = self.approval_key(tool_name, arguments)
        if self._approvals.get(key) != token:
            return False
        del self._approvals[key]
        return True
