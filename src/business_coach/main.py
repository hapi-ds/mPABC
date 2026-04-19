"""mPABS - Main entry point.

Initializes application settings, logging, database, 
and launches the NiceGUI web interface.
"""

from __future__ import annotations

import logging
import urllib.request
import urllib.error

from nicegui import ui

from business_coach.config import AppSettings
from business_coach.db.repository import TopicRepository
from business_coach.db.schema import get_connection
from business_coach.dspy_modules.modules import configure_dspy
from business_coach.gui.layout import create_layout
from business_coach.logging_config import setup_logging

logger = logging.getLogger(__name__)


def check_lm_studio_connectivity(base_url: str, timeout: float = 5.0) -> bool:
    """Check whether LM Studio is reachable at the configured base URL."""
    url = f"{base_url.rstrip('/')}/models"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def main() -> None:
    """Start the mPABS Business Coach System."""

    settings = AppSettings()
    setup_logging(settings)
    logger.info("mPABS Business Coach starting")

    configure_dspy(settings)
    logger.info("DSPy configured with LM Studio at %s", settings.lm_studio_base_url)

    from business_coach.rag.engine import RAGEngine
    rag_engine = RAGEngine(settings)

    conn = get_connection(settings.database_path)
    topic_repo = TopicRepository(conn)

    lm_studio_reachable = check_lm_studio_connectivity(settings.lm_studio_base_url)
    if not lm_studio_reachable:
        logger.error("LM Studio is unreachable at %s", settings.lm_studio_base_url)

    @ui.page("/")
    def index() -> None:
        if not lm_studio_reachable:
            with ui.card().classes("bg-negative text-white w-full q-pa-sm q-mb-sm"):
                ui.label(
                    "⚠ LM Studio is unreachable. "
                    "AI generation is disabled until the LLM backend is available."
                )

        create_layout(topic_repo, conn, rag_engine=rag_engine, settings=settings)

    logger.info("Launching NiceGUI web interface")
    ui.run(
        title="mPABS - Business Coach",
        port=settings.nicegui_port,
        reload=settings.nicegui_reload,
        uvicorn_reload_excludes=".*, .py[cod], .sw.*, ~*, logs/*, data/*, *.log, *.db",
    )


def cli() -> None:
    import subprocess
    import sys

    raise SystemExit(
        subprocess.call([sys.executable, "-m", "business_coach.main"])
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
