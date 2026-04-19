import asyncio
import sqlite3
from nicegui import ui
from business_coach.db.repository import BusinessIdeaRepository, CanvasElementRepository, ChatHistoryRepository
from business_coach.agents.workflow import generate_canvas_element
from business_coach.gui.chat_panel import create_chat_panel
from business_coach.gui.editable_field import create_editable_field

CANVAS_ELEMENTS = [
    "Key Partners", "Key Activities", "Key Resources", 
    "Value Propositions", "Customer Relationships", "Channels", 
    "Customer Segments", "Cost Structure", "Revenue Streams"
]

def create_canvas_panel(
    container: ui.column,
    topic_id: int,
    conn: sqlite3.Connection,
    idea_repo: BusinessIdeaRepository,
    canvas_rel_repo: CanvasElementRepository,
    chat_repo: ChatHistoryRepository
) -> None:
    container.clear()
    
    all_handlers = []
    
    with container.classes("w-full h-full").style("display: flex; flex-direction: row; gap: 16px;"):
        
        # Left side: Canvas Elements
        with ui.column().classes("w-2/3 h-full overflow-y-auto q-pr-md"):
            ui.label("Step 2: Business Model Canvas").classes("text-h5 font-bold q-mb-md")
            
            idea_data = idea_repo.get_by_topic(topic_id)
            idea_text = idea_data["primary_description"] if idea_data else ""
            
            if not idea_text:
                with ui.card().classes("w-full bg-yellow-50 border-l-4 border-yellow-500"):
                    ui.icon("warning", size="md").classes("text-yellow-600")
                    ui.label("Please enter your business idea in the 'Idea & Search' tab first.").classes("text-body1 text-grey-8 q-mt-sm")
                    with ui.row().classes("q-mt-sm"):
                        ui.markdown("[Go to Idea Panel →](#idea)").classes("text-primary text-sm")
                return
            
            async def run_all_canvas():
                for handler in all_handlers:
                    await handler()
            
            with ui.row().classes("w-full q-mb-md"):
                ui.button("Run All Elements", on_click=run_all_canvas).props("color=accent icon=play_strength")
            
            for element in CANVAS_ELEMENTS:
                with ui.card().classes("w-full q-mb-md"):
                    ui.label(element).classes("text-h6 font-bold")
                    
                    existing = canvas_rel_repo.get_element(topic_id, element)
                    content = existing.content if existing else ""
                    feedback = existing.user_feedback if existing and existing.user_feedback else ""
                    
                    editable_content_container = ui.column().classes("w-full q-mb-sm")
                    editable_content = create_editable_field(
                        value=content,
                        label="Content",
                        readonly_label=f"{element} Content",
                        is_frozen=True,
                        rows=4,
                    ).render(editable_content_container)
                    
                    editable_feedback_container = ui.column().classes("w-full q-mb-sm")
                    editable_feedback = create_editable_field(
                        value=feedback,
                        label="Feedback / Review Notes",
                        readonly_label="Review Notes",
                        is_frozen=False,
                        rows=2,
                    ).render(editable_feedback_container)
                    
                    spinner = ui.spinner(size="sm").classes("q-ml-sm")
                    spinner.set_visibility(False)
                    
                    def make_handler(el_name=element, content_field=editable_content, f_in=editable_feedback, spin=spinner):
                        async def handler():
                            spin.set_visibility(True)
                            try:
                                result = await asyncio.to_thread(
                                    generate_canvas_element,
                                    business_idea=idea_text,
                                    element_name=el_name,
                                    previous_content=content_field.value,
                                    user_feedback=f_in.value
                                )
                                content_field.value = result
                                canvas_rel_repo.upsert(topic_id, el_name, result, f_in.value)
                                ui.notify(f"{el_name} updated.", type="positive")
                            except Exception as e:
                                ui.notify(f"Failed to generate {el_name}: {e}", type="negative")
                            finally:
                                spin.set_visibility(False)
                        return handler
                    
                    handler = make_handler()
                    all_handlers.append(handler)

                    with ui.row().classes("w-full justify-end q-mt-sm"):
                        ui.button("Generate / Redo", on_click=handler).props("color=primary")
                        save_content_btn = ui.button("Save Content", on_click=editable_content.save).props("flat color=secondary size=sm")
                        save_feedback_btn = ui.button("Save Feedback", on_click=editable_feedback.save).props("flat color=secondary size=sm")
                        
        # Right side: AI Chat
        with ui.column().classes("w-1/3 h-full"):
            ui.label("AI Assistant").classes("text-h6 font-bold q-mb-sm")
            chat_container = ui.column().classes("w-full border rounded p-2").style("flex-grow: 1; height: 600px; overflow-y: auto;")
            create_chat_panel(chat_container, topic_id, chat_repo, rag_engine=None, settings=None, idea_repo=idea_repo)
