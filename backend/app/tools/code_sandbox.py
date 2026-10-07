"""Safe local code execution tool.

The first implementation is intentionally disabled unless explicitly enabled.
It runs subprocesses in a temporary directory with a timeout and bounded output.
A production deployment should replace this backend with a container/microVM
sandbox before enabling it for untrusted users.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from app.models.tool import ToolResult, ToolSpec


class CodeSandboxTool:
    spec = ToolSpec(
        name="code.sandbox",
        description="Execute a short program in an isolated temporary workspace.",
        capabilities=("code_execution",),
        requires_confirmation=True,
    )

    async def execute(self, arguments: dict) -> ToolResult:
        language = str(arguments.get("language", "python")).lower()
        code = str(arguments.get("code", ""))
        timeout = min(max(int(arguments.get("timeout_seconds", 5)), 1), 10)

        if not code.strip():
            return ToolResult(self.spec.name, None, False, "No code supplied")
        if language not in {"python"}:
            return ToolResult(self.spec.name, None, False, "Only Python is supported by the safe development backend")

        with tempfile.TemporaryDirectory(prefix="nova-sandbox-") as directory:
            root = Path(directory)
            script = root / "main.py"
            script.write_text(code, encoding="utf-8")

            env = {
                "PATH": os.environ.get("PATH", ""),
                "PYTHONUNBUFFERED": "1",
            }
            process = await asyncio.create_subprocess_exec(
                "python",
                str(script),
                cwd=directory,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return ToolResult(self.spec.name, None, False, "Execution timed out")

        output = stdout.decode("utf-8", errors="replace")[-12000:]
        error = stderr.decode("utf-8", errors="replace")[-12000:]
        if process.returncode != 0:
            return ToolResult(self.spec.name, {"stdout": output, "stderr": error, "exit_code": process.returncode}, False, "Program exited with an error")
        return ToolResult(self.spec.name, {"stdout": output, "stderr": error, "exit_code": 0}, True)
