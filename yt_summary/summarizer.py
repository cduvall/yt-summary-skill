"""LLM-based video transcript summarization."""

import anthropic


class SummarizerError(Exception):
    """Exception raised when summarization fails."""

    pass


def summarize_transcript(
    transcript: str, api_key: str, model: str = "claude-sonnet-4-5-20250929"
) -> str:
    """
    Summarize a video transcript using Claude API.

    Args:
        transcript: Transcript text to summarize
        api_key: Anthropic API key
        model: Claude model ID to use

    Returns:
        Raw summary text from Claude

    Raises:
        SummarizerError: If summarization fails
    """
    client = anthropic.Anthropic(api_key=api_key)

    try:
        message = client.messages.create(
            model=model,
            max_tokens=2048,
            system="You are an expert at summarizing video transcripts with attention to actionable details.",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Summarize the following video transcript in less than five sentences. "
                        "Then provide a bulleted list of the top takeaways from the video.\n\n"
                        "IMPORTANT: If the video contains any of the following, extract them explicitly:\n"
                        "- Step-by-step instructions or procedures\n"
                        "- Supplement protocols or stacks (dosages, timing, combinations)\n"
                        "- Specific recommendations or action items\n"
                        "- Product names, brands, or specific tools mentioned\n"
                        "- Numbered lists or sequential processes\n\n"
                        "Format your response as:\n"
                        "SUMMARY:\n[your summary here]\n\n"
                        "TOP TAKEAWAYS:\n- [takeaway 1]\n- [takeaway 2]\n...\n\n"
                        "PROTOCOLS & INSTRUCTIONS:\n"
                        "[If the video contains specific protocols, supplement stacks, step-by-step instructions, "
                        "or detailed recommendations, list them here with exact dosages, timing, and steps. "
                        "If none exist, write 'None mentioned.']\n\n"
                        f"TRANSCRIPT:\n{transcript}"
                    ),
                }
            ],
        )
        return message.content[0].text

    except Exception as e:
        raise SummarizerError(f"Claude API error: {e}") from e
