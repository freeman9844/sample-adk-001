"""
Deploy the sample agent to Vertex AI Agent Engine (us-central1).

Uses vertexai.agent_engines (GA API) instead of the older
vertexai.preview.reasoning_engines so that:
  - agent_framework is set in the spec  → Framework shown in the console
  - async / async_stream / bidi_stream modes are registered → Playground works
  - model inference is routed to the global endpoint via GOOGLE_CLOUD_LOCATION
    override in agent/agent.py

Usage:
    python deploy.py --project YOUR_PROJECT_ID
    python deploy.py --project YOUR_PROJECT_ID --delete RESOURCE_NAME
    python deploy.py --project YOUR_PROJECT_ID --list
"""

import argparse
import os

import vertexai
from vertexai import agent_engines

LOCATION = "us-central1"  # Agent Engine location


def deploy(project_id: str) -> None:
    staging_bucket = f"gs://{project_id}-adk-staging"
    vertexai.init(project=project_id, location=LOCATION, staging_bucket=staging_bucket)

    from agent import root_agent

    app = agent_engines.AdkApp(
        agent=root_agent,
        enable_tracing=True,
    )

    print(f"Deploying to Agent Engine in {LOCATION}...")
    remote_app = agent_engines.create(
        agent_engine=app,
        requirements=[
            "google-adk>=1.0.0",
            "google-genai>=1.0.0",
            "google-cloud-aiplatform[adk,agent_engines]>=1.88.0",
            "cloudpickle>=3.0.0",
        ],
        extra_packages=["agent/"],
        display_name="sample-adk-agent",
        description="Simple ADK sample agent (gemini-3-flash-preview, global)",
    )

    print(f"\nDeployed successfully!")
    print(f"Resource name : {remote_app.resource_name}")
    print(f"\nTo test remotely:")
    print(f"  session = remote_app.create_session(user_id='test-user')")
    print(f"  for event in remote_app.stream_query(")
    print(f"      user_id='test-user',")
    print(f"      session_id=session['id'],")
    print(f"      message='What time is it in Seoul?',")
    print(f"  ):")
    print(f"      print(event)")


def delete(project_id: str, resource_name: str) -> None:
    vertexai.init(project=project_id, location=LOCATION)
    agent_engines.get(resource_name).delete()
    print(f"Deleted: {resource_name}")


def list_agents(project_id: str) -> None:
    vertexai.init(project=project_id, location=LOCATION)
    for agent in agent_engines.list():
        print(agent.resource_name, "-", agent.display_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, help="GCP project ID")
    parser.add_argument("--delete", metavar="RESOURCE_NAME", help="Delete a deployed agent")
    parser.add_argument("--list", action="store_true", help="List deployed agents")
    args = parser.parse_args()

    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", args.project)
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")

    if args.delete:
        delete(args.project, args.delete)
    elif args.list:
        list_agents(args.project)
    else:
        deploy(args.project)
