# GraphMind

> **AI-Powered Code Dependency & Architecture Visualizer**
>
> Transform any codebase into an interactive, queryable knowledge graph. Understand architecture, trace dependencies, find dead code, and chat with your codebase — all in one workbench.

<p align="center">
  <img src="https://img.shields.io/badge/Phase-1%20Foundation-blue?style=for-the-badge" alt="Phase 1">
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react" alt="React 18">
  <img src="https://img.shields.io/badge/FastAPI-0.110-009688?style=for-the-badge&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Redis-7-FF4438?style=for-the-badge&logo=redis" alt="Redis">
  <img src="https://img.shields.io/badge/Qdrant-Vector_DB-EA4A2F?style=for-the-badge" alt="Qdrant">
  <img src="https://img.shields.io/badge/Celery-Distributed-37814A?style=for-the-badge&logo=celery" alt="Celery">
  <img src="https://img.shields.io/badge/Tree--sitter-AST_Parsing-000000?style=for-the-badge" alt="Tree-sitter">
</p>

---

## The Problem

Developers waste hours understanding unfamiliar codebases. Existing tools produce static, unreadable dependency graphs with zero AI reasoning. They can't answer:

- *"What breaks if I delete UserService?"*
- *"How does auth flow from route to database?"*
- *"Where is payment logic scattered across this 80,000-line repo?"*
- *"Is there dead code slowing down my build?"*

## The Solution

GraphMind fuses **static AST analysis**, **graph traversal**, **vector search**, and **LLM reasoning** into a single interactive workbench — visual and conversational at once.

| Feature | Traditional Tools | GraphMind |
|---------|-------------------|-----------|
| Dependency Graph | Static image | Interactive, filterable, real-time |
| Architecture View | Manual diagrams | Auto-detected layers + violations |
| Code Search | Text grep | Semantic vector search + graph context |
| Questions | Manual reading | RAG-powered chat with code citations |
| Impact Analysis | Guesswork | Graph traversal with risk scoring |
| Dead Code | Heuristics only | Reachability from entry points + AI |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GRAPHMIND ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │
│  │   Frontend   │◄──►│   Backend    │◄──►│   Workers    │◄──►│  Queue   │  │
│  │  (React 18)  │    │  (FastAPI)   │    │  (Celery)    │    │ (Redis)  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └──────────┘  │
│         │                    │                    │                         │
│         ▼                    ▼                    ▼                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                  │
│  │ React Flow   │    │ PostgreSQL   │    │ Tree-sitter  │                  │
│  │ Graph Canvas │    │ (Supabase)   │    │ AST Parsers  │                  │
│  └──────────────┘    └──────────────┘    └──────────────┘                  │
│                           │                    │                             │
│                           ▼                    ▼                             │
│                    ┌──────────────┐    ┌──────────────┐                    │
│                    │   Qdrant     │    │  Anthropic   │                    │
│                    │ Vector Search│    │   Claude API │                    │
│                    └──────────────┘    └──────────────┘                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Frontend
- **React 18** + TypeScript + Vite
- **TailwindCSS v3** + shadcn/ui (custom design system)
- **React Flow v11** (heavily customized graph canvas)
- **Framer Motion** (animations)
- **D3.js** (sequence/layer diagrams)
- **Monaco Editor** (inline code preview)
- **Zustand** + **TanStack Query** (state management)
- **Socket.io-client** (real-time updates)

### Backend
- **FastAPI** (Python 3.11+)
- **SQLAlchemy 2.0** + **Alembic** (async ORM + migrations)
- **PostgreSQL** (Supabase free tier)
- **Redis** (Upstash free tier) — job queue, caching, rate limiting
- **Celery** (background workers for parsing/analysis/embeddings)
- **Tree-sitter** (multi-language AST parsing)
- **NetworkX** (graph algorithms)
- **FastEmbed** (local embeddings: all-MiniLM-L6-v2)
- **Qdrant** (vector search — Qdrant Cloud free tier)
- **Socket.io** (real-time progress events)

### AI Layer
- **Anthropic Claude** (primary reasoning — claude-sonnet-4-6)
- **Google Gemini 1.5 Pro** (fallback / cost optimization)
- **FastEmbed** for local embedding generation

### Infrastructure (Free Tier Ready)
| Service | Provider | Free Tier |
|---------|----------|-----------|
| Frontend | Vercel | 100GB bandwidth |
| Backend | Render | 750 hrs/month |
| Workers | Render | 750 hrs/month |
| PostgreSQL | Supabase | 500MB |
| Vector DB | Qdrant Cloud | 1GB |
| Redis | Upstash | 10K commands/day |
| Auth | Supabase Auth | Unlimited |
| Storage | Supabase Storage | 1GB |

---

## Phase Roadmap

| Phase | Name | Status | Deliverable |
|-------|------|--------|-------------|
| 1 | **Foundation & Import** | 🚧 In Progress | Auth, GitHub/ZIP import, progress UI, landing page |
| 2 | **AST Parsing Engine** | ⏳ Pending | Multi-language symbol/relationship extraction |
| 3 | **Graph Engine & Viz** | ⏳ Pending | Interactive React Flow canvas + architecture views |
| 4 | **Vector Embeddings + AI Chat** | ⏳ Pending | RAG-powered codebase Q&A with streaming |
| 5 | **Impact Analysis + Dead Code** | ⏳ Pending | Risk intelligence + actionable reports |
| 6 | **Summary + Refactoring** | ⏳ Pending | AI architecture summary + refactoring assistant |
| 7 | **Polish & Export** | ⏳ Pending | Performance, PDF export, keyboard nav, error states |

---

## Quick Start (Local Development)

### Prerequisites
- Docker + Docker Compose
- Node.js 20+ (for frontend dev)
- Python 3.11+ (for backend dev)

### 1. Clone & Configure
```bash
git clone https://github.com/yourusername/graphmind.git
cd graphmind

# Copy environment template
cp graphmind-backend/.env.example graphmind-backend/.env
# Edit .env with your keys (see Environment Variables below)
```

### 2. Start Infrastructure
```bash
docker-compose up -d postgres redis qdrant
```

### 3. Run Backend
```bash
cd graphmind-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 4. Run Frontend
```bash
cd graphmind-frontend
npm install
npm run dev
```

### 5. Run Workers (separate terminals)
```bash
# Terminal 1: Celery worker
cd graphmind-backend && source .venv/bin/activate
celery -A app.workers.celery_app worker --loglevel=info

# Terminal 2: Celery beat (scheduler)
celery -A app.workers.celery_app beat --loglevel=info
```

### 6. Open App
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- GraphQL Playground: http://localhost:8000/graphql (if enabled)

---

## Environment Variables

### Backend (`graphmind-backend/.env`)
```bash
# Database
DATABASE_URL=postgresql+asyncpg://graphmind:graphmind@localhost:5432/graphmind

# Redis
REDIS_URL=redis://localhost:6379/0

# Qdrant
QDRANT_URL=http://localhost:6333

# Auth
SECRET_KEY=your-super-secret-key-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# GitHub OAuth (create at github.com/settings/developers)
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GITHUB_REDIRECT_URI=http://localhost:8000/auth/github/callback

# Frontend URL (CORS)
FRONTEND_URL=http://localhost:5173

# AI Providers (at least one required)
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...

# Supabase (for storage + auth)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
SUPABASE_BUCKET=graphmind-repos

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Rate Limiting
RATE_LIMIT_IMPORTS_PER_DAY=10
RATE_LIMIT_CHAT_PER_DAY=100
```

---

## Project Structure

```
graphmind/
├── graphmind-backend/
│   ├── app/
│   │   ├── config.py              # Pydantic Settings
│   │   ├── database.py            # Async SQLAlchemy engine
│   │   ├── main.py                # FastAPI app entry
│   │   ├── models/                # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── repository.py
│   │   │   ├── file.py
│   │   │   ├── symbol.py
│   │   │   ├── relationship.py
│   │   │   ├── analysis_report.py
│   │   │   └── chat_message.py
│   │   ├── schemas/               # Pydantic request/response
│   │   ├── routers/               # API endpoints
│   │   ├── services/              # Business logic
│   │   ├── workers/               # Celery tasks
│   │   ├── parsers/               # Tree-sitter parsers
│   │   └── utils/                 # Helpers
│   ├── alembic/                   # DB migrations
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── graphmind-frontend/
│   ├── src/
│   │   ├── pages/                 # Route components
│   │   ├── components/
│   │   │   ├── layout/            # AppShell, Sidebar, TopBar
│   │   │   ├── ui/                # shadcn/ui components
│   │   │   ├── repository/        # Import, Progress, Cards
│   │   │   ├── graph/             # React Flow nodes/edges
│   │   │   └── chat/              # Chat panel components
│   │   ├── stores/                # Zustand state
│   │   ├── hooks/                 # Custom React hooks
│   │   ├── lib/                   # API client, query client
│   │   └── types/                 # TypeScript types
│   ├── tailwind.config.ts         # Design system tokens
│   ├── vite.config.ts
│   └── package.json
│
├── docker-compose.yml
└── README.md
```

---

## API Endpoints (Planned)

### Authentication
```
POST   /api/v1/auth/register           # Email/password register
POST   /api/v1/auth/login              # Email/password login
POST   /api/v1/auth/refresh            # Refresh access token
POST   /api/v1/auth/logout             # Logout (blacklist refresh)
GET    /api/v1/auth/github             # Initiate GitHub OAuth
GET    /api/v1/auth/github/callback    # GitHub OAuth callback
GET    /api/v1/auth/me                 # Current user profile
```

### Repositories
```
POST   /api/v1/repositories/import/github    # Import from GitHub
POST   /api/v1/repositories/import/zip       # Import from ZIP upload
GET    /api/v1/repositories                  # List user repositories
GET    /api/v1/repositories/{id}             # Get repository details
DELETE /api/v1/repositories/{id}             # Delete repository
GET    /api/v1/repositories/{id}/status      # Real-time analysis status
```

### Graph & Analysis
```
GET    /api/v1/repositories/{id}/graph              # Full dependency graph
GET    /api/v1/repositories/{id}/graph/node/{sid}   # Node + neighbors
GET    /api/v1/repositories/{id}/graph/path         # Shortest path between nodes
GET    /api/v1/repositories/{id}/graph/impact/{sid} # Impact analysis
GET    /api/v1/repositories/{id}/graph/cycles       # Circular dependencies
GET    /api/v1/repositories/{id}/graph/layers       # Architecture layer view
GET    /api/v1/repositories/{id}/sequence           # Sequence diagram for route
GET    /api/v1/repositories/{id}/dead-code          # Dead code report
GET    /api/v1/repositories/{id}/summary            # AI repository summary
GET    /api/v1/repositories/{id}/refactoring        # Refactoring recommendations
```

### Chat (RAG)
```
POST   /api/v1/repositories/{id}/chat         # Stream chat response
GET    /api/v1/repositories/{id}/chat/history # Conversation history
DELETE /api/v1/repositories/{id}/chat/history # Clear history
```

### Export
```
GET    /api/v1/repositories/{id}/export/pdf     # Full PDF report
GET    /api/v1/repositories/{id}/export/graph   # Graph as SVG
GET    /api/v1/repositories/{id}/export/report  # Markdown summary
```

---

## Design System

### Colors (Dark Intelligence)
```css
--bg-void:        #080B14   /* Canvas */
--bg-surface:     #0E1220   /* Cards, panels */
--bg-elevated:    #151C2E   /* Hover, active */
--border-subtle:  #1E2A42   /* Dividers */
--accent-primary: #3B82F6   /* Electric blue — nodes, CTAs */
--accent-graph:   #8B5CF6   /* Violet — edges, relationships */
--accent-success: #10B981   /* Emerald — healthy states */
--accent-danger:  #EF4444   /* Red — risk, impact, dead code */
--accent-warn:    #F59E0B   /* Amber — warnings, circular deps */
--text-primary:   #F1F5F9   /* Main text */
--text-secondary: #94A3B8   /* Labels, metadata */
--text-muted:     #475569   /* Placeholders, disabled */
```

### Typography
- **Display/Code:** `JetBrains Mono` (module names, code labels, node titles)
- **Body:** `Inter` (prose, descriptions, chat)
- **Data:** `JetBrains Mono` at small sizes (counts, scores, paths)

### Motion Principles
- Graph nodes: spring-animated, staggered, physics-based
- Panel transitions: 200ms ease-out slide
- Skeleton loaders with subtle shimmer (no spinners)
- Edge glow on hover, ripple on click
- Full `prefers-reduced-motion` support

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'feat: add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Commit Convention
```
feat:     New feature
fix:      Bug fix
docs:     Documentation only
style:    Formatting, missing semicolons, etc.
refactor: Code change that neither fixes a bug nor adds a feature
test:     Adding missing tests
chore:    Maintenance
```

### Code Quality
```bash
# Backend
cd graphmind-backend
ruff check .          # Lint
ruff format .         # Format
mypy app/             # Type check
pytest                # Tests

# Frontend
cd graphmind-frontend
npm run lint          # ESLint
npm run format        # Prettier
npm run typecheck     # tsc --noEmit
npm run test          # Vitest
```

---

## Deployment (Free Tier)

### 1. Supabase
- Create project → SQL Editor → Run migrations
- Enable Auth → GitHub OAuth provider
- Create storage bucket `graphmind-repos`
- Get: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`

### 2. Qdrant Cloud
- Create free cluster (1GB)
- Get: `QDRANT_URL`, `QDRANT_API_KEY`

### 3. Upstash Redis
- Create free database (10K commands/day)
- Get: `REDIS_URL` (REST URL + token)

### 4. Render (Backend + Worker)
- **Web Service**: Connect GitHub repo → `graphmind-backend`
  - Build: `pip install -r requirements.txt`
  - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
  - Env vars: All from `.env`
- **Background Worker**: Same repo
  - Start: `celery -A app.workers.celery_app worker --loglevel=info`

### 5. Vercel (Frontend)
- Import `graphmind-frontend` folder
- Framework: Vite
- Env: `VITE_API_URL=https://your-backend.onrender.com`
- Build: `npm run build`

### 6. GitHub OAuth App
- Settings → Developer settings → OAuth Apps
- Callback: `https://your-backend.onrender.com/auth/github/callback`
- Add `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` to Render

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [Tree-sitter](https://tree-sitter.github.io/) — Incremental parsing
- [React Flow](https://reactflow.dev/) — Graph visualization
- [FastEmbed](https://github.com/qdrant/fastembed) — Local embeddings
- [Qdrant](https://qdrant.tech/) — Vector similarity search
- [shadcn/ui](https://ui.shadcn.com/) — Beautiful accessible components
- [Anthropic](https://www.anthropic.com/) — Claude API

---

<p align="center">
  <strong>Built with ❤️ for developers who want to understand code, not just read it.</strong>
</p>

<p align="center">
  <a href="https://github.com/yourusername/graphmind/issues">Report Bug</a>
  •
  <a href="https://github.com/yourusername/graphmind/issues">Request Feature</a>
  •
  <a href="https://github.com/yourusername/graphmind/discussions">Discussions</a>
</p>