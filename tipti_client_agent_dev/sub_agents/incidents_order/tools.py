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
# Tool: Obtener órdenes entregadas
# =========================================
def obtener_ordenes_entregadas(TOKEN: str, tool_context: ToolContext):
    """Obtiene todas las órdenes que ya han sido entregadas."""

    token_state = tool_context.state.get("TOKEN")
    if token_state:
        TOKEN = token_state

    headers = {
        "Authorization": f"JWT {TOKEN}",
        "Content-Type": "application/json",
        "x-tipti": os.getenv("X-TIPTI")
    }
    api_url = os.getenv("API_URL")
    url = f"{api_url}/api/v3/chatbot/orders_delivered/"
    all_orders = []

    while url:
        response = requests.get(url, headers=headers)
        data = response.json()
        all_orders.extend(data.get("results", []))
        url = data.get("next")

    return {
        "results": all_orders,
        "count": len(all_orders)
    }

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
# Tool: Validar estado de una orden específica
# =========================================
def validar_orden(order_id: str, TOKEN: str, tool_context: ToolContext):
    """Valida que la orden pertenezca al cliente."""
    
    token_state = tool_context.state.get("TOKEN")
    if token_state:
        TOKEN = token_state

    headers = {
        "Authorization": f"JWT {TOKEN}",
        "Content-Type": "application/json",
        "x-tipti": os.getenv("X-TIPTI")
    }
    params = {"order_id": order_id}
    api_url = os.getenv("API_URL")
    url = f"{api_url}/api/v3/chatbot/validate_order/"
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

# =========================================
# Tool: Ver productos de una orden
# =========================================
def buscar_productos_en_orden(order_id: str, keyword: str):
    """Busca stockitems asociados a una orden usando la API interna de Tipti."""
    API_BASE_URL = "https://api-data.tipti.market/api/"
    auth_url = f"{API_BASE_URL}auth_token"
    auth_payload = {
        "email": "luis.chuquin@tipti.market",
        "password": os.getenv("CHUQIN_PASS")
    }
    auth_response = requests.post(auth_url, json=auth_payload)
    auth_response.raise_for_status()
    access_token = auth_response.json().get("access_token")

    headers_model = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload_model = {
        "key_word": keyword,
        "order_id": int(order_id)
    }
    url_model = f"{API_BASE_URL}services/search_terms_order"
    response = requests.post(url_model, headers=headers_model, json=payload_model)
    response.raise_for_status()
    return response.json()

# =========================================
# Tool: Validar credito
# =========================================
def validar_credito(order_id: str, stockitem_id: str, quantity: int, TOKEN: str, tool_context: ToolContext):
    """Valida que el valor total de la incidencia no supere los $10,
    y que no exista ya una incidencia activa para este producto en la orden."""
    
    token_state = tool_context.state.get("TOKEN")
    if token_state:
        TOKEN = token_state

    api_url = os.getenv("API_URL")
    url = f"{api_url}/api/v3/chatbot/validate_credit_value_to_tipti_card/"
    headers = {
        "Authorization": f"JWT {TOKEN}",
        "Content-Type": "application/json",
        "x-tipti": os.getenv("X-TIPTI")
    }
    params = {
        "order_id": order_id,
        "stockitem_id": stockitem_id,
        "quantity": quantity
    }

    response = requests.post(url, headers=headers, json=params)
    if response.status_code == 200:
        data = response.json()
        print("Validación de acreditación ejecutada:")
        print(json.dumps(data, indent=4))
        return data
    else:
        print(f"Error al validar acreditación. Status code: {response.status_code}")
        print(response.text)
        return None

# =========================================
# Tool: mising product
# =========================================
def create_incident_missing_products(order_id: int, stockitem_id: int, detail: str, quantity: int, date_order: str, hours_order: str, TOKEN: str, tool_context: ToolContext):
    """: Crear un nuevo pedido de un producto específico que tuvo algún inconveniente en una orden ya entregada"""
    
    token_state = tool_context.state.get("TOKEN")
    if token_state:
        TOKEN = token_state

    api_url = os.getenv("API_URL")
    url = f"{api_url}/api/v3/chatbot/create_incident_missing_products/"
    headers = {
        "Authorization": f"JWT {TOKEN}",
        "Content-Type": "application/json",
        "x-tipti": os.getenv("X-TIPTI")
    }
    payload = {
        "order_id":    order_id,
        "stockitem_id": stockitem_id,
        "incident_detail": detail,
        "quantity":    quantity,
        "date_order":  date_order,
        "hours_order": hours_order
    }
    
    response = requests.post(url, headers=headers, json=payload)
    return response.json()

# =========================================
# Tool: bad condition product
# =========================================
def create_incident_product_in_bad_condition(order_id: int, stockitem_id: int, detail: str, quantity: int, date_order: str, hours_order: str, TOKEN: str, tool_context: ToolContext):
    """Crear un nuevo pedido de un producto en mal estado que tuvo algún inconveniente en  una orden ya entregada """
    
    token_state = tool_context.state.get("TOKEN")
    if token_state:
        TOKEN = token_state

    api_url = os.getenv("API_URL")
    url = f"{api_url}/api/v3/chatbot/create_incident_product_in_bad_condition/"
    headers = {
        "Authorization": f"JWT {TOKEN}",
        "Content-Type": "application/json",
        "x-tipti": os.getenv("X-TIPTI")
    }
    body = {
        "order_id": order_id,
        "stockitem_id": stockitem_id,
        "incident_detail": detail,
        "quantity": quantity,
        "date_order": date_order,
        "hours_order": hours_order
    }
    response = requests.post(url, headers=headers, json=body)
    return response.json()

# =========================================
# Tool: credit_value_to_tipti_card
# =========================================
def credit_value_to_tipti_card(order_id: str, stockitem_id: str, incidence_type: str, quantity: int, TOKEN: str, tool_context: ToolContext):
    """Acreditar un valor a la Tipti Card cuando la orden ya está facturada"""
    token_state = tool_context.state.get("TOKEN")
    if token_state:
        TOKEN = token_state

    api_url = os.getenv("API_URL")
    url = f"{api_url}/api/v3/chatbot/credit_value_to_tipti_card/"
    
    headers = {
        "Authorization": f"JWT {TOKEN}",
        "Content-Type": "application/json",
        "x-tipti": os.getenv("X-TIPTI")
    }

    incidence_type = "producto_incorrecto"
    body = {
        "order_id": order_id,
        "stockitem_id": stockitem_id,
        "incidence_type": incidence_type,
        "quantity": quantity
    }
    response = requests.post(url, headers=headers, json=body)
    return response.json()
