from google.adk import Agent
from google.adk.tools import FunctionTool
from . import prompt
from .tools import *

# MODEL = "gemini-2.0-flash"
MODEL = "gemini-2.5-flash-preview-05-20"

tool_answer_question = FunctionTool(func=answer_the_question)

root_agent = Agent(
    model=MODEL,
    name="question_and_answer_agent",
    instruction=prompt.QyA_PROMPT,
    tools=[tool_answer_question],
)