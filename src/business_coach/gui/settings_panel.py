import logging
import sqlite3
from pathlib import Path
from nicegui import ui
from business_coach.config import AppSettings
from business_coach.db.repository import (
    TopicRepository,
    CanvasElementRepository,
    VoicePersonaRepository,
    PlanSectionRepository,
    PersonalityPreferenceRepository,
    ResearchSessionRepository,
    WebSearchRepository,
    SpecialistOverrideRepository,
)
from business_coach.agents.specialists import SPECIALIST_REGISTRY, get_specialist
from business_coach.export.docx_exporter import DOCXExporter
from business_coach.export.latex_exporter import (
    export_canvas_latex,
    export_voices_latex,
    export_plan_latex,
)
from business_coach.export.pdf_exporter import (
    WEASYPRINT_AVAILABLE,
    export_canvas_pdf,
    export_plan_pdf,
    export_voices_pdf,
    get_template_html,
)

logger = logging.getLogger(__name__)


def create_settings_panel(container: ui.column, topic_id: int, conn: sqlite3.Connection, settings: AppSettings) -> None:
    container.clear()

    with container:
        ui.label("Step 5: Export & Settings").classes("text-h5 font-bold q-mb-md")
        ui.label("Export your documents to DOCX or PDF format.").classes("text-body1 q-mb-lg")

        topic_repo = TopicRepository(conn)
        canvas_repo = CanvasElementRepository(conn)
        voices_repo = VoicePersonaRepository(conn)
        plan_repo = PlanSectionRepository(conn)

        topic = topic_repo.get_by_id(topic_id)
        topic_name = topic.name if topic else "Unknown"

        export_dir = Path.home() / "Documents" / "mPABS_Exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        exporter = DOCXExporter(export_dir)

        # DOCX Export Section
        ui.label("Microsoft Word (.docx)").classes("text-h6 font-bold q-mb-sm")

        with ui.row().classes("w-full gap-4"):

            def export_canvas_docx():
                elements = canvas_repo.get_by_topic(topic_id)
                if not elements:
                    ui.notify("No canvas elements to export.", type="warning")
                    return
                path = exporter.export_canvas(topic_name, elements)
                ui.notify(f"Canvas exported to {path}", type="positive")

            ui.button("Export Canvas (.docx)", on_click=export_canvas_docx).props("color=primary icon=download")

            def export_voices_docx():
                voices = voices_repo.get_by_topic(topic_id)
                if not voices:
                    ui.notify("No voices to export.", type="warning")
                    return
                path = exporter.export_voices(topic_name, voices)
                ui.notify(f"Voices exported to {path}", type="positive")

            ui.button("Export Voices (.docx)", on_click=export_voices_docx).props("color=secondary icon=download")

            def export_plan_docx():
                sections = plan_repo.get_by_topic(topic_id)
                if not sections:
                    ui.notify("No plan sections to export.", type="warning")
                    return
                path = exporter.export_plan(topic_name, sections)
                ui.notify(f"Business Plan exported to {path}", type="positive")

            ui.button("Export Business Plan (.docx)", on_click=export_plan_docx).props("color=accent icon=download")

        # PDF Export Section
        ui.label("Professional PDF (with Markdown Support)").classes("text-h6 font-bold q-mb-sm")

        if not WEASYPRINT_AVAILABLE:
            ui.label(
                "⚠ WeasyPrint is not installed — PDF export is disabled. "
                "Install it with: uv add weasyprint"
            ).classes("text-body2 text-negative q-mb-sm")

        with ui.row().classes("w-full gap-4"):

            def export_canvas_pdf_with_preview():
                elements = canvas_repo.get_by_topic(topic_id)
                if not elements:
                    ui.notify("No canvas elements to export.", type="warning")
                    return

                context = {
                    "topic_name": topic_name,
                    "generated_date": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "canvas_elements": elements,
                }

                get_template_html("canvas_template.html", context)

                with ui.dialog() as preview_dialog, ui.card().classes("min-w-[500px]"):
                    ui.label(f"Preview: {topic_name} - Canvas").classes("text-h6")

                    # Show HTML preview
                    with ui.column().classes("w-full max-h-96 overflow-auto p-4 bg-grey-100 border rounded"):
                        ui.markdown("<strong>HTML Preview ( rendered):</strong>").classes("text-sm text-grey")
                        # Display a simplified view for preview
                        for el in elements:
                            with ui.row().classes("w-full q-mb-sm"):
                                ui.label(el.element_name).classes("font-bold text-primary")

                    def confirm_export():
                        path = export_canvas_pdf(topic_name, elements, export_dir)
                        preview_dialog.close()
                        ui.notify(f"Canvas PDF exported to {path}", type="positive")

                    with ui.row().classes("w-full justify-end gap-2 q-mt-sm"):
                        ui.button("Cancel", on_click=preview_dialog.close).props("flat")
                        ui.button("Export PDF", on_click=confirm_export, icon="download").props("color=primary")

                preview_dialog.open()

            ui.button("Export Canvas (.pdf)", on_click=export_canvas_pdf_with_preview).props(
                "color=deep-orange icon=file_download"
            ).set_enabled(WEASYPRINT_AVAILABLE)

            def export_voices_pdf_with_preview():
                voices = voices_repo.get_by_topic(topic_id)
                if not voices:
                    ui.notify("No voices to export.", type="warning")
                    return

                context = {
                    "topic_name": topic_name,
                    "generated_date": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "voices": voices,
                }

                get_template_html("voices_template.html", context)

                with ui.dialog() as preview_dialog, ui.card().classes("min-w-[500px]"):
                    ui.label(f"Preview: {topic_name} - Voices").classes("text-h6")

                    with ui.column().classes("w-full max-h-96 overflow-auto p-4 bg-grey-100 border rounded"):
                        ui.markdown("<strong>PDF Preview (rendered):</strong>").classes("text-sm text-grey")
                        for voice in voices:
                            with ui.row().classes("w-full q-mb-sm"):
                                ui.label(f"{voice.name}").classes("font-bold text-primary")

                    def confirm_export():
                        path = export_voices_pdf(topic_name, voices, export_dir)
                        preview_dialog.close()
                        ui.notify(f"Voices PDF exported to {path}", type="positive")

                    with ui.row().classes("w-full justify-end gap-2 q-mt-sm"):
                        ui.button("Cancel", on_click=preview_dialog.close).props("flat")
                        ui.button("Export PDF", on_click=confirm_export, icon="download").props("color=deep-orange")

                preview_dialog.open()

            ui.button("Export Voices (.pdf)", on_click=export_voices_pdf_with_preview).props(
                "color=deep-orange icon=file_download"
            ).set_enabled(WEASYPRINT_AVAILABLE)

            def export_plan_pdf_with_preview():
                sections = plan_repo.get_by_topic(topic_id)
                if not sections:
                    ui.notify("No plan sections to export.", type="warning")
                    return

                context = {
                    "topic_name": topic_name,
                    "generated_date": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "plan_sections": sections,
                }

                get_template_html("plan_template.html", context)

                with ui.dialog() as preview_dialog, ui.card().classes("min-w-[500px]"):
                    ui.label(f"Preview: {topic_name} - Business Plan").classes("text-h6")

                    with ui.column().classes("w-full max-h-96 overflow-auto p-4 bg-grey-100 border rounded"):
                        ui.markdown("<strong>PDF Preview (rendered):</strong>").classes("text-sm text-grey")
                        for section in sections:
                            with ui.row().classes("w-full q-mb-sm"):
                                ui.label(section.section_name).classes("font-bold text-primary")

                    def confirm_export():
                        path = export_plan_pdf(topic_name, sections, export_dir)
                        preview_dialog.close()
                        ui.notify(f"Business Plan PDF exported to {path}", type="positive")

                    with ui.row().classes("w-full justify-end gap-2 q-mt-sm"):
                        ui.button("Cancel", on_click=preview_dialog.close).props("flat")
                        ui.button("Export PDF", on_click=confirm_export, icon="download").props("color=deep-orange")

                preview_dialog.open()

            ui.button("Export Business Plan (.pdf)", on_click=export_plan_pdf_with_preview).props(
                "color=deep-orange icon=file_download"
            ).set_enabled(WEASYPRINT_AVAILABLE)

        ui.separator().classes("w-full q-my-lg")

        # LaTeX Export Section
        ui.label("LaTeX (.tex)").classes("text-h6 font-bold q-mb-sm")

        session_repo = ResearchSessionRepository(conn)
        web_repo = WebSearchRepository(conn)

        with ui.row().classes("w-full gap-4"):

            def export_canvas_tex():
                try:
                    elements = canvas_repo.get_by_topic(topic_id)
                    if not elements:
                        ui.notify("No canvas elements to export.", type="warning")
                        return
                    path = export_canvas_latex(topic_name, elements, export_dir)
                    if path == Path(""):
                        ui.notify("No canvas elements to export.", type="warning")
                        return
                    ui.notify(f"Canvas LaTeX exported to {path}", type="positive")
                except Exception as exc:
                    logger.exception("Failed to export canvas LaTeX for topic %d", topic_id)
                    ui.notify(f"Failed to export canvas LaTeX: {exc}", type="negative")

            ui.button("Export Canvas (.tex)", on_click=export_canvas_tex).props("color=teal icon=description")

            def export_voices_tex():
                try:
                    voices = voices_repo.get_by_topic(topic_id)
                    if not voices:
                        ui.notify("No voices to export.", type="warning")
                        return
                    path = export_voices_latex(topic_name, voices, export_dir)
                    if path == Path(""):
                        ui.notify("No voices to export.", type="warning")
                        return
                    ui.notify(f"Voices LaTeX exported to {path}", type="positive")
                except Exception as exc:
                    logger.exception("Failed to export voices LaTeX for topic %d", topic_id)
                    ui.notify(f"Failed to export voices LaTeX: {exc}", type="negative")

            ui.button("Export Voices (.tex)", on_click=export_voices_tex).props("color=teal icon=description")

            def export_plan_tex():
                try:
                    sections = plan_repo.get_by_topic(topic_id)
                    if not sections:
                        ui.notify("No plan sections to export.", type="warning")
                        return
                    # Gather web search results for bibliography generation
                    search_results = []
                    sessions = session_repo.get_by_topic(topic_id)
                    for session in sessions:
                        search_results.extend(web_repo.get_by_session(session["id"]))

                    path = export_plan_latex(
                        topic_name,
                        sections,
                        export_dir,
                        search_results=search_results if search_results else None,
                    )
                    if path == Path(""):
                        ui.notify("No plan sections to export.", type="warning")
                        return
                    ui.notify(f"Business Plan LaTeX exported to {path}", type="positive")
                except Exception as exc:
                    logger.exception("Failed to export plan LaTeX for topic %d", topic_id)
                    ui.notify(f"Failed to export plan LaTeX: {exc}", type="negative")

            ui.button("Export Business Plan (.tex)", on_click=export_plan_tex).props("color=teal icon=description")

        ui.separator().classes("w-full q-my-lg")

        # Personality Mode Section
        ui.label("AI Personality Mode").classes("text-h6 font-bold q-mb-sm")
        ui.label("Select how creative or strict the AI responses should be.").classes("text-body2 q-mb-sm")

        personality_repo = PersonalityPreferenceRepository(conn)
        saved_prefs = personality_repo.get_by_topic(topic_id)
        current_mode = "Balanced"
        if saved_prefs:
            current_mode = saved_prefs.get("global", "Balanced")

        def on_personality_change(e) -> None:
            """Persist personality mode selection to the database."""
            try:
                personality_repo.save(topic_id, {"global": e.value})
                ui.notify(f"Personality mode set to {e.value}", type="positive")
            except Exception as exc:
                logger.exception("Failed to save personality mode for topic %d", topic_id)
                ui.notify(f"Failed to save personality mode: {exc}", type="negative")

        ui.select(
            options=["Creative", "Balanced", "Strict"],
            value=current_mode,
            on_change=on_personality_change,
            label="Personality Mode",
        ).classes("w-64")

        ui.separator().classes("w-full q-my-lg")

        # Specialist Assignments Section
        ui.label("Specialist Assignments").classes("text-h6 font-bold q-mb-sm")
        ui.label("View or override the AI specialist for each section.").classes("text-body2 q-mb-sm")

        override_repo = SpecialistOverrideRepository(conn)
        overrides = override_repo.get_all_overrides(topic_id)

        # Build specialist options: id -> role_title, plus a default option
        specialist_options = {"__default__": "Default (from registry)"}
        for persona in SPECIALIST_REGISTRY.values():
            specialist_options[persona.id] = persona.role_title

        # All sections: canvas elements + plan sections + voice_personas
        all_sections = [
            "Key Partners",
            "Key Activities",
            "Key Resources",
            "Value Propositions",
            "Customer Relationships",
            "Channels",
            "Customer Segments",
            "Cost Structure",
            "Revenue Streams",
            "Executive Summary",
            "Company Description",
            "Market Analysis",
            "Organization & Management",
            "Service or Product Line",
            "Marketing & Sales",
            "Funding Request",
            "Financial Projections",
            "Appendix",
            "voice_personas",
        ]

        for section_name in all_sections:
            default_specialist = get_specialist(section_name)
            current_id = overrides.get(section_name, "__default__")

            def make_on_change(sec=section_name):
                def on_change(e):
                    if e.value == "__default__":
                        override_repo.delete(topic_id, sec)
                        ui.notify(f"Reset {sec} to default specialist", type="info")
                    else:
                        override_repo.save(topic_id, sec, e.value)
                        ui.notify(f"Set {sec} specialist to {specialist_options[e.value]}", type="positive")

                return on_change

            with ui.row().classes("w-full items-center gap-2"):
                ui.label(section_name).classes("w-48 font-medium")
                ui.label(f"Default: {default_specialist.role_title}").classes("text-grey text-sm w-64")
                ui.select(
                    options=specialist_options,
                    value=current_id,
                    on_change=make_on_change(),
                    label="Override",
                ).classes("w-64")

        ui.separator().classes("w-full q-my-lg")
        ui.label("App Settings").classes("text-h6 font-bold q-mb-sm")
        ui.label(f"LM Studio Endpoint: {settings.lm_studio_base_url}").classes("text-body2")
