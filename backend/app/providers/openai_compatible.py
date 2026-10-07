import json
from collections.abc import AsyncIterator
import httpx

from app.models.base import ModelInfo
from app.models.tool import ToolCall
from app.models.types import ModelRequest, ModelResponse
from app.providers.base import ModelProvider

class OpenAICompatibleProvider(ModelProvider):
    def __init__(self, base_url: str, api_key: str, model: str, provider_name: str = "openai-compatible") -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = model
        self.provider_name = provider_name

    def list_models(self) -> list[ModelInfo]:
        return [ModelInfo(id=self.default_model, provider=self.provider_name,
            capabilities=("chat", "reasoning", "coding"), context_window=32768,
            supports_tools=True, supports_vision=True, supports_streaming=True)]

    def _payload(self, model: str, request: ModelRequest, stream: bool = False) -> dict:
        messages = []
        for m in request.messages:
            item = {"role": m.role, "content": m.content}
            if m.tool_call_id:
                item["tool_call_id"] = m.tool_call_id
            if m.tool_calls:
                item["tool_calls"] = [{"id": c.id or c.name, "type": "function",
                    "function": {"name": c.name, "arguments": json.dumps(c.arguments)}} for c in m.tool_calls]
            messages.append(item)
        payload = {"model": model, "messages": messages, "temperature": request.temperature}
        if request.max_tokens is not None: payload["max_tokens"] = request.max_tokens
        if request.tools: payload["tools"] = list(request.tools)
        if stream: payload["stream"] = True
        return payload

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def chat(self, model: str, request: ModelRequest) -> ModelResponse:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=self._headers(), json=self._payload(model, request))
            response.raise_for_status()
            data = response.json()
        choice = data["choices"][0]
        message = choice["message"]
        calls = []
        for call in message.get("tool_calls") or []:
            fn = call.get("function", {})
            try: args = json.loads(fn.get("arguments", "{}"))
            except json.JSONDecodeError: args = {}
            calls.append(ToolCall(name=fn.get("name", ""), arguments=args, id=call.get("id")))
        usage = data.get("usage") or {}
        return ModelResponse(content=message.get("content") or "", model=data.get("model", model),
            provider=self.provider_name, usage={k: int(v) for k,v in usage.items() if isinstance(v,(int,float))},
            finish_reason=choice.get("finish_reason"), tool_calls=tuple(calls))

    async def stream(self, model: str, request: ModelRequest) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=90.0) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions", headers=self._headers(), json=self._payload(model, request, True)) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"): continue
                    payload = line[5:].strip()
                    if payload == "[DONE]": break
                    try: data = json.loads(payload)
                    except json.JSONDecodeError: continue
                    for choice in data.get("choices", []):
                        delta = choice.get("delta", {}).get("content")
                        if delta: yield delta
