"""
OpenRouter client — OpenAI-compatible API for all LLM calls.
All planner and finder calls route through here.
"""

import os

from openai import OpenAI

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_EXTRA_HEADERS = {
    "HTTP-Referer": "https://github.com/Mohd-Mursaleen/android-ai-agent",
    "X-Title": "android-ai-agent",
}


def get_client() -> OpenAI:
    """
    Build an OpenAI client pointed at OpenRouter.

    Returns:
        Configured OpenAI client.

    Raises:
        ValueError: If OPENROUTER_API_KEY is not set.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENROUTER_API_KEY environment variable not set.\n"
            "Get your key at https://openrouter.ai/keys\n"
            "Then run: export OPENROUTER_API_KEY='your-key-here'"
        )
    return OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)


def vision_completion(
    model: str,
    system_prompt: str,
    user_text: str,
    image_base64: str,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    """
    Send a vision request (text + image) to OpenRouter.

    Args:
        model: OpenRouter model ID, e.g. "anthropic/claude-sonnet-4-5".
        system_prompt: System message content.
        user_text: User message text accompanying the image.
        image_base64: Base64-encoded PNG screenshot.
        temperature: Sampling temperature.
        max_tokens: Maximum response tokens.

    Returns:
        Stripped response text from the model.

    Raises:
        ValueError: If OPENROUTER_API_KEY is missing.
        openai.OpenAIError: On API or network errors.
    """
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"},
                    },
                ],
            },
        ],
        extra_headers=_EXTRA_HEADERS,
    )
    return response.choices[0].message.content.strip()


def text_completion(
    model: str,
    system_prompt: str,
    user_text: str,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    """
    Send a text-only request to OpenRouter.

    Args:
        model: OpenRouter model ID.
        system_prompt: System message content.
        user_text: User message text.
        temperature: Sampling temperature.
        max_tokens: Maximum response tokens.

    Returns:
        Stripped response text from the model.

    Raises:
        ValueError: If OPENROUTER_API_KEY is missing.
        openai.OpenAIError: On API or network errors.
    """
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        extra_headers=_EXTRA_HEADERS,
    )
    return response.choices[0].message.content.strip()
