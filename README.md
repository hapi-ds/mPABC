# mPABC — my Personal Artificial Business Coach

<p align="center">
  <a href="https://github.com/hapi-ds/mPABC/releases">
    <img src="https://img.shields.io/github/v/release/hapi-ds/mPABC?style=flat-square&color=blue" alt="Latest Release">
  </a>
  <img src="https://img.shields.io/badge/python-3.13-blue?style=flat-square&logo=python&logoColor=white" alt="Python Version">
  <a href="https://github.com/hapi-ds/mPABC/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/hapi-ds/mPABC?style=flat-square" alt="License">
  </a>
</p>

<p align="center">
  <a href="https://github.com/hapi-ds/mPABC/actions">
    <img src="https://github.com/hapi-ds/mPABC/actions/workflows/ci.yml/badge.svg" alt="CI Pipeline Status">
  </a>
</p>

It all started with **mPAPA** ([github.com/hapi-ds/mPAPA](https://github.com/hapi-ds/mPAPA)), a project where I discovered how surprisingly well local LLMs could perform, even with smaller models. The key was to **break down complex tasks into granular, manageable steps and delegate them to specialized agents**.

Funnily enough, this is a principle I’ve known for years from project management: ***a successful project relies on refined tasks, solvable and understood by the executor**. In truly agile projects, the "Ready" state is crucial—a task is only ready to be implemented when its complexity has been reduced to a clear, actionable level. This approach is rooted in **problem-solving competence** rather than pure "specialism". By applying this to AI—ensuring every prompt is "Ready" for the model—even small local LLMs can deliver professional-grade business results.

This modular success inspired me to develop a whole series of these "mPAx" tools. Since my next challenge involved drafting business plans, **mPABC** was born.

## Features

- **Business Idea Capture** — Describe your idea and run granular market research with AI-scored web search results
- **Business Model Canvas** — AI-generated canvas elements (Key Partners, Value Propositions, Customer Segments, etc.) with edit/freeze/redo workflow
- **Custom Voice Personas** — Generate target audience personas based on your canvas
- **Business Plan Generation** — Full business plan with standard sections (Executive Summary through Appendix), generated from your idea, canvas, and personas
- **AI Personality Modes** — Choose Creative, Balanced, or Strict to control how imaginative or evidence-based the AI responses are
- **Multi-format Export** — Export to DOCX, PDF, or LaTeX (.tex) with optional BibTeX bibliography from web search results
- **AI Chat Assistant** — Context-aware chat panel alongside the canvas editor
- **Local-first** — All data stays in a local SQLite database; LLM inference runs through your own LM Studio instance

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager)
- [LM Studio](https://lmstudio.ai/) running locally with a loaded model

## Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/mPABC.git
cd mPABC

# Install dependencies
uv sync

# Copy and configure environment
cp .env.example .env
# Edit .env to match your LM Studio setup

# Start LM Studio and load a model

# Run the application
uv run python -m business_coach.main
```

The web interface opens at `http://localhost:8080` by default.

## Configuration

All settings use the `BC_` environment variable prefix and are loaded from `.env`. Copy `.env.example` to `.env` and adjust as needed.

| Variable | Default | Description |
|----------|---------|-------------|
| `BC_LM_STUDIO_BASE_URL` | `http://localhost:1234/v1` | LM Studio API endpoint |
| `BC_LM_STUDIO_API_KEY` | `not-needed` | API key (LM Studio doesn't require one) |
| `BC_MODEL_CANVAS` | `default` | Model for Business Model Canvas generation |
| `BC_MODEL_VOICES` | `default` | Model for voice persona generation |
| `BC_MODEL_PLAN` | `default` | Model for business plan section generation |
| `BC_MODEL_RESEARCH` | `default` | Model for search section generation and result scoring |
| `BC_MODEL_CHAT` | `default` | Model for AI chat assistant |
| `BC_EMBEDDING_MODEL_NAME` | `text-embedding-nomic-embed-text-v1.5` | Embedding model for RAG |
| `BC_DEFAULT_MAX_TOKENS` | `8192` | Max tokens for AI responses |
| `BC_DATABASE_PATH` | `data/business_coach.db` | SQLite database path |
| `BC_LOG_FILE_PATH` | `logs/business_coach.log` | Log file path |
| `BC_LOG_LEVEL` | `INFO` | Log level (DEBUG, INFO, WARNING, ERROR) |
| `BC_NICEGUI_PORT` | `8080` | Web server port |
| `BC_NICEGUI_RELOAD` | `false` | Auto-reload on file changes (dev mode) |
| `BC_DOCX_TEMPLATE_DIR` | `src/business_coach/export/templates` | DOCX template directory |
| `BC_DOCX_TEMPLATE_NAME` | `template.docx` | DOCX template filename |
| `BC_MONITORING_INTERVAL_HOURS` | `24` | Background search interval |
| `BC_SEARCH_MAX_RESULTS_PER_SOURCE` | `10` | Max results per search source |
| `BC_SEARCH_REQUEST_DELAY_SECONDS` | `3.0` | Rate limiting delay between requests |
| `BC_SEARCH_RELEVANCE_TOP_K` | `200` | Max documents to score for relevance |

## Workflow

1. **Idea & Search** — Enter your business idea, generate research categories, and run web searches
2. **Canvas & Chat** — Generate and refine Business Model Canvas elements with AI assistance
3. **Custom Voices** — Generate target audience personas from your canvas
4. **Business Plan** — Generate a full business plan using all prior context
5. **Settings** — Export to DOCX/PDF/LaTeX, configure AI personality mode

Each field supports an Edit/Save toggle, a Freeze switch to lock finalized content, and a Redo button that incorporates your feedback into regeneration.

## Export Formats

- **DOCX** — Microsoft Word format via python-docx
- **PDF** — Professional PDF with markdown rendering via WeasyPrint
- **LaTeX (.tex)** — LaTeX source files compilable with `pdflatex`/`texmake`, with optional BibTeX bibliography generated from web search results

## Development

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest --tb=short -q

# Run with auto-reload for development
BC_NICEGUI_RELOAD=true uv run python -m business_coach.main
```

## Project Structure

```
src/business_coach/
├── agents/          # DSPy workflow orchestration
├── db/              # SQLite schema, models, repositories
├── dspy_modules/    # DSPy Signatures and configuration
├── export/          # DOCX, PDF, and LaTeX exporters
├── gui/             # NiceGUI panels and components
├── monitoring/      # Background search scheduler
├── parsers/         # Web search (DuckDuckGo)
├── rag/             # RAG engine and embeddings
├── config.py        # Pydantic Settings (BC_ prefix)
├── exceptions.py    # Custom exception hierarchy
├── logging_config.py # Structured logging setup
└── main.py          # Application entry point
```

## License

See [LICENSE](LICENSE).

---

*Built by [koehler](https://koehler.eu.com). Open source. Local first. Always.*
