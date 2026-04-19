import dspy
import json
import logging
from business_coach.dspy_modules.modules import BusinessCanvasGenerator, VoicePersonaGenerator, PlanSectionGenerator, SearchSectionGenerator, SearchResultScorer
from business_coach.parsers.web_search import search_web
from business_coach.rag.embeddings import EmbeddingService
from business_coach.db.repository import WebSearchRepository, ResearchSessionRepository

def generate_search_sections(business_idea: str, user_feedback: str = "") -> list[dict]:
    """Generate search sections using LLM."""
    query_agent = dspy.Predict(SearchSectionGenerator)
    try:
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
            {"section_name": "Target Customers", "search_query": f"target audience demographics for {business_idea[:50]}"},
            {"section_name": "Finances", "search_query": f"startup costs and pricing for {business_idea[:50]}"}
        ]

def run_section_search(
    topic_id: int,
    business_idea: str,
    section_name: str,
    search_query: str,
    conn,
    rag_engine,
    settings,
    progress_callback
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
        progress_callback(f"Found {len(results)} results. Scoring...")
        for res in results:
            # Score the result
            score_res = scorer_agent(
                business_idea=business_idea,
                search_query=search_query,
                search_result_snippet=res.snippet
            )
            
            try:
                score = int(score_res.relevance_score)
            except ValueError:
                score = 50
                
            if score >= 60: # Threshold for relevance
                # Generate embedding
                embedding_bytes = emb_service.generate_embedding(res.title + " " + res.snippet)
                if embedding_bytes:
                    import struct
                    res.embedding = embedding_bytes
                    web_repo.create(session_id, res)
                    saved_results.append(res)
                    
                    emb_floats = list(struct.unpack(f"{len(embedding_bytes)//4}f", embedding_bytes))
                    docs_to_index.append({
                        "text": f"[{section_name}] {res.title}\\n{res.snippet}",
                        "metadata": {"url": res.url, "source": "web", "section": section_name},
                        "embedding": emb_floats
                    })
    except Exception as e:
        logger.error(f"Search/Score failed for query '{search_query}': {e}")
        progress_callback(f"Search failed: {e}")
        
    if docs_to_index:
        progress_callback(f"Indexing {len(docs_to_index)} relevant documents...")
        rag_engine.index_with_embeddings(topic_id, docs_to_index)
        progress_callback("Done!")
    else:
        progress_callback("No highly relevant documents found.")
        
    return saved_results


logger = logging.getLogger(__name__)

def generate_canvas_element(business_idea: str, element_name: str, previous_content: str = "", user_feedback: str = "") -> str:
    """Generate content for a specific canvas element using DSPy."""
    agent = dspy.Predict(BusinessCanvasGenerator)
    try:
        result = agent(
            business_idea=business_idea,
            element_name=element_name,
            previous_content=previous_content,
            user_feedback=user_feedback
        )
        return result.generated_content
    except Exception as e:
        logger.error(f"Failed to generate canvas element: {e}")
        return f"Error generating {element_name}."

def generate_voice_personas(business_canvas_text: str, num_personas: int) -> list[dict]:
    """Generate a list of voice personas based on the canvas."""
    agent = dspy.Predict(VoicePersonaGenerator)
    try:
        result = agent(
            business_canvas=business_canvas_text,
            num_personas=str(num_personas)
        )
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

def generate_plan_section(business_idea: str, business_canvas_text: str, personas_text: str, section_name: str, previous_content: str = "", user_feedback: str = "") -> str:
    """Generate a section of the business plan using DSPy."""
    agent = dspy.Predict(PlanSectionGenerator)
    try:
        result = agent(
            business_idea=business_idea,
            business_canvas=business_canvas_text,
            personas=personas_text,
            section_name=section_name,
            previous_content=previous_content,
            user_feedback=user_feedback
        )
        return result.generated_content
    except Exception as e:
        logger.error(f"Failed to generate plan section: {e}")
        return f"Error generating {section_name}."
