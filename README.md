# NOVA AI

NOVA AI is an AI orchestration platform designed to go beyond a simple chatbot or provider aggregator.

## Current status

**v0.1.0 — Foundation**

The repository contains the initial FastAPI backend foundation. Next layers are model adapters, intelligent routing, agent orchestration, tools, memory/RAG, and the UI.

## Architecture

- **API:** FastAPI
- **Orchestrator:** planning, model selection, tools, verification
- **Models:** provider adapters + local models
- **Knowledge:** database + vector retrieval + object storage
- **Tools:** web, code execution, files, Git, MCP-compatible integrations
- **Clients:** web first, then Android/desktop

## Development

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://127.0.0.1:8000/docs.

### Android / physical phone development

Run the API on `0.0.0.0:8000` so a phone can reach it over the same Wi-Fi network. In NOVA's **Connection** panel, use your computer's LAN address, for example `http://192.168.1.20:8000`. The Android client permits development HTTP traffic so Android's cleartext policy does not block local/LAN testing. For production, deploy the API behind HTTPS.

## Roadmap

1. Backend foundation
2. Provider/model abstraction
3. Intelligent model router
4. Agent orchestrator
5. Tool system and safe execution
6. Memory + RAG
7. Chat UI
8. Authentication, persistence, observability
9. Evaluation and reliability
10. Android/desktop clients
