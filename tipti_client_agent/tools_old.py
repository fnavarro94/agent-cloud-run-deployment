import os
import time
from datetime import datetime, timedelta, timezone

import httpx
from dotenv import load_dotenv

load_dotenv(override=True)

# ───────── HubSpot auth constants ─────────────────────────────────────
CLIENT_ID: str | None = os.getenv("HS_CLIENT_ID")
CLIENT_SECRET: str | None = os.getenv("HS_CLIENT_SECRET")
ENV_REFRESH_TOKEN: str | None = os.getenv("HS_REFRESH_TOKEN")  # ← must be set
BASE_API_URL = "https://api.hubapi.com"

# A single HTTP client reused by all tools
client = httpx.Client(base_url=BASE_API_URL, timeout=10)

# In‑memory cache that lives for the lifetime of the container
_token_data: dict | None = None  # will hold access/refresh tokens & expiry
_REFRESH_MARGIN = 120  # seconds before expiry to proactively refresh


# ---------------------------------------------------------------------
# ────────────────  AUTH / TOKEN MANAGEMENT HELPERS  ──────────────────
# ---------------------------------------------------------------------

def _exchange_refresh_token(refresh_token: str) -> dict:
    """Swap a refresh token for a fresh **access** token.

    Raises ``httpx.HTTPStatusError`` if HubSpot returns an error.
    """
    payload = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
    }
    r = httpx.post(f"{BASE_API_URL}/oauth/v1/token", data=payload)
    r.raise_for_status()

    data = r.json()
    # HubSpot gives ``expires_in`` (seconds). Convert to absolute epoch.
    data["expires_at"] = int(time.time()) + data.get("expires_in", 0)
    return data


def refresh_token_if_needed() -> tuple[bool, str | None]:
    """Ensure the HubSpot **access** token is valid and attached to *client*.

    Returns
    -------
    tuple
        (ready: bool, error_message: str | None)
    """
    global _token_data

    # 1) Bootstrap on first use ---------------------------------------
    if _token_data is None:
        if not ENV_REFRESH_TOKEN:
            return False, "HS_REFRESH_TOKEN not set in the environment."
        try:
            _token_data = _exchange_refresh_token(ENV_REFRESH_TOKEN)
        except httpx.HTTPError as e:
            msg = e.response.text if isinstance(e, httpx.HTTPStatusError) else str(e)
            return False, f"Initial token exchange failed: {msg}"

    # 2) Refresh ≤ _REFRESH_MARGIN seconds before expiry --------------
    if time.time() >= _token_data["expires_at"] - _REFRESH_MARGIN:
        try:
            _token_data = _exchange_refresh_token(_token_data["refresh_token"])
        except httpx.HTTPError as e:
            msg = e.response.text if isinstance(e, httpx.HTTPStatusError) else str(e)
            return False, f"Token refresh failed: {msg}"

    # 3) Attach Bearer token to the shared client ---------------------
    client.headers["Authorization"] = f"Bearer {_token_data['access_token']}"
    return True, None


# ---------------------------------------------------------------------
# ────────────────────────────  TOOLS  ────────────────────────────────
# ---------------------------------------------------------------------

def saludar_al_usuario() -> dict:
    """Trivial demo tool."""
    return {"result": "se saludó al usuario"}


def create_handoff_task(phone_number: str) -> dict:
    """Create a high‑priority HubSpot task so a human can take over.

    Parameters
    ----------
    phone_number : str
        Customer phone number in **E.164** format (e.g. "+59398…").
    """
    # Step 0 ── Auth ---------------------------------------------------
    ok, err = refresh_token_if_needed()
    if not ok:
        return {"status": "error", "step": "auth", "error_message": err}

    # Step 1 ── Look up the contact -----------------------------------
    try:
        search = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "phone",
                    "operator": "EQ",
                    "value": phone_number,
                }]
            }],
            "properties": ["phone", "hubspot_owner_id"],
        }
        r = client.post("/crm/v3/objects/contacts/search", json=search)
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPStatusError as e:
        return {"status": "error", "step": "contact_search", "error_message": e.response.text}

    if data.get("total", 0) == 0:
        return {
            "status": "error",
            "step": "contact_search",
            "error_message": f"No contact with phone {phone_number}",
        }

    contact = data["results"][0]
    contact_id = contact["id"]
    owner_id = contact["properties"].get("hubspot_owner_id")

    # Step 2 ── Assign owner if missing -------------------------------
    if not owner_id:
        owner_id = "80477440"  # 👈 fixed owner for debugging
        try:
            client.patch(
                f"/crm/v3/objects/contacts/{contact_id}",
                json={"properties": {"hubspot_owner_id": owner_id}},
            )
        except httpx.HTTPStatusError as e:
            return {"status": "error", "step": "owner_assign", "error_message": e.response.text}

    # Step 3 ── Create the task ---------------------------------------
    due = int((datetime.now(timezone.utc) + timedelta(hours=8)).timestamp() * 1000)
    task_payload = {
        "properties": {
            "hs_task_subject": "Human assistance requested via Chatbot",
            "hs_task_body": "The chatbot has requested a human to take over.",
            "hs_task_status": "NOT_STARTED",
            "hs_task_priority": "HIGH",
            "hubspot_owner_id": owner_id,
            "hs_timestamp": due,
        },
        "associations": [{
            "to": {"id": contact_id},
            "types": [{
                "associationCategory": "HUBSPOT_DEFINED",
                "associationTypeId": 204,
            }],
        }],
    }
    try:
        r = client.post("/crm/v3/objects/tasks", json=task_payload)
        r.raise_for_status()
        task_id = r.json()["id"]
    except httpx.HTTPStatusError as e:
        return {"status": "error", "step": "task_create", "error_message": e.response.text}

    # Step 4 ── Toggle workflow‑trigger flags -------------------------
    ts_ms = str(int(time.time() * 1000))
    try:
        client.patch(
            f"/crm/v3/objects/contacts/{contact_id}",
            json={
                "properties": {
                    "admin_responding": "true",
                    "admin_responding_timestamp": ts_ms,
                }
            },
        )
    except httpx.HTTPStatusError as e:
        return {"status": "error", "step": "workflow_trigger", "error_message": e.response.text}

    return {"status": "success", "task_id": task_id, "contact_id": contact_id}


def assign_agent(phone: str) -> dict:
    """Public‑facing tool: hand a WhatsApp/chatbot conversation to a human."""
    return create_handoff_task(phone)
