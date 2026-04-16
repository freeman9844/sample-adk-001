import os

from google.adk.agents import Agent

from .client import MODEL
from .tools import get_current_time, summarize_text

# ADK creates its own genai.Client using GOOGLE_CLOUD_LOCATION.
# Override to "global" so model inference hits the global endpoint
# even though Agent Engine runs in us-central1.
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

root_agent = Agent(
    name="sample_agent",
    model=MODEL,  # gemini-3-flash-preview via global endpoint
    description="A sample agent that checks the time and summarizes text.",
    instruction=(
        "You are a helpful assistant. "
        "Use get_current_time when asked about the current time. "
        "Use summarize_text when asked to summarize a passage. "
        "Answer concisely and clearly."
    ),
    tools=[get_current_time, summarize_text],
)
