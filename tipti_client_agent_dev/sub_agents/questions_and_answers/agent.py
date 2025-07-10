from google.adk import Agent
from google.adk.tools import FunctionTool
from . import prompt
from .tools import *

# MODEL = "gemini-2.0-flash"


import os
from pathlib import Path

import google.auth
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.cloud import logging as google_cloud_logging

load_dotenv()

# Load environment variables from .env file in root directory
root_dir = Path(__file__).parent.parent
dotenv_path = root_dir / ".env"
load_dotenv(dotenv_path=dotenv_path)

# Use default project from credentials if not in .env
_, project_id = google.auth.default()
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "True")

MODEL = "gemini-2.5-flash-preview-05-20"

tool_answer_question = FunctionTool(func=answer_the_question)

root_agent = Agent(
    model=MODEL,
    name="question_and_answer_agent",
    instruction=prompt.QyA_PROMPT,
    tools=[tool_answer_question],
)