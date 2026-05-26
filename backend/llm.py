"""
LLM integration via OpenRouter API.

Model: mistralai/mistral-7b-instruct:free
  - Free tier, fast, reliable JSON output
  - Pin this model ID so results are reproducible

The prompt is engineered to return ONLY valid JSON — no markdown fences,
no prose. The parser handles edge cases (fences, whitespace) robustly.
"""

import json
import os
import re

import httpx
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_ID = "openai/gpt-oss-120b:free"

# Maximum characters of text to send to the LLM (avoid token overflow)
MAX_TEXT_CHARS = 8000


def _build_prompt(text: str) -> str:
    """
    Build the structured generation prompt.
    The model is explicitly told to return ONLY JSON — no preamble or prose.
    """
    truncated = text[:MAX_TEXT_CHARS]
    return f"""You are an expert study assistant. Analyze the following text and generate study material.

Return ONLY valid JSON in exactly this format — no markdown, no explanation, no code fences, just raw JSON:

{{
  "flashcards": [
    {{"front": "Specific question about a fact, concept, or definition", "back": "Clear and precise answer from the text"}},
    {{"front": "...", "back": "..."}},
    {{"front": "...", "back": "..."}},
    {{"front": "...", "back": "..."}},
    {{"front": "...", "back": "..."}}
  ],
  "quiz": [
    {{
      "question": "A specific question from the text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer_index": 0
    }},
    {{
      "question": "...",
      "options": ["...", "...", "...", "..."],
      "correct_answer_index": 1
    }},
    {{
      "question": "...",
      "options": ["...", "...", "...", "..."],
      "correct_answer_index": 2
    }},
    {{
      "question": "...",
      "options": ["...", "...", "...", "..."],
      "correct_answer_index": 0
    }},
    {{
      "question": "...",
      "options": ["...", "...", "...", "..."],
      "correct_answer_index": 3
    }}
  ]
}}

Requirements:
- Generate EXACTLY 5 flashcards and EXACTLY 5 quiz questions
- All questions must be based ONLY on facts present in the provided text
- Flashcard fronts must ask about specific facts, concepts, or definitions — not vague summaries
- Each quiz question must have EXACTLY 4 options and correct_answer_index must be 0, 1, 2, or 3
- Do NOT invent information not present in the text

Text to analyze:
---
{truncated}
---"""


def _extract_json(raw: str) -> dict:
    """
    Robustly extract JSON from the LLM response.
    Handles markdown code fences, leading/trailing whitespace, etc.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).strip()
    cleaned = re.sub(r"```\s*$", "", cleaned).strip()

    # Try direct parse first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find JSON object boundaries
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start:end])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not parse JSON from LLM response. Raw output:\n{raw[:500]}")


def _validate_structure(data: dict) -> None:
    """Validate that the parsed JSON has the required keys and counts."""
    if "flashcards" not in data or "quiz" not in data:
        raise ValueError("LLM response missing 'flashcards' or 'quiz' keys")

    for i, fc in enumerate(data["flashcards"]):
        if "front" not in fc or "back" not in fc:
            raise ValueError(f"Flashcard {i} missing 'front' or 'back'")

    for i, q in enumerate(data["quiz"]):
        if "question" not in q or "options" not in q or "correct_answer_index" not in q:
            raise ValueError(f"Quiz question {i} missing required fields")
        if len(q["options"]) != 4:
            raise ValueError(f"Quiz question {i} must have exactly 4 options")
        if q["correct_answer_index"] not in [0, 1, 2, 3]:
            raise ValueError(f"Quiz question {i} correct_answer_index must be 0-3")


async def generate_study_content(extracted_text: str) -> dict:
    """
    Call OpenRouter with the study text and return parsed flashcards + quiz.

    Returns:
        {
            "flashcards": [{"front": str, "back": str}, ...],
            "quiz": [{"question": str, "options": [...], "correct_answer_index": int}, ...]
        }

    Raises:
        ValueError: if API key missing, API call fails, or response is unparseable
    """
    if not OPENROUTER_API_KEY:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable is not set. "
            "Please add it to your .env file."
        )

    prompt = _build_prompt(extracted_text)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://ai-study-assistant.onrender.com",
        "X-Title": "AI Study Assistant",
    }

    payload = {
        "model": MODEL_ID,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,  # Low temp = more deterministic JSON output
        "max_tokens": 2048,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(OPENROUTER_BASE_URL, json=payload, headers=headers)

    if response.status_code != 200:
        raise ValueError(
            f"OpenRouter API error {response.status_code}: {response.text[:300]}"
        )

    result = response.json()
    raw_content = result["choices"][0]["message"]["content"]

    data = _extract_json(raw_content)
    _validate_structure(data)

    return data
