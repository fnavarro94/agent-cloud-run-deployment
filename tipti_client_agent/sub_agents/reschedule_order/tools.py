import os
import json
import requests
from dotenv import load_dotenv
from google.adk.tools import ToolContext

load_dotenv()
_token_cache = None

def obtener_token_dev() -> str:
    """
    Obtiene y cachea EN MEMORIA el token de autenticación para API de Tipti.
    This version is safe for cloud environments.
    """
    # Use the 'global' keyword to modify the variable defined outside the function.
    global _token_cache

    # 1. If the token is already in our memory cache, return it immediately.
    if _token_cache:
        print("Token found in cache.")
        return _token_cache

    # 2. If not in cache, print a message and fetch it from the API.
    print("Token not in cache. Fetching from API...")
    api_url = os.getenv("API_URL")
    url = f"{api_url}/misuper/api-token-auth/"
    payload = {
        "username": os.getenv("TIPTI_USERNAME"),
        "password": os.getenv("TIPTI_PASSWORD"),
        "returnSecureToken": True
    }
    headers = {
        "Content-Type": "application/json",
        "x-tipti": os.getenv("X-TIPTI")
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    token = response.json().get("token")

    # 3. Save the new token into our in-memory cache variable.
    _token_cache = token
    
    # 4. Return the new token.
    return token

# =========================================
# Tool: Identificar usuario por teléfono
# =========================================
def identificar_usuario_por_telefono(phone: str, tool_context: ToolContext):
    """
    Busca un usuario de Tipti por número de teléfono y obtener la información básica de la cuenta si existe. 
    Args:
        phone (str): Número de teléfono del usuario en formato internacional, e.g. '593984708324'
    Returns:
        dict: Diccionario con los datos del usuario si se encuentra, en el siguiente formato:
        {
            "first_name": str, "last_name": str, "user_id": str, "token": str, "prime_type": str, "client_id": int, "status": bool, "alive": bool
        }
        Si el número no está registrado:
        {
            "existe": False,
            "mensaje": "Usuario no encontrado"
        }
    """
    token_dev = obtener_token_dev()
    headers = {
        "Authorization": f"JWT {token_dev}",
        "Content-Type": "application/json",
        "x-tipti": os.getenv("X-TIPTI")
    }
    api_url = os.getenv("API_URL")
    url = f"{api_url}/api/v3/chatbot/user/?phone={phone}"
    response = requests.get(url, headers=headers)
    data = response.json()

    if data.get("token") != "":
        tool_context.state["TOKEN"] = data["token"]

    return data

# =========================================
# Tool: Iniciar sesión cliente
# =========================================
def iniciar_sesion_cliente(tipti_id: str):
    """Inicia sesión y envía código OTP al cliente."""
    api_url = os.getenv("API_URL")
    url = f"{api_url}/api/v3/chatbot/user?tipti_id={tipti_id}"
    response = requests.get(url)
    return response.json()

# =========================================
# Tool: Validar código OTP
# =========================================
def validar_codigo_otp(code_valid: str, tool_context: ToolContext):
    """Valida el código OTP ingresado por el usuario."""
    token_dev = obtener_token_dev()
    headers = {
        "Authorization": f"JWT {token_dev}",
        "Content-Type": "application/json",
        "x-tipti": os.getenv("X-TIPTI")
    }
    api_url = os.getenv("API_URL")
    url = f"{api_url}/api/v3/chatbot/user/validate?code_valid={code_valid}"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    if data.get("token") != "":
        tool_context.state["TOKEN"] = data["token"]

    return data

# =========================================
# Tool: Mostrar órdenes activas
# =========================================
def mostrar_ordenes_activas(TOKEN: str, tool_context: ToolContext):
    """Muestra las órdenes activas del cliente autenticado.
    Usa el token guardado en el estado como 'TOKEN"""

    token_state = tool_context.state.get("TOKEN")
    if token_state:
        TOKEN = token_state

    headers = {
        "Authorization": f"JWT {TOKEN}",
        "Content-Type": "application/json",
        "x-tipti": os.getenv("X-TIPTI")
    }
    url = f"{os.getenv('API_URL')}/api/v3/chatbot/active_orders"
    all_orders = []

    while url:
        response = requests.get(url, headers=headers)
        data = response.json()
        all_orders.extend(data.get("available_orders", []))
        url = data.get("next")

    return {"results": all_orders, "count": len(all_orders)}

# =========================================
# Tool: Obtener fechas disponibles
# =========================================
def obtener_fechas_disponibles(order_id: str, TOKEN: str, tool_context: ToolContext):
    """Obtiene las fechas disponibles para reagendar una orden."""
    
    token_state = tool_context.state.get("TOKEN")
    if token_state:
        TOKEN = token_state

    headers = {
        "Authorization": f"JWT {TOKEN}",
        "Content-Type": "application/json",
        "x-tipti": os.getenv("X-TIPTI")
    }
    url = f"{os.getenv('API_URL')}/api/v3/chatbot/order_available_schedule_dates_for_delivery?order_id={order_id}"
    response = requests.get(url, headers=headers)
    return response.json()

# =========================================
# Tool: Obtener horas disponibles por fecha
# =========================================
def obtener_horas_por_fecha(order_id: str, date: str, TOKEN: str, tool_context: ToolContext):
    """Obtiene las horas disponibles para una fecha específica y orden."""

    token_state = tool_context.state.get("TOKEN")
    if token_state:
        TOKEN = token_state

    headers = {
        "Authorization": f"JWT {TOKEN}",
        "Content-Type": "application/json",
        "x-tipti": os.getenv("X-TIPTI")
    }
    url = f"{os.getenv('API_URL')}/api/v3/chatbot/order_available_schedule_hours_for_delivery?date={date}&order_id={order_id}"
    all_hours = []

    while url:
        response = requests.get(url, headers=headers)
        data = response.json()
        all_hours.extend(data.get("results", []))
        url = data.get("next")

    return {"results": all_hours, "count": len(all_hours)}

# =========================================
# Tool: Reagendar orden
# =========================================
def reagendar_orden(order_id: str, new_date: str, new_hour: str, TOKEN: str, tool_context: ToolContext):
    """Reagenda una orden a nueva fecha y hora."""

    token_state = tool_context.state.get("TOKEN")
    if token_state:
        TOKEN = token_state

    headers = {
        "Authorization": f"JWT {TOKEN}",
        "Content-Type": "application/json",
        "x-tipti": os.getenv("X-TIPTI")
    }
    url = f"{os.getenv('API_URL')}/api/v3/chatbot/order_reschedule/"
    payload = {
        "order_id": order_id,
        "new_schedule_date": new_date,
        "new_schedule_hour": new_hour
    }
    response = requests.put(url, headers=headers, json=payload)
    return response.json()