import dspy


class BusinessCanvasGenerator(dspy.Signature):
    """Generate content for a specific Business Model Canvas element based on the initial idea and user feedback."""

    business_idea = dspy.InputField(desc="The core business idea")
    element_name = dspy.InputField(desc="The name of the canvas element (e.g. 'Key Partners', 'Value Propositions')")
    previous_content = dspy.InputField(desc="Previous content generated (if any)")
    user_feedback = dspy.InputField(desc="User feedback to incorporate (if any)")

    generated_content = dspy.OutputField(desc="The updated text for this canvas element.")


class VoicePersonaGenerator(dspy.Signature):
    """Generate target audience personas based on the completed Business Model Canvas."""

    business_canvas = dspy.InputField(desc="The completed business model canvas elements")
    num_personas = dspy.InputField(desc="Number of personas to generate")

    personas_json = dspy.OutputField(desc="A valid JSON array of objects, each with keys 'name', 'description', and 'communication_style'. Ensure proper commas between objects. Example: [{\"name\": \"...\", \"description\": \"...\", \"communication_style\": \"...\"}]")


class VoiceStatementGenerator(dspy.Signature):
    """Generate what a persona would say about the business idea in their unique communication style."""

    persona_name = dspy.InputField(desc="The name of the persona")
    persona_description = dspy.InputField(desc="Description of the persona's background and perspective")
    communication_style = dspy.InputField(desc="The persona's communication style")
    business_canvas = dspy.InputField(desc="The business model canvas text")

    voice_statement = dspy.OutputField(desc="A paragraph expressing what this persona would say about the business idea, written in their unique communication style")


class PlanSectionGenerator(dspy.Signature):
    """Generate a specific section of the Business Plan."""

    business_idea = dspy.InputField()
    business_canvas = dspy.InputField()
    personas = dspy.InputField()
    section_name = dspy.InputField()
    previous_content = dspy.InputField()
    user_feedback = dspy.InputField()

    generated_content = dspy.OutputField(desc="The updated text for this business plan section.")


class SearchSectionGenerator(dspy.Signature):
    """Generate search sections and specific queries for market research."""

    business_idea = dspy.InputField(desc="The core business idea")
    user_feedback = dspy.InputField(desc="User suggestions for refining the search sections (if any)")

    sections_json = dspy.OutputField(
        desc="A JSON list of objects, each with 'section_name' (e.g. 'Competitors', 'Customers', 'Finances') and 'search_query' (the exact query string to use in DuckDuckGo). Max 6 sections."
    )


class SearchResultScorer(dspy.Signature):
    """Score the relevance of a web search result to the business idea."""

    business_idea = dspy.InputField()
    search_query = dspy.InputField()
    search_result_snippet = dspy.InputField()

    relevance_score = dspy.OutputField(
        desc="An integer from 0 to 100 representing how useful this snippet is for the business plan."
    )
    reasoning = dspy.OutputField(desc="Brief reason for the score.")


def configure_dspy(settings) -> dict[str, dspy.LM]:
    """Configure DSPy with per-task LM instances.

    Creates a separate LM for each agent task so users can assign
    different models via BC_MODEL_CANVAS, BC_MODEL_VOICES, etc.
    The "chat" model is set as the global default.

    Args:
        settings: AppSettings instance with model assignments.

    Returns:
        Dict mapping task name to configured dspy.LM instance.
    """

    def _make_lm(model_name: str, cache: bool = True) -> dspy.LM:
        return dspy.LM(
            model=f"openai/{model_name}",
            api_base=settings.lm_studio_base_url,
            api_key=settings.lm_studio_api_key,
            max_tokens=settings.default_max_tokens,
            cache=cache,
        )

    lms = {
        "canvas": _make_lm(settings.model_canvas),
        "voices": _make_lm(settings.model_voices, cache=False),
        "plan": _make_lm(settings.model_plan),
        "research": _make_lm(settings.model_research),
        "chat": _make_lm(settings.model_chat),
    }

    # Set chat model as the global default
    dspy.configure(lm=lms["chat"], adapter=dspy.ChatAdapter(use_json_adapter_fallback=False))
    return lms
