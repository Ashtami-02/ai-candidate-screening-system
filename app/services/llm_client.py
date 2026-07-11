"""
Small wrapper around the Gemini API.

Why this file exists: without it, every module that needs the LLM would
configure its own client and repeat the same boilerplate. Centralizing it
here means if we ever swap models, add retry logic, or switch providers,
we change it in exactly one place.
"""

import google.generativeai as genai

from app.config import settings

genai.configure(api_key=settings.gemini_api_key)
_model = genai.GenerativeModel(settings.gemini_model)


def generate(prompt: str, max_output_tokens: int = None) -> str:
    """
    Send a prompt to Gemini and return the plain text response.

    max_output_tokens, when set, caps how much the model can generate.
    This isn't just a safety limit -- response time scales with output
    length, so capping a task that only needs a short answer (like resume
    extraction) measurably speeds up that specific call.

    This is intentionally simple (no streaming, no chat history) --
    every call is a single, independent request. Session/conversation
    state, if we need it later, will be managed by OUR code (in the
    database), not by keeping a live chat object in memory.
    """
    generation_config = {"max_output_tokens": max_output_tokens} if max_output_tokens else None
    # Without this, the SDK automatically retries quota/network errors with
    # increasing delays for 30-60+ seconds before finally raising -- long
    # enough that the browser gives up first and reports a bare "Failed to
    # fetch," hiding the real reason. Capping the timeout means a failure
    # surfaces in ~20s with an actual error message instead.
    response = _model.generate_content(
        prompt,
        generation_config=generation_config,
        request_options={"timeout": 60},
    )
    return response.text
