"""
ADK tool functions.

get_current_time  — pure Python, no model call needed.
summarize_text    — calls GenAI SDK directly, showing how to use the
                    shared client alongside ADK.
"""

from datetime import datetime
import zoneinfo

from .client import MODEL, get_client


def get_current_time(timezone: str = "UTC") -> dict:
    """Returns the current time for a given timezone.

    Args:
        timezone: Timezone name (e.g. "UTC", "Asia/Seoul", "America/New_York")

    Returns:
        dict with 'time' and 'timezone' keys, or 'error' on failure.
    """
    try:
        tz = zoneinfo.ZoneInfo(timezone)
        now = datetime.now(tz)
        return {"time": now.strftime("%Y-%m-%d %H:%M:%S %Z"), "timezone": timezone}
    except Exception as e:
        return {"error": str(e), "timezone": timezone}


def summarize_text(text: str) -> dict:
    """Summarizes the given text using the GenAI SDK directly.

    This tool demonstrates calling google-genai alongside ADK:
    the same shared client (global endpoint, gemini-3-flash-preview)
    is used for both the agent's own reasoning and this direct SDK call.

    Args:
        text: The text to summarize.

    Returns:
        dict with 'summary' key, or 'error' on failure.
    """
    try:
        client = get_client()
        response = client.models.generate_content(
            model=MODEL,
            contents=f"Summarize the following text in 2-3 sentences:\n\n{text}",
        )
        return {"summary": response.text}
    except Exception as e:
        return {"error": str(e)}
