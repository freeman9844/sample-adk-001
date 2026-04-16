"""
Run the agent locally for quick testing (no deployment needed).

Usage:
    GOOGLE_CLOUD_PROJECT=your-project python test_local.py
    adk web   # browser UI (recommended)
"""

import os

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")

from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService
from google.adk.types import Content, Part
from agent import root_agent

USER_ID = "local-test-user"
SESSION_ID = "local-session-001"

QUERIES = [
    "Hello! Who are you?",
    "What time is it in Seoul right now?",
    "Please summarize this: The Google Agent Development Kit (ADK) is an open-source "
    "framework that lets developers build, evaluate, and deploy AI agents. It supports "
    "multi-agent architectures, built-in tools, and seamless deployment to Vertex AI "
    "Agent Engine.",
]


def main() -> None:
    session_service = InMemorySessionService()
    runner = InMemoryRunner(agent=root_agent, session_service=session_service)
    session_service.create_session(
        app_name=root_agent.name,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )

    for query in QUERIES:
        print(f"\n{'='*60}")
        print(f"User : {query}")
        print(f"{'='*60}")

        for event in runner.run(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=Content(role="user", parts=[Part(text=query)]),
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        print(f"Agent: {part.text}")


if __name__ == "__main__":
    main()
