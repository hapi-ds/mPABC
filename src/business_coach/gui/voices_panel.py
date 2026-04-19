import asyncio
import sqlite3
from nicegui import ui
from business_coach.db.repository import CanvasElementRepository, VoicePersonaRepository
from business_coach.agents.workflow import generate_voice_personas

def create_voices_panel(
    container: ui.column,
    topic_id: int,
    conn: sqlite3.Connection,
    canvas_repo: CanvasElementRepository,
    voices_repo: VoicePersonaRepository
) -> None:
    container.clear()
    
    with container:
        # Use fresh repo to get latest data after generation
        fresh_voices_repo = VoicePersonaRepository(conn)
        
        ui.label("Step 3: Custom Voices (Target Personas)").classes("text-h5 font-bold q-mb-md")
        ui.label("Generate target audience personas based on your Business Model Canvas.").classes("text-body1 q-mb-md")
        
        canvas_elements = canvas_repo.get_by_topic(topic_id)
        
        if not canvas_elements:
            with ui.card().classes("w-full bg-yellow-50 border-l-4 border-yellow-500"):
                ui.icon("warning", size="md").classes("text-yellow-600")
                ui.label("Please generate some Business Model Canvas elements first.").classes("text-body1 text-grey-8 q-mt-sm")
                with ui.row().classes("q-mt-sm"):
                    ui.markdown("[Go to Canvas Panel →](#canvas)").classes("text-primary text-sm")
            return
        
        num_voices = ui.number("Number of voices to generate", value=3, format="%.0f").classes("w-64")
        spinner = ui.spinner(size="sm")
        spinner.set_visibility(False)
        
        personas_container = ui.column().classes("w-full q-mt-md gap-4")
        
        def display_personas():
            personas_container.clear()
            # Use fresh repo for latest data
            personas = fresh_voices_repo.get_by_topic(topic_id)
            if not personas:
                with personas_container: ui.label("No personas generated yet.").classes("text-grey")
                return
                
            for p in personas:
                with personas_container:
                    with ui.card().classes("w-full bg-grey-1"):
                        ui.label(p.name).classes("text-h6 font-bold")
                        ui.label(p.description).classes("text-body2 q-mb-sm")
                        ui.label(f"Style: {p.communication_style}").classes("text-caption italic")
        
        async def run_generation():
            spinner.set_visibility(True)
            try:
                canvas_text = "\n".join([f"{e.element_name}:\n{e.content}" for e in canvas_elements])
                num = int(num_voices.value)
                
                results = await asyncio.to_thread(generate_voice_personas, canvas_text, num)
                
                # Clear existing personas using passed-in repo
                voices_repo.delete_by_topic(topic_id)
                
                # Save new personas
                for r in results:
                    voices_repo.create(
                        topic_id, 
                        r.get("name", "Unknown"), 
                        r.get("description", ""), 
                        r.get("communication_style", "")
                    )
                ui.notify(f"Generated {len(results)} personas.", type="positive")
            except Exception as e:
                ui.notify(f"Generation failed: {e}", type="negative")
            finally:
                spinner.set_visibility(False)
                # Use fresh repo to display latest data
                display_personas()
                
        ui.button("Generate Voices", on_click=run_generation).props("color=primary")
        display_personas()
