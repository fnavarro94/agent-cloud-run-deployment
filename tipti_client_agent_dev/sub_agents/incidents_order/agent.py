from google.adk import Agent
from google.adk.tools import FunctionTool
from google.adk.tools.load_memory_tool import load_memory_tool



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


from . import prompt
from .tools import *

from datetime import datetime

date_today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# MODEL = "gemini-2.0-flash"
MODEL = "gemini-2.5-flash-preview-05-20"

tool_identificar_usuario_por_telefono = FunctionTool(func=identificar_usuario_por_telefono)
tool_iniciar_sesion_cliente = FunctionTool(func=iniciar_sesion_cliente)
tool_validar_codigo_otp = FunctionTool(func=validar_codigo_otp)
tool_ordenes_entregadas = FunctionTool(func=obtener_ordenes_entregadas)
tool_fechas_disponibles = FunctionTool(func=obtener_fechas_disponibles)
tool_horas_por_fecha = FunctionTool(func=obtener_horas_por_fecha)
tool_validar_orden = FunctionTool(func=validar_orden)
tool_productos_en_orden = FunctionTool(func=buscar_productos_en_orden)
tool_validar_credito = FunctionTool(func=validar_credito)
tool_create_incident_missing_products = FunctionTool(func=create_incident_missing_products)
tool_create_incident_product_in_bad_condition = FunctionTool(func=create_incident_product_in_bad_condition)
tool_credit_value_to_tipti_card= FunctionTool(func=credit_value_to_tipti_card)


root_agent = Agent(
    model=MODEL,
    name="incidents_order_agent",
    description=(
        "Este agente es responsable del gestionar los incidentes de prodcutos de ordenes ya entregadas"
    ),
    #instruction=prompt.INCIDENT_ORDER_PROMPT.format(date_today=date_today),
    instruction=prompt.INCIDENT_ORDER_PROMPT,
    tools=[tool_identificar_usuario_por_telefono, tool_iniciar_sesion_cliente, tool_validar_codigo_otp,
    tool_ordenes_entregadas, tool_fechas_disponibles, tool_horas_por_fecha, tool_validar_orden,
    tool_productos_en_orden, tool_validar_credito, tool_create_incident_missing_products,
    tool_create_incident_product_in_bad_condition, tool_credit_value_to_tipti_card, load_memory_tool],
)