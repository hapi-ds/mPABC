"""PDF generation for mPABS using Jinja2 + WeasyPrint."""

import logging
from pathlib import Path
from datetime import datetime
import re

from jinja2 import Environment, FileSystemLoader, BaseLoader
from weasyprint import HTML

logger = logging.getLogger(__name__)

# Load templates from file system
template_dir = Path(__file__).parent.parent / 'templates'
env = Environment(
    loader=FileSystemLoader(str(template_dir)),
    autoescape=True
)

def _fix_markdown_table_headers(text: str) -> str:
    """Fix markdown tables that have missing leading pipe in header row."""
    lines = text.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Check if this looks like a markdown table header without leading |
        # Pattern: starts with text, has pipes, no leading |
        if '|' in stripped and not stripped.startswith('|'):
            # This might be a table header row missing the first pipe
            parts = [p.strip() for p in stripped.split('|') if p.strip()]
            
            if len(parts) >= 2:
                # Check if next line is separator (has dashes)
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if '|' in next_line and '-' in next_line:
                        # This is likely a table header row missing first pipe
                        fixed_lines.append('| ' + ' | '.join(parts) + ' |')
                        continue
        
        fixed_lines.append(line)
    
    return '\n'.join(fixed_lines)


def _markdown_filter(text: str) -> str:
    """Convert markdown to HTML."""
    try:
        import markdown as md_lib
        
        # Fix common markdown table formatting issues first
        fixed_text = _fix_markdown_table_headers(text)
        
        # Convert to HTML with tables extension
        return md_lib.markdown(fixed_text, extensions=['tables', 'fenced_code'])
    except ImportError:
        logger.warning("Markdown library not installed")
        return text.replace('\n', '<br>')

env.filters['markdown'] = _markdown_filter

# Define the correct order for business plan sections
PLAN_SECTION_ORDER = [
    "Executive Summary", "Company Description", "Market Analysis",
    "Organization & Management", "Service or Product Line",
    "Marketing & Sales", "Funding Request", "Financial Projections"
]
APPENDIX_SECTION = "Appendix"

def _sort_plan_sections(sections: list) -> list:
    """Sort plan sections in correct order with Appendix last."""
    ordered = []
    appendix = None
    
    for section in sections:
        if section.section_name == APPENDIX_SECTION:
            appendix = section
        else:
            # Find position in order
            try:
                idx = PLAN_SECTION_ORDER.index(section.section_name)
                ordered.append((idx, section))
            except ValueError:
                # Section not in standard list - append at end
                ordered.append((999, section))
    
    # Sort by index
    ordered.sort(key=lambda x: x[0])
    result = [s for _, s in ordered]
    
    # Append appendix if it exists
    if appendix:
        result.append(appendix)
    
    return result


def _render_template(template_name: str, context: dict) -> str:
    """Render a Jinja2 template with the given context."""
    try:
        template = env.get_template(template_name)
        return template.render(**context)
    except Exception as e:
        logger.error(f"Failed to render template {template_name}: {e}")
        raise


def export_canvas_pdf(topic_name: str, canvas_elements: list, output_dir: Path) -> Path:
    """Export Business Model Canvas to PDF."""
    context = {
        'topic_name': topic_name,
        'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'canvas_elements': canvas_elements
    }
    
    html_content = _render_template('canvas_template.html', context)
    html = HTML(string=html_content, base_url=str(template_dir))
    
    filename = f"{topic_name.replace(' ', '_')}_Canvas.pdf"
    out_path = output_dir / filename
    html.write_pdf(str(out_path))
    
    logger.info(f"Exported canvas PDF: {out_path}")
    return out_path


def export_voices_pdf(topic_name: str, voices: list, output_dir: Path) -> Path:
    """Export Target Personas to PDF."""
    context = {
        'topic_name': topic_name,
        'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'voices': voices
    }
    
    html_content = _render_template('voices_template.html', context)
    html = HTML(string=html_content, base_url=str(template_dir))
    
    filename = f"{topic_name.replace(' ', '_')}_Voices.pdf"
    out_path = output_dir / filename
    html.write_pdf(str(out_path))
    
    logger.info(f"Exported voices PDF: {out_path}")
    return out_path


def export_plan_pdf(topic_name: str, plan_sections: list, output_dir: Path) -> Path:
    """Export Business Plan to PDF."""
    # Sort sections in correct order
    sorted_sections = _sort_plan_sections(plan_sections)
    
    context = {
        'topic_name': topic_name,
        'generated_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'plan_sections': sorted_sections
    }
    
    html_content = _render_template('plan_template.html', context)
    html = HTML(string=html_content, base_url=str(template_dir))
    
    filename = f"{topic_name.replace(' ', '_')}_BusinessPlan.pdf"
    out_path = output_dir / filename
    html.write_pdf(str(out_path))
    
    logger.info(f"Exported plan PDF: {out_path}")
    return out_path


def get_template_html(template_name: str, context: dict) -> str:
    """Get rendered HTML for preview without generating PDF."""
    return _render_template(template_name, context)

