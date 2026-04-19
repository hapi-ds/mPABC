from nicegui import ui
import sqlite3
import asyncio
import json
from business_coach.db.repository import BusinessIdeaRepository, ResearchSessionRepository, WebSearchRepository
from business_coach.agents.workflow import generate_search_sections, run_section_search
from business_coach.config import AppSettings
from business_coach.gui.editable_field import create_editable_field

def create_idea_panel(
    container: ui.column,
    topic_id: int,
    conn: sqlite3.Connection,
    idea_repo: BusinessIdeaRepository,
    rag_engine,
    settings: AppSettings,
    header_status_label: ui.label,
    header_spinner: ui.spinner
) -> None:
    container.clear()
    
    # Create fresh repo to ensure we get latest data after tab switches
    fresh_idea_repo = BusinessIdeaRepository(conn)
    session_repo = ResearchSessionRepository(conn)
    web_repo = WebSearchRepository(conn)
    
    with container:
        ui.label("Step 1: Your Business Idea").classes("text-h5 font-bold q-mb-md")
        
        # Load existing idea from fresh repo
        existing = fresh_idea_repo.get_by_topic(topic_id)
        desc = existing["primary_description"] if existing else ""
        saved_sections_json = existing["search_terms"][0] if existing and existing["search_terms"] else "[]"
        try:
            saved_sections = json.loads(saved_sections_json)
        except Exception:
            saved_sections = []
            
        editable_desc = create_editable_field(
            value=desc,
            label="Describe your business idea (Problem, Solution, Target Audience, Value Prop)",
            readonly_label="Business Idea",
            on_save=lambda val: idea_repo.upsert(topic_id, val, [json.dumps(saved_sections)]),
            is_frozen=True,
            rows=6,
        ).render(ui.column().classes("w-full q-mb-md"))
        
        ui.button("Save Idea", on_click=editable_desc.save).classes("q-mt-sm").props("color=primary")
        
        ui.separator().classes("w-full q-my-md")
        ui.label("Granular Market Research").classes("text-h6 font-bold q-mb-sm")
        ui.label("Generate research categories, then run each search individually or all at once.").classes("text-caption text-grey-7")
        
        sections_container = ui.column().classes("w-full gap-4 q-mt-md")
        
        # We'll store the run handlers so we can run them all
        run_handlers = []
        
        async def generate_sections():
            idea = editable_desc.value.strip()
            if not idea: 
                ui.notify("Please enter a business idea first.", type="warning")
                return
            
            header_spinner.set_visibility(True)
            header_status_label.set_text("Generating research sections...")
            
            try:
                sections = await asyncio.to_thread(generate_search_sections, business_idea=idea)
                nonlocal saved_sections
                saved_sections = sections
                save_idea(sections)
                render_sections(idea, sections)
            except Exception as e:
                ui.notify(f"Failed to generate sections: {e}", type="negative")
            finally:
                header_spinner.set_visibility(False)
                header_status_label.set_text("")
                
        with ui.row().classes("w-full gap-2 items-center q-mb-md"):
            ui.button("Generate Research Categories", on_click=generate_sections).props("color=secondary")
            
            async def run_all_searches():
                for handler in run_handlers:
                    await handler()
                    
            ui.button("Run All Searches", on_click=run_all_searches).props("color=accent icon=play_arrow")
        
        def render_sections(idea: str, sections: list):
            sections_container.clear()
            run_handlers.clear()
            for sec in sections:
                render_single_section(idea, sec)
                
        def render_single_section(idea: str, sec: dict):
            s_name = sec.get("section_name", "Research")
            s_query = sec.get("search_query", "")
            
            with sections_container:
                with ui.card().classes("w-full bg-grey-1"):
                    ui.label(s_name).classes("text-h6 font-bold")
                    
                    editable_query = create_editable_field(
                        value=s_query,
                        label="Search Query",
                        readonly_label="Search Query",
                        is_frozen=True,
                    ).render(ui.column().classes("w-full q-mb-sm"))
                    
                    progress_log = ui.log(max_lines=10).classes("w-full h-24 q-mb-sm").style("display: none;")
                    results_area = ui.column().classes("w-full gap-2")
                    
                    # Load existing results for this specific query
                    existing_sessions = session_repo.get_by_topic(topic_id)
                    for session in existing_sessions:
                        if session["query"] == s_query:
                            results = web_repo.get_by_session(session["id"])
                            for r in results:
                                with results_area:
                                    with ui.card().classes("w-full q-mb-sm bg-white"):
                                        ui.link(r.title, r.url).classes("text-subtitle2 font-bold")
                                        ui.label(r.snippet).classes("text-body2 text-grey-8")
                    
                    async def run_this_search():
                        progress_log.style("display: block;")
                        progress_log.clear()
                        progress_log.push(f"Starting search for: {editable_query.value}")
                        results_area.clear()
                        
                        def p_cb(msg: str):
                            progress_log.push(msg)
                            
                        try:
                            results = await asyncio.to_thread(
                                run_section_search,
                                topic_id=topic_id,
                                business_idea=idea,
                                section_name=s_name,
                                search_query=editable_query.value,
                                conn=conn,
                                rag_engine=rag_engine,
                                settings=settings,
                                progress_callback=p_cb
                            )
                            
                            if not results:
                                with results_area: ui.label("No relevant results found.").classes("text-grey")
                            else:
                                for r in results:
                                    with results_area:
                                        with ui.card().classes("w-full q-mb-sm bg-white"):
                                            ui.link(r.title, r.url).classes("text-subtitle2 font-bold")
                                            ui.label(r.snippet).classes("text-body2 text-grey-8")
                        except Exception as e:
                            progress_log.push(f"Error: {e}")
                            
                    run_handlers.append(run_this_search)
                    
                    with ui.row().classes("w-full items-center gap-2"):
                        ui.button("Run Search", on_click=run_this_search).props("color=primary size=sm")
                        ui.button("Rerun Search", on_click=run_this_search).props("flat color=primary size=sm")
                        ui.button("Save Query", on_click=editable_query.save).props("flat color=secondary size=sm")
                        
        if saved_sections:
            render_sections(desc, saved_sections)
