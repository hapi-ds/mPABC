import asyncio
import logging
import sqlite3
from nicegui import ui
from business_coach.db.repository import (
    BusinessIdeaRepository,
    CanvasElementRepository,
    VoicePersonaRepository,
    PlanSectionRepository,
)
from business_coach.agents.workflow import generate_plan_section
from business_coach.gui.editable_field import EditableField

logger = logging.getLogger(__name__)

PLAN_SECTIONS = [
    "Executive Summary",
    "Company Description",
    "Market Analysis",
    "Organization & Management",
    "Service or Product Line",
    "Marketing & Sales",
    "Funding Request",
    "Financial Projections",
    "Appendix",
]


def create_plan_panel(
    container: ui.column,
    topic_id: int,
    conn: sqlite3.Connection,
    idea_repo: BusinessIdeaRepository,
    canvas_repo: CanvasElementRepository,
    voices_repo: VoicePersonaRepository,
    plan_repo: PlanSectionRepository,
    header_spinner=None,
    header_status_label=None,
) -> None:
    container.clear()

    with container:
        fresh_voices_repo = VoicePersonaRepository(conn)

        ui.label("Step 4: Business Plan").classes("text-h5 font-bold q-mb-md")
        ui.label("Generate the final business plan sections using context from your idea, canvas, and voices.").classes(
            "text-body1 q-mb-md"
        )

        idea_data = idea_repo.get_by_topic(topic_id)
        idea_text = idea_data["primary_description"] if idea_data else ""

        canvas_elements = canvas_repo.get_by_topic(topic_id)

        if not idea_text or not canvas_elements:
            with ui.card().classes("w-full bg-yellow-50 border-l-4 border-yellow-500"):
                ui.icon("warning", size="md").classes("text-yellow-600")
                ui.label("Please complete the Idea and Canvas steps first.").classes("text-body1 text-grey-8 q-mt-sm")
                with ui.row().classes("q-mt-sm"):
                    ui.markdown("[Go to Canvas Panel →](#canvas)").classes("text-primary text-sm")
            return

        canvas_text = "\n".join([f"{e.element_name}:\n{e.content}" for e in canvas_elements])

        personas = fresh_voices_repo.get_by_topic(topic_id)
        if not personas:
            with ui.card().classes("w-full bg-yellow-50 border-l-4 border-yellow-500"):
                ui.icon("warning", size="md").classes("text-yellow-600")
                ui.label("Please generate Custom Voices first.").classes("text-body1 text-grey-8 q-mt-sm")
                with ui.row().classes("q-mt-sm"):
                    ui.markdown("[Go to Voices Panel →](#voices)").classes("text-primary text-sm")
            return

        personas_text = "\n".join([f"{p.name}: {p.description} ({p.communication_style})" for p in personas])

        # Store component references so run_all can update them
        section_fields = {}

        async def run_all_sections():
            if header_spinner and header_status_label:
                header_spinner.set_visibility(True)
                header_status_label.set_text("Generating all business plan sections...")

            try:
                for idx, section_name in enumerate(PLAN_SECTIONS):
                    result = await asyncio.to_thread(
                        generate_plan_section,
                        business_idea=idea_text,
                        business_canvas_text=canvas_text,
                        personas_text=personas_text,
                        section_name=section_name,
                        previous_content="",
                        user_feedback="",
                    )

                    # Update the UI component if it exists and is not frozen
                    if section_name in section_fields:
                        field = section_fields[section_name]
                        if not field.is_frozen:
                            plan_repo.upsert(topic_id, section_name, result, "")
                            field.value = result

                    # Show progress
                    progress = f"{idx + 1}/{len(PLAN_SECTIONS)}"
                    if header_status_label:
                        header_status_label.set_text(f"Generated: {progress}")

                ui.notify(f"Generated all {len(PLAN_SECTIONS)} sections!", type="positive")
            except Exception as e:
                ui.notify(f"Failed to run all: {e}", type="negative")
            finally:
                if header_spinner and header_status_label:
                    header_spinner.set_visibility(False)
                    header_status_label.set_text("")

        with ui.row().classes("w-full q-mb-md"):
            ui.button("Run All Sections", on_click=run_all_sections).props("color=accent icon=play_strength")

        for section_name in PLAN_SECTIONS:
            with ui.card().classes("w-full q-mb-md"):
                ui.label(section_name).classes("text-h6 font-bold")

                existing = plan_repo.get_section(topic_id, section_name)
                content = existing.content if existing else ""
                feedback = existing.user_feedback if existing and existing.user_feedback else ""

                field_container = ui.column().classes("w-full")

                spinner = ui.spinner(size="sm").classes("q-ml-sm")
                spinner.set_visibility(False)

                # Create the field first (no callbacks yet)
                ef = EditableField(
                    value=content,
                    label=section_name,
                    is_frozen=False,
                    show_feedback=True,
                    rows=6,
                )
                ef.feedback_value = feedback

                # Wire callbacks, capturing ef via default arg
                def make_redo_callback(f=ef, sec_name=section_name, spin=spinner):
                    async def on_redo(content_val: str, feedback_val: str):
                        spin.set_visibility(True)
                        try:
                            result = await asyncio.to_thread(
                                generate_plan_section,
                                business_idea=idea_text,
                                business_canvas_text=canvas_text,
                                personas_text=personas_text,
                                section_name=sec_name,
                                previous_content=content_val,
                                user_feedback=feedback_val,
                            )
                            f.value = result
                            plan_repo.upsert(topic_id, sec_name, result, feedback_val)
                            ui.notify(f"{sec_name} updated.", type="positive")
                        except Exception as e:
                            ui.notify(f"Failed to generate {sec_name}: {e}", type="negative")
                        finally:
                            spin.set_visibility(False)

                    return on_redo

                def make_save_callback(f=ef, sec_name=section_name):
                    def on_save(content_val: str):
                        try:
                            plan_repo.upsert(topic_id, sec_name, content_val, f.feedback_value, f.is_frozen)
                        except Exception as e:
                            logger.exception(f"Failed to save content for {sec_name}: {e}")

                    return on_save

                def make_freeze_callback(f=ef, sec_name=section_name):
                    def on_freeze(is_frozen: bool):
                        try:
                            plan_repo.upsert(topic_id, sec_name, f.value, f.feedback_value, is_frozen)
                        except Exception as e:
                            logger.exception(f"Failed to save freeze state for {sec_name}: {e}")

                    return on_freeze

                ef.on_save = make_save_callback()
                ef.on_freeze = make_freeze_callback()
                ef.on_redo = make_redo_callback()
                ef.render(field_container)

                # Store field reference for run_all
                section_fields[section_name] = ef
