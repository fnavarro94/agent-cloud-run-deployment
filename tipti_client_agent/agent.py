from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools import FunctionTool


from . import prompt
from .sub_agents import reschedule_agent, incidents_agent, question_and_answer_agent
from .tools import escalate_to_human_adk
from datetime import date


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
