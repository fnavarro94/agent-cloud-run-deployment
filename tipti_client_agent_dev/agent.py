from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import FunctionTool


from . import prompt
from .sub_agents import reschedule_agent, incidents_agent, question_and_answer_agent
from .tools import escalate_to_human_adk
from datetime import date

from pathlib import Path
from dotenv import load_dotenv


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
# MODEL = "gemini-2.0-flash"

tool_asignar_agente = FunctionTool(func=escalate_to_human_adk)

root_agent = LlmAgent(
    name="client_coordinator",
    model=MODEL,
    description=(
        "Asiste a los usuarios de Tipti en diferentes procesos como reagendamiento de órdenes,"
        "reporte de incidencias y permite responder preguntas del usuario delegando cada tarea a subagentes especializados."
        
    ),
    instruction=prompt.CLIENT_COORDINATOR_PROMPT,
    output_key="client_coordinator_output",
    sub_agents=[reschedule_agent, incidents_agent, question_and_answer_agent],
    tools=[tool_asignar_agente]
    
    
)

# root_agent = client_coordinator
