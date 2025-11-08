import json
import os
import re
from typing import List, Dict, Any, Optional, Tuple

DEFAULT_NUM_QUESTIONS = 5


def _normalize_items(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    norm = {"items": []}
    for it in items or []:
        q = it.get("question") or it.get("q") or it.get("prompt")
        choices = it.get("choices") or it.get("options") or []
        correct = it.get("correct_index")
        # Allow models that return correct letter like "B" or number
        correct_letter = it.get("correct")
        if correct is None and correct_letter is not None:
            if isinstance(correct_letter, str):
                idx = ord(correct_letter.strip().upper()[0]) - ord("A")
                if 0 <= idx < len(choices):
                    correct = idx
            elif isinstance(correct_letter, int):
                if 0 <= correct_letter < len(choices):
                    correct = correct_letter
        if q and choices:
            norm["items"].append({
                "question": q,
                "choices": [str(c) for c in choices],
                "correct_index": correct if isinstance(correct, int) else 0,
                "points": int(it.get("points") or 1),
                "explanation": it.get("explanation") or "",
            })
    return norm


def _build_prompt(topic: str, difficulty: str, num_questions: int) -> str:
    return (
        "You are an expert quiz generator. Create multiple-choice questions as strict JSON.\n"
        f"Topic: {topic}\n"
        f"Difficulty: {difficulty}\n"
        f"Count: {num_questions}\n\n"
        "Return JSON with this schema: {\n"
        "  \"items\": [\n"
        "    {\n"
        "      \"question\": string,\n"
        "      \"choices\": [string, string, string, string],\n"
        "      \"correct_index\": integer (0-3),\n"
        "      \"explanation\": string (optional),\n"
        "      \"points\": integer (optional, default 1)\n"
        "    }\n"
        "  ]\n"
        "}\n"
        "Do not include any commentary, markdown, or code fences—only raw JSON."
    )


def _extract_json_blob(text: str) -> Optional[str]:
    # Try to find the first JSON object in the text
    if not text:
        return None
    # Strip code fences if present
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.IGNORECASE | re.MULTILINE)
    # Find outermost braces
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return None


def _openai_call(prompt: str, model: Optional[str] = None, timeout: int = 30) -> Tuple[str, Dict[str, Any]]:
    from openai import OpenAI

    client = OpenAI()
    model = model or os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        timeout=timeout,
    )
    content = resp.choices[0].message.content if resp.choices else ""
    meta = {"id": getattr(resp, "id", None), "model": model}
    return content or "", meta


def _anthropic_call(prompt: str, model: Optional[str] = None, timeout: int = 30) -> Tuple[str, Dict[str, Any]]:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    client = anthropic.Client(api_key=api_key) if api_key else anthropic.Client()
    model = model or os.getenv("ANTHROPIC_MODEL", "claude-2.1")
    # Using the legacy completions API for compatibility
    full_prompt = f"{anthropic.HUMAN_PROMPT} {prompt}{anthropic.AI_PROMPT}"
    resp = client.completions.create(model=model, max_tokens_to_sample=1000, prompt=full_prompt)
    content = getattr(resp, "completion", "")
    meta = {"model": model}
    return content or "", meta


def _gemini_call(prompt: str, model: Optional[str] = None, timeout: int = 30) -> Tuple[str, Dict[str, Any]]:
    """Call Google Gemini via google-generativeai client with model auto-discovery.

    - Reads API key from GOOGLE_API_KEY or GEMINI_API_KEY
    - If GEMINI_MODEL is unset or invalid, lists available models and picks the
      first text-capable model using generateContent.
    - Returns (text, meta) where meta contains chosen model and discovery info.
    """
    import google.generativeai as genai  # type: ignore

    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY/GEMINI_API_KEY for Gemini provider")

    # Basic sanity check: Gemini API keys from AI Studio typically start with 'AIza'
    if not (api_key.startswith("AIza") or api_key.startswith("ya29") or api_key.startswith("gsk_")):
        # Don't block, but include a helpful meta hint
        pass

    genai.configure(api_key=api_key)

    # Try to resolve a valid model
    explicit = model or os.getenv("GEMINI_MODEL")
    available_models = []
    try:
        available_models = [
            m.name for m in genai.list_models()
            if getattr(m, "supported_generation_methods", None)
            and "generateContent" in m.supported_generation_methods
        ]
    except Exception:
        # Listing can fail on some accounts; we'll fallback to known names
        available_models = []

    # list_models returns names like 'models/gemini-2.5-flash' – the SDK accepts plain ids.
    def _plain(n: str) -> str:
        return n.split("/")[-1] if "/" in n else n
    available_plain = [_plain(n) for n in available_models]

    # Preferred candidates in order
    preferred = [
        # Latest naming
        "gemini-flash-latest",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        # 1.5 series for wider compatibility
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        # Pro models as fallback
        "gemini-2.5-pro",
        "gemini-1.5-pro-latest",
        "gemini-1.5-pro",
        "gemini-pro",
    ]

    chosen: Optional[str] = None
    if explicit:
        chosen = explicit
        # If we could list models and the explicit one isn't present, fall back
        if available_plain and _plain(chosen) not in available_plain:
            chosen = None

    if not chosen:
        # If we have a list, pick the first preferred that exists; otherwise use the first available
        if available_plain:
            for p in preferred:
                if p in available_plain:
                    chosen = p
                    break
            if not chosen:
                chosen = available_plain[0]
        else:
            # Last-resort guess if list_models failed
            chosen = preferred[0]

    generation_config = {"temperature": 0.3}
    m = genai.GenerativeModel(chosen, generation_config=generation_config)

    # generate_content has no explicit timeout; rely on HTTP client defaults
    resp = m.generate_content(prompt)
    content = ""
    try:
        content = resp.text or ""
    except Exception:
        content = ""

    meta = {
        "model": chosen,
        "explicit_model": explicit,
        "listed_models": available_plain[:25],
        "listed_models_raw": available_models[:25],
    }
    return content, meta


def generate_questions(topic: str, difficulty: str = "medium", num_questions: int = DEFAULT_NUM_QUESTIONS,
                       provider: Optional[str] = None) -> Dict[str, Any]:
    """Generate multiple-choice questions via the configured provider and return normalized JSON.

    Returns a dict: {"prompt": str, "raw": str, "parsed": dict, "provider": str, "meta": dict}
    """
    # Provider selection precedence: explicit env/arg -> openai -> anthropic -> gemini
    provider = provider or os.getenv("AI_PROVIDER")
    if not provider:
        if os.getenv("OPENAI_API_KEY"):
            provider = "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
            provider = "gemini"
        else:
            raise ValueError("No AI provider configured. Set AI_PROVIDER and corresponding API key in .env")
    prompt = _build_prompt(topic, difficulty, num_questions)

    raw = ""
    meta: Dict[str, Any] = {}

    if provider == "openai":
        raw, meta = _openai_call(prompt)
    elif provider == "anthropic":
        raw, meta = _anthropic_call(prompt)
    elif provider == "gemini":
        raw, meta = _gemini_call(prompt)
    else:
        raise ValueError(f"Unknown AI provider: {provider}")

    json_blob = _extract_json_blob(raw) or raw
    parsed_dict: Dict[str, Any]
    try:
        parsed_dict = json.loads(json_blob)
        # If the model returned a top-level list, wrap it
        if isinstance(parsed_dict, list):
            parsed_dict = {"items": parsed_dict}
    except Exception:
        # Last resort: try to normalize an empty list to avoid crashing callers
        parsed_dict = {"items": []}

    parsed = _normalize_items(parsed_dict.get("items") if isinstance(parsed_dict, dict) else [])
    return {"prompt": prompt, "raw": raw, "parsed": parsed, "provider": provider, "meta": meta}
