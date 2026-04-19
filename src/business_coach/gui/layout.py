"""Main layout for the mPABS Business Coach GUI."""

from __future__ import annotations

import logging
import sqlite3
from typing import TYPE_CHECKING

from nicegui import ui

from business_coach.config import AppSettings
from business_coach.db.repository import (
    TopicRepository,
    BusinessIdeaRepository,
    CanvasElementRepository,
    VoicePersonaRepository,
    PlanSectionRepository,
    ChatHistoryRepository
)
# We will import the panel creation functions
from business_coach.gui.idea_panel import create_idea_panel
from business_coach.gui.canvas_panel import create_canvas_panel
from business_coach.gui.voices_panel import create_voices_panel
from business_coach.gui.plan_panel import create_plan_panel
from business_coach.gui.settings_panel import create_settings_panel

logger = logging.getLogger(__name__)


def create_layout(
    topic_repo: TopicRepository,
    conn: sqlite3.Connection,
    *,
    rag_engine=None,
    settings: AppSettings | None = None,
) -> None:
    state: dict = {
        "selected_topic_id": None,
    }

    with ui.header().classes("items-center q-pa-none").style("flex-direction: column; align-items: stretch;"):
        with ui.row().classes("w-full items-center justify-between q-px-md").style("min-height: 48px;"):
            ui.label("mPABS - Business Coach").classes("text-h6 font-bold text-white")

            with ui.tabs().classes("text-white") as tabs:
                idea_tab = ui.tab("Idea & Search")
                canvas_tab = ui.tab("Canvas & Chat")
                voices_tab = ui.tab("Custom Voices")
                plan_tab = ui.tab("Business Plan")
                settings_tab = ui.tab("Settings")

        with ui.row().classes("w-full q-px-md items-center justify-center").style("background: rgba(0,0,0,0.25); min-height: 24px;"):
            header_spinner = ui.spinner("dots", size="xs", color="white")
            header_spinner.set_visibility(False)
            header_status_label = ui.label("").classes("text-caption text-grey-4")

    with ui.left_drawer(value=True).classes("p-4") as drawer:
        ui.label("Topics").classes("text-h6 q-mb-sm")
        topic_list_container = ui.column().classes("w-full gap-1")

        def _refresh_topic_list() -> None:
            topic_list_container.clear()
            topics = topic_repo.get_all()
            with topic_list_container:
                if not topics:
                    ui.label("No topics yet.").classes("text-grey")
                for topic in topics:
                    btn = ui.button(
                        topic.name,
                        on_click=lambda _, tid=topic.id: _select_topic(tid),
                    ).classes("w-full justify-start")
                    if topic.id == state["selected_topic_id"]:
                        btn.props("color=primary")
                    else:
                        btn.props("flat color=dark")

        def _select_topic(topic_id: int) -> None:
            state["selected_topic_id"] = topic_id
            _refresh_topic_list()
            _on_topic_selected(topic_id)

        async def _open_new_topic_dialog() -> None:
            with ui.dialog() as dialog, ui.card().classes("min-w-[300px]"):
                ui.label("New Topic").classes("text-h6")
                name_input = ui.input(label="Topic name").classes("w-full")
                dialog_error = ui.label("").classes("text-negative text-caption")
                dialog_error.set_visibility(False)

                def _create_topic() -> None:
                    name = name_input.value.strip()
                    if not name:
                        return
                    if topic_repo.name_exists(name):
                        dialog_error.set_text(f'Topic "{name}" already exists.')
                        dialog_error.set_visibility(True)
                        return
                    new_topic = topic_repo.create(name)
                    dialog.close()
                    _select_topic(new_topic.id)

                with ui.row().classes("w-full justify-end gap-2 q-mt-sm"):
                    ui.button("Cancel", on_click=dialog.close).props("flat")
                    ui.button("Create", on_click=_create_topic).props("color=primary")

            dialog.open()

        ui.button("New Topic", on_click=_open_new_topic_dialog, icon="add").classes("w-full q-mt-md")

    with ui.tab_panels(tabs, value=idea_tab).classes("w-full flex-grow") as panels:
        with ui.tab_panel(idea_tab):
            idea_container = ui.column().classes("w-full p-4")
            if state["selected_topic_id"] is None:
                with idea_container: ui.label("Select a topic")

        with ui.tab_panel(canvas_tab):
            canvas_container = ui.column().classes("w-full p-4")
            if state["selected_topic_id"] is None:
                with canvas_container: ui.label("Select a topic")

        with ui.tab_panel(voices_tab):
            voices_container = ui.column().classes("w-full p-4")
            if state["selected_topic_id"] is None:
                with voices_container: ui.label("Select a topic")

        with ui.tab_panel(plan_tab):
            plan_container = ui.column().classes("w-full p-4")
            if state["selected_topic_id"] is None:
                with plan_container: ui.label("Select a topic")

        with ui.tab_panel(settings_tab):
            settings_container = ui.column().classes("w-full p-4")
            # Always show settings, even if no topic is selected


    def _on_topic_selected(topic_id: int) -> None:
        topic = topic_repo.get_by_id(topic_id)
        if topic is None: return

        idea_repo = BusinessIdeaRepository(conn)
        canvas_rel_repo = CanvasElementRepository(conn)
        voices_repo = VoicePersonaRepository(conn)
        plan_repo = PlanSectionRepository(conn)
        chat_repo = ChatHistoryRepository(conn)

        # Clear ONLY the topic-dependent containers to remove old content/labels
        idea_container.clear()
        canvas_container.clear()
        voices_container.clear()
        plan_container.clear()

        create_idea_panel(
            idea_container, topic_id, conn=conn,
            idea_repo=idea_repo,
            rag_engine=rag_engine,
            settings=settings,
            header_status_label=header_status_label, header_spinner=header_spinner
        )
        create_canvas_panel(
            canvas_container, topic_id, conn=conn,
            idea_repo=idea_repo, canvas_rel_repo=canvas_rel_repo, chat_repo=chat_repo
        )
        create_voices_panel(
            voices_container, topic_id, conn=conn,
            canvas_repo=canvas_rel_repo, voices_repo=voices_repo
        )
        create_plan_panel(
            plan_container, topic_id, conn=conn,
            idea_repo=idea_repo, canvas_repo=canvas_rel_repo,
            voices_repo=voices_repo, plan_repo=plan_repo,
            header_spinner=header_spinner, header_status_label=header_status_label
        )
        # Settings is persistent; we do not clear or recreate it here.
        try:
            create_settings_panel(
                settings_container, topic_id, conn=conn,
                settings=settings or AppSettings()
            )
        except Exception as e:
            logger.error(f"Failed to create settings panel: {e}", exc_info=True)
            with settings_container: ui.label(f"Error loading settings panel: {e}").classes("text-negative")

    _refresh_topic_list()
