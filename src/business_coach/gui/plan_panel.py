import asyncio
import sqlite3
from nicegui import ui
from business_coach.db.repository import (
    BusinessIdeaRepository, CanvasElementRepository, VoicePersonaRepository, PlanSectionRepository, ChatHistoryRepository
)
from business_coach.agents.workflow import generate_plan_section

PLAN_SECTIONS = [
    "Executive Summary", "Company Description", "Market Analysis",
    "Organization & Management", "Service or Product Line",
    "Marketing & Sales", "Funding Request", "Financial Projections", "Appendix"
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
    header_status_label=None
) -> None:
    container.clear()
    
    with container:
        fresh_voices_repo = VoicePersonaRepository(conn)
        
        ui.label("Step 4: Business Plan").classes("text-h5 font-bold q-mb-md")
        ui.label("Generate the final business plan sections using context from your idea, canvas, and voices.").classes("text-body1 q-mb-md")
        
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
        section_components = {}
        
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
                        user_feedback=""
                    )
                    plan_repo.upsert(topic_id, section_name, result, "")
                    
                    # Update the UI component if it exists
                    if section_name in section_components:
                        disp = section_components[section_name]["display"]
                        disp.value = result
                        disp.update()
                    
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
                
                content_display = ui.textarea(value=content).classes("w-full").props("readonly rows=6")
                feedback_input = ui.input("Feedback / Review Notes", value=feedback).classes("w-full")
                
                # Store component reference for run_all
                section_components[section_name] = {"display": content_display}
                
                spinner = ui.spinner(size="sm").classes("q-ml-sm")
                spinner.set_visibility(False)
                
                def make_handler(sec_name=section_name, disp=content_display, f_in=feedback_input, spin=spinner):
                    async def handler():
                        spin.set_visibility(True)
                        try:
                            result = await asyncio.to_thread(
                                generate_plan_section,
                                business_idea=idea_text,
                                business_canvas_text=canvas_text,
                                personas_text=personas_text,
                                section_name=sec_name,
                                previous_content=disp.value,
                                user_feedback=f_in.value
                            )
                            disp.value = result
                            disp.update()
                            plan_repo.upsert(topic_id, sec_name, result, f_in.value)
                            ui.notify(f"{sec_name} updated.", type="positive")
                        except Exception as e:
                            ui.notify(f"Failed to generate {sec_name}: {e}", type="negative")
                        finally:
                            spin.set_visibility(False)
                    return handler
                
                with ui.row().classes("w-full justify-end q-mt-sm"):
                    ui.button("Generate / Redo", on_click=make_handler()).props("color=primary")

