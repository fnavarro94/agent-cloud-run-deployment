from google.adk import Agent
from google.adk.tools import FunctionTool
from google.adk.tools.load_memory_tool import load_memory_tool

from . import prompt
from .tools import *

from datetime import datetime

date_today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# MODEL = "gemini-2.0-flash"
MODEL = "gemini-2.5-flash-preview-05-20"

tool_identificar_usuario_por_telefono = FunctionTool(func=identificar_usuario_por_telefono)
tool_iniciar_sesion_cliente = FunctionTool(func=iniciar_sesion_cliente)
tool_validar_codigo_otp = FunctionTool(func=validar_codigo_otp)
tool_ordenes_activas = FunctionTool(func=mostrar_ordenes_activas)
tool_fechas_disponibles = FunctionTool(func=obtener_fechas_disponibles)
tool_horas_por_fecha = FunctionTool(func=obtener_horas_por_fecha)
tool_reagendar_orden = FunctionTool(func=reagendar_orden)


root_agent = Agent(
    model=MODEL,
    name="reschedule_order_agent",
    description=(
        "Este agente es responsable del reagendamiento de órdenes activas"
    ),
    #instruction=prompt.RESCHEDULER_ORDER_PROMPT.format(date_today=date_today),
    instruction=prompt.RESCHEDULER_ORDER_PROMPT,
    tools=[
        tool_identificar_usuario_por_telefono, tool_iniciar_sesion_cliente, tool_validar_codigo_otp,
        tool_ordenes_activas, tool_fechas_disponibles, tool_horas_por_fecha, tool_reagendar_orden,
        load_memory_tool,
    ]
)