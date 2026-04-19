import sqlite3
from pathlib import Path
from nicegui import ui
from business_coach.config import AppSettings
from business_coach.db.repository import TopicRepository, CanvasElementRepository, VoicePersonaRepository, PlanSectionRepository
from business_coach.export.docx_exporter import DOCXExporter
from business_coach.export.pdf_exporter import (
    export_canvas_pdf,
    export_voices_pdf,
    export_plan_pdf,
    get_template_html
)

def create_settings_panel(
    container: ui.column,
    topic_id: int,
    conn: sqlite3.Connection,
    settings: AppSettings
) -> None:
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
        
        with ui.row().classes("w-full gap-4"):
            preview_canvas_dialog = None
            
            def export_canvas_pdf_with_preview():
                elements = canvas_repo.get_by_topic(topic_id)
                if not elements:
                    ui.notify("No canvas elements to export.", type="warning")
                    return
                
                context = {
                    'topic_name': topic_name,
                    'generated_date': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'canvas_elements': elements
                }
                
                html_content = get_template_html('canvas_template.html', context)
                
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
            
            ui.button("Export Canvas (.pdf)", on_click=export_canvas_pdf_with_preview).props("color=deep-orange icon=file_download")
            
            def export_voices_pdf_with_preview():
                voices = voices_repo.get_by_topic(topic_id)
                if not voices:
                    ui.notify("No voices to export.", type="warning")
                    return
                
                context = {
                    'topic_name': topic_name,
                    'generated_date': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'voices': voices
                }
                
                html_content = get_template_html('voices_template.html', context)
                
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
            
            ui.button("Export Voices (.pdf)", on_click=export_voices_pdf_with_preview).props("color=deep-orange icon=file_download")
            
            def export_plan_pdf_with_preview():
                sections = plan_repo.get_by_topic(topic_id)
                if not sections:
                    ui.notify("No plan sections to export.", type="warning")
                    return
                
                context = {
                    'topic_name': topic_name,
                    'generated_date': __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'plan_sections': sections
                }
                
                html_content = get_template_html('plan_template.html', context)
                
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
            
            ui.button("Export Business Plan (.pdf)", on_click=export_plan_pdf_with_preview).props("color=deep-orange icon=file_download")
        
        ui.separator().classes("w-full q-my-lg")
        ui.label("App Settings").classes("text-h6 font-bold q-mb-sm")
        ui.label(f"LM Studio Endpoint: {settings.lm_studio_base_url}").classes("text-body2")

