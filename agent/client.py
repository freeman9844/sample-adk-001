"""
Shared google-genai client configured for Vertex AI with the global endpoint.

Both ADK tools and standalone GenAI SDK calls share this client so that
model inference always hits the global endpoint regardless of where the
Agent Engine itself runs (us-central1).
"""

import os
from google import genai

MODEL = "gemini-3-flash-preview"

# Module-level singleton — created once per process.
_client: genai.Client | None = None


def get_client() -> genai.Client:
    """Return a cached genai.Client pointed at the Vertex AI global endpoint."""
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True,
            project=os.environ["GOOGLE_CLOUD_PROJECT"],
            location="global",  # model served from the global endpoint
        )
    return _client
