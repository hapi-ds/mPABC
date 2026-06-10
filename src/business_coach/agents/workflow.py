import dspy
import json
import logging
import sqlite3

from business_coach.dspy_modules.modules import (
    BusinessCanvasGenerator,
    VoicePersonaGenerator,
    PlanSectionGenerator,
    SearchSectionGenerator,
    SearchResultScorer,
)
from business_coach.parsers.web_search import search_web
from business_coach.rag.embeddings import EmbeddingService
from business_coach.db.repository import (
    WebSearchRepository,
    ResearchSessionRepository,
    PersonalityPreferenceRepository,
    SpecialistOverrideRepository,
)
from business_coach.agents.specialists import get_specialist, SPECIALIST_REGISTRY, SpecialistPersona
from business_coach.exceptions import SearchServiceError

logger = logging.getLogger(__name__)

# Per-task LM instances, populated by init_task_lms() at startup
_task_lms: dict[str, dspy.LM] = {}


def init_task_lms(lms: dict[str, dspy.LM]) -> None:
    """Store per-task LM instances for use by workflow functions.

    Called once at startup after configure_dspy() returns the LM dict.
    """
    _task_lms.update(lms)


PERSONALITY_PROMPTS: dict[str, str] = {
    "Creative": "You are a highly creative and imaginative business advisor. Think outside the box, suggest bold ideas, and explore unconventional approaches.",
    "Balanced": "You are a balanced business advisor. Combine creative thinking with factual accuracy and practical considerations.",
    "Strict": "You are a precise and factual business advisor. Only state what can be supported by evidence or established business principles. Avoid speculation.",
}


def _get_personality_prompt(topic_id: int, conn: sqlite3.Connection) -> str:
    """Read the personality mode for a topic and return the system prompt.

    Args:
        topic_id: The topic ID to look up preferences for.
        conn: An open SQLite connection.

    Returns:
        The personality system prompt string, defaulting to "Balanced".
    """
    try:
        repo = PersonalityPreferenceRepository(conn)
        prefs = repo.get_by_topic(topic_id)
        mode = "Balanced"  # default
        if prefs:
            mode = prefs.get("global", "Balanced")
        return PERSONALITY_PROMPTS.get(mode, PERSONALITY_PROMPTS["Balanced"])
    except Exception:
        logger.exception(
            "Failed to read personality mode for topic %d, using Balanced default",
            topic_id,
        )
        return PERSONALITY_PROMPTS["Balanced"]


def _resolve_specialist(
    section_name: str,
    topic_id: int | None = None,
    conn: sqlite3.Connection | None = None,
) -> SpecialistPersona:
    """Resolve the specialist persona for a section, checking overrides first.

    Args:
        section_name: The canvas element or plan section name.
        topic_id: Optional topic ID for override lookup.
        conn: Optional SQLite connection for override lookup.

    Returns:
        The resolved SpecialistPersona (override > registry > fallback).
    """
    if topic_id is not None and conn is not None:
        try:
            repo = SpecialistOverrideRepository(conn)
            override_id = repo.get_override(topic_id, section_name)
            if override_id is not None:
                # Look up the specialist by ID in the registry
                for persona in SPECIALIST_REGISTRY.values():
                    if persona.id == override_id:
                        return persona
                # Override references a non-existent specialist
                logger.warning(
                    "Override for topic %d section '%s' references unknown specialist '%s', falling back to default",
                    topic_id,
                    section_name,
                    override_id,
                )
        except Exception:
            logger.exception(
                "Failed to read specialist override for topic %d section '%s'",
                topic_id,
                section_name,
            )
    return get_specialist(section_name)


def _compose_prompt(
    topic_id: int | None,
    conn: sqlite3.Connection | None,
    section_name: str,
) -> str:
    """Build the composed prompt: personality + specialist.

    Args:
        topic_id: The topic ID (for personality and override lookup).
        conn: SQLite connection.
        section_name: The section name to resolve the specialist for.

    Returns:
        The full composed prompt string.
    """
    personality = PERSONALITY_PROMPTS["Balanced"]  # default
    if topic_id is not None and conn is not None:
        personality = _get_personality_prompt(topic_id, conn)

    specialist = _resolve_specialist(section_name, topic_id, conn)
    return f"{personality}\n\n{specialist.system_prompt}"


def generate_search_sections(business_idea: str, user_feedback: str = "") -> list[dict]:
    """Generate search sections using LLM."""
    query_agent = dspy.Predict(SearchSectionGenerator)
    try:
        with dspy.context(lm=_task_lms.get("research")):
            q_res = query_agent(business_idea=business_idea, user_feedback=user_feedback)
        queries_text = q_res.sections_json

        # Strip markdown json blocks if present
        if queries_text.startswith("```json"):
            queries_text = queries_text[7:-3]
        elif queries_text.startswith("```"):
            queries_text = queries_text[3:-3]

        sections = json.loads(queries_text.strip())
        if not isinstance(sections, list):
            return [{"section_name": "General Research", "search_query": str(sections)}]
        return sections
    except Exception as e:
        logger.error(f"Failed to generate sections: {e}")
        return [
            {"section_name": "Competitors", "search_query": f"top competitors for {business_idea[:50]}"},
            {
                "section_name": "Target Customers",
                "search_query": f"target audience demographics for {business_idea[:50]}",
            },
            {"section_name": "Finances", "search_query": f"startup costs and pricing for {business_idea[:50]}"},
        ]


def run_section_search(
    topic_id: int,
    business_idea: str,
    section_name: str,
    search_query: str,
    conn,
    rag_engine,
    settings,
    progress_callback,
) -> list:
    """Run search, score, and index for a single section."""
    session_repo = ResearchSessionRepository(conn)
    web_repo = WebSearchRepository(conn)
    emb_service = EmbeddingService(
        model_name=settings.embedding_model_name,
        api_base=settings.lm_studio_base_url,
        api_key=settings.lm_studio_api_key,
    )
    scorer_agent = dspy.Predict(SearchResultScorer)

    docs_to_index = []
    saved_results = []

    progress_callback(f"Searching web for '{search_query}'...")
    session_id = session_repo.create(topic_id, search_query)
    try:
        results = search_web(search_query, max_results=5)
    except SearchServiceError as e:
        logger.error(f"Search service unavailable for query '{search_query}': {e}")
        progress_callback(f"Search service unavailable: {e}")
        return saved_results

    progress_callback(f"Found {len(results)} results. Scoring...")

    # Phase 1: Score each result individually (one failure doesn't cascade)
    for res in results:
        try:
            with dspy.context(lm=_task_lms.get("research")):
                score_res = scorer_agent(
                    business_idea=business_idea, search_query=search_query, search_result_snippet=res.snippet
                )
        except Exception as e:
            logger.warning(f"Scoring failed for '{res.title[:40]}': {e}")
            score_res = None

        if score_res is not None:
            try:
                score = int(score_res.relevance_score)
            except ValueError:
                score = 50
        else:
            score = 50

        if score >= 60:  # Threshold for relevance
            web_repo.create(session_id, res)
            saved_results.append(res)

    # Threshold notification: results found but none passed scoring threshold
    if results and not saved_results:
        progress_callback(
            f"Found {len(results)} results, but none scored above the relevance threshold (60). Consider broadening your query."
        )
        return saved_results

    # Phase 2: Attempt embedding + RAG indexing (does not gatekeep result display)
    for res in saved_results:
        embedding_bytes = emb_service.generate_embedding(res.title + " " + res.snippet)
        if embedding_bytes:
            import struct

            res.embedding = embedding_bytes

            emb_floats = list(struct.unpack(f"{len(embedding_bytes) // 4}f", embedding_bytes))
            docs_to_index.append(
                {
                    "text": f"[{section_name}] {res.title}\\n{res.snippet}",
                    "metadata": {"url": res.url, "source": "web", "section": section_name},
                    "embedding": emb_floats,
                }
            )
        else:
            progress_callback(
                f"Warning: Could not generate embedding for '{res.title[:40]}...' — result saved without RAG indexing"
            )

    if docs_to_index:
        progress_callback(f"Indexing {len(docs_to_index)} relevant documents...")
        rag_engine.index_with_embeddings(topic_id, docs_to_index)
        progress_callback("Done!")

    return saved_results


def generate_canvas_element(
    business_idea: str,
    element_name: str,
    previous_content: str = "",
    user_feedback: str = "",
    conn: sqlite3.Connection | None = None,
    topic_id: int | None = None,
) -> str:
    """Generate content for a specific canvas element using DSPy.

    Args:
        business_idea: The core business idea description.
        element_name: The canvas element name (e.g. 'Key Partners').
        previous_content: Previously generated content, if any.
        user_feedback: User feedback to incorporate, if any.
        conn: Optional SQLite connection for personality mode lookup.
        topic_id: Optional topic ID for personality mode lookup.

    Returns:
        Generated content string for the canvas element.
    """
    signature = BusinessCanvasGenerator
    composed = _compose_prompt(topic_id, conn, element_name)
    original_instructions = signature.__doc__ or ""
    signature = signature.with_instructions(f"{composed}\n\n{original_instructions}")

    agent = dspy.Predict(signature)
    try:
        with dspy.context(lm=_task_lms.get("canvas")):
            result = agent(
                business_idea=business_idea,
                element_name=element_name,
                previous_content=previous_content,
                user_feedback=user_feedback,
            )
        return result.generated_content
    except Exception as e:
        logger.error(f"Failed to generate canvas element: {e}")
        return f"Error generating {element_name}."


def generate_voice_personas(
    business_canvas_text: str,
    num_personas: int,
    conn: sqlite3.Connection | None = None,
    topic_id: int | None = None,
) -> list[dict]:
    """Generate a list of voice personas based on the canvas.

    Args:
        business_canvas_text: The completed business model canvas text.
        num_personas: Number of personas to generate.
        conn: Optional SQLite connection for personality mode lookup.
        topic_id: Optional topic ID for personality mode lookup.

    Returns:
        List of persona dicts with 'name', 'description', 'communication_style'.
    """
    signature = VoicePersonaGenerator
    composed = _compose_prompt(topic_id, conn, "voice_personas")
    original_instructions = signature.__doc__ or ""
    signature = signature.with_instructions(f"{composed}\n\n{original_instructions}")

    agent = dspy.Predict(signature)
    try:
        with dspy.context(lm=_task_lms.get("voices")):
            result = agent(business_canvas=business_canvas_text, num_personas=str(num_personas))
        personas_text = result.personas_json

        # Strip markdown json blocks if present
        if personas_text.startswith("```json"):
            personas_text = personas_text[7:-3]
        elif personas_text.startswith("```"):
            personas_text = personas_text[3:-3]

        return json.loads(personas_text.strip())
    except Exception as e:
        logger.error(f"Failed to generate personas: {e}")
        return []


def generate_plan_section(
    business_idea: str,
    business_canvas_text: str,
    personas_text: str,
    section_name: str,
    previous_content: str = "",
    user_feedback: str = "",
    conn: sqlite3.Connection | None = None,
    topic_id: int | None = None,
) -> str:
    """Generate a section of the business plan using DSPy.

    Args:
        business_idea: The core business idea description.
        business_canvas_text: The completed business model canvas text.
        personas_text: Text representation of voice personas.
        section_name: The plan section name to generate.
        previous_content: Previously generated content, if any.
        user_feedback: User feedback to incorporate, if any.
        conn: Optional SQLite connection for personality mode lookup.
        topic_id: Optional topic ID for personality mode lookup.

    Returns:
        Generated content string for the plan section.
    """
    signature = PlanSectionGenerator
    composed = _compose_prompt(topic_id, conn, section_name)
    original_instructions = signature.__doc__ or ""
    signature = signature.with_instructions(f"{composed}\n\n{original_instructions}")

    agent = dspy.Predict(signature)
    try:
        with dspy.context(lm=_task_lms.get("plan")):
            result = agent(
                business_idea=business_idea,
                business_canvas=business_canvas_text,
                personas=personas_text,
                section_name=section_name,
                previous_content=previous_content,
                user_feedback=user_feedback,
            )
        return result.generated_content
    except Exception as e:
        logger.error(f"Failed to generate plan section: {e}")
        return f"Error generating {section_name}."
