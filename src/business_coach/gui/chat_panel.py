"""AI Chat panel UI for mPABS."""

import asyncio
import logging
from typing import Any
import dspy
from nicegui import ui

from business_coach.db.repository import ChatHistoryRepository, BusinessIdeaRepository

logger = logging.getLogger(__name__)


def build_chat_prompt(question: str, invention_context: dict | None = None) -> str:
    parts: list[str] = []
    if invention_context is not None:
        desc = invention_context.get("primary_description", "")
        if desc:
            parts.append(f"Business Idea:\n{desc}\n")
    parts.append(f"Question: {question}")
    # Added instruction to prompt for hard facts
    parts.append(
        "\nPlease provide a detailed response, and where applicable, include 'hard facts' such as cost estimations, market size, or other quantifiable data."
    )
    return "\n".join(parts)


def _render_message(role: str, text: str) -> None:
    if role == "user":
        with ui.row().classes("w-full justify-end"):
            ui.chat_message(text=text, name="You", sent=True).classes("bg-blue-100")
    else:
        with ui.row().classes("w-full justify-start"):
            ui.chat_message(text=text, name="Assistant", sent=False).classes("bg-grey-200 text-lg")


def create_chat_panel(
    container: Any,
    topic_id: int,
    chat_repo: ChatHistoryRepository,
    *,
    rag_engine: Any | None = None,
    settings: Any | None = None,
    idea_repo: BusinessIdeaRepository | None = None,
) -> None:
    container.clear()
    invention_context: dict | None = None
    if idea_repo is not None:
        try:
            idea = idea_repo.get_by_topic(topic_id)
            if idea is not None:
                invention_context = {
                    "primary_description": idea["primary_description"],
                }
        except Exception:
            logger.exception("Failed to load idea for chat context, topic %d", topic_id)

        with container:
            ui.label("AI Chat").classes("text-h6 q-mb-sm")
            scroll_area = ui.scroll_area().classes("w-full border rounded-lg p-2").style("height: 700px;")

            chat_messages_container = None
            with scroll_area:
                chat_messages_container = ui.column().classes("w-full gap-2")

        existing = chat_repo.get_by_topic(topic_id)
        with chat_messages_container:
            for msg in existing:
                _render_message(msg.role, msg.message)

        with ui.row().classes("w-full items-end gap-2 q-mt-sm"):
            message_input = ui.textarea(label="Type a message…").classes("flex-grow").props("rows=3")

            async def _on_send() -> None:
                text = message_input.value.strip() if message_input.value else ""
                if not text:
                    return

                chat_repo.save_message(topic_id, "user", text)
                with chat_messages_container:
                    _render_message("user", text)

                message_input.value = ""
                await ui.context.client.connected()

                prompt = build_chat_prompt(text, invention_context=invention_context)
                try:
                    lm = dspy.settings.lm
                    if lm is None:
                        raise ConnectionError("DSPy LM is not configured")
                    response = await asyncio.to_thread(lm, prompt)

                    if isinstance(response, list) and response:
                        item = response[0]
                        assistant_text = item.get("text", "") if isinstance(item, dict) else str(item)
                    else:
                        assistant_text = str(response)
                except Exception as exc:
                    logger.error(f"LLM Error: {exc}")
                    error_msg = "⚠️ The LLM backend is currently unavailable."
                    with chat_messages_container:
                        _render_message("assistant", error_msg)
                    scroll_area.scroll_to(percent=1.0)
                    return

                chat_repo.save_message(topic_id, "assistant", assistant_text)
                with chat_messages_container:
                    _render_message("assistant", assistant_text)
                scroll_area.scroll_to(percent=1.0)

            ui.button("Send", on_click=_on_send).props("color=primary")

            def _on_clear_chat() -> None:
                chat_repo.delete_by_topic(topic_id)
                chat_messages_container.clear()
                ui.notify("Chat history cleared.", type="info")

            ui.button("Clear Chat", on_click=_on_clear_chat, icon="delete_sweep").props("flat color=negative size=sm")
