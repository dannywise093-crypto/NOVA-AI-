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

Run the API on `0.0.0.0:8000` for local development. The NOVA app keeps the API address internal; users do not enter an IP address. For production, deploy the API behind HTTPS.

### Google and X sign-in

NOVA supports real OAuth 2.0 + PKCE sign-in for Google and X. The app opens the provider login, the provider returns to the NOVA API, and the API sends a one-time code back to the Android app using the `nova://auth/callback` deep link. Google recommends authorization-code based flows for secure sign-in, and X supports OAuth 2.0 PKCE for user authentication. 

Set these backend environment variables before enabling the buttons:

```env
OAUTH_PUBLIC_BASE_URL=https://api.example.com
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
X_OAUTH_CLIENT_ID=...
X_OAUTH_CLIENT_SECRET=...
AUTH_SECRET=...
```

Register these callback URLs with the providers:

- `https://api.example.com/api/auth/google/callback`
- `https://api.example.com/api/auth/x/callback`

For Google, create Android/Web OAuth credentials and use the backend web client for the authorization-code exchange. For X, enable OAuth 2.0 PKCE and configure the callback URL in the X developer console. Production OAuth should use HTTPS.

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
