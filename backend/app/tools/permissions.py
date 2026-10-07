from dataclasses import dataclass


@dataclass(frozen=True)
class ToolPermission:
    allow_network: bool = False
    allow_filesystem: bool = False
    allow_code_execution: bool = False
    require_confirmation: bool = True


class PermissionPolicy:
    def __init__(self, permission: ToolPermission | None = None) -> None:
        self.permission = permission or ToolPermission()

    def allowed(self, capability: str) -> bool:
        mapping = {
            "network": self.permission.allow_network,
            "filesystem": self.permission.allow_filesystem,
            "code_execution": self.permission.allow_code_execution,
        }
        return mapping.get(capability, True)
