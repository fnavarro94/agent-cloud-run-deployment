# ---------------------------------------------------------------------
# escalate_to_hubspot_agent.py   (full hand-off version)
#
# • Stateless OAuth (tokens live only in RAM)
# • Escalates ticket + assigns human agent
# • Creates high-priority Task
# • Sets contact.admin_responding / contact.admin_responding_timestamp
# ---------------------------------------------------------------------
from __future__ import annotations

import os
import random
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

import httpx
from dotenv import load_dotenv

# ────────────────────────── ENV / CONSTANTS ───────────────────────────
load_dotenv(override=True)

CLIENT_ID: str | None         = os.getenv("HS_CLIENT_ID")
CLIENT_SECRET: str | None     = os.getenv("HS_CLIENT_SECRET")
ENV_REFRESH_TOKEN: str | None = os.getenv("HS_REFRESH_TOKEN")  # <- must exist

BASE_API_URL = "https://api.hubapi.com"
PORTAL_ID    = 50110583

CLOSED_TICKET_STAGE_ID  = "4"
AWAITING_STAGE_DEFAULT  = "2"
REFRESH_MARGIN_SECONDS  = 120          # refresh 2 min before expiry
FALLBACK_OWNER_ID       = "80477440"   # used only when contact has no owner

# Shared HTTP client
_client = httpx.Client(base_url=BASE_API_URL, timeout=10)
_token_data: Dict[str, Any] | None = None   # in-memory token cache


# ─────────────────────── TOKEN-MANAGEMENT HELPERS ─────────────────────
def _exchange_refresh_token(refresh_token: str) -> Dict[str, Any]:
    if not (CLIENT_ID and CLIENT_SECRET):
        raise RuntimeError("HS_CLIENT_ID / HS_CLIENT_SECRET not set.")
    payload = {
        "grant_type":    "refresh_token",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": refresh_token,
    }
    r = httpx.post(f"{BASE_API_URL}/oauth/v1/token", data=payload)
    r.raise_for_status()
    data = r.json()
    data["expires_at"] = int(time.time()) + data.get("expires_in", 0)
    return data


def _refresh_token_if_needed() -> None:
    """Attach a valid Bearer token to `_client`."""
    global _token_data
    if _token_data is None:
        if not ENV_REFRESH_TOKEN:
            raise RuntimeError("HS_REFRESH_TOKEN missing in environment.")
        _token_data = _exchange_refresh_token(ENV_REFRESH_TOKEN)

    if time.time() >= _token_data["expires_at"] - REFRESH_MARGIN_SECONDS:
        _token_data = _exchange_refresh_token(_token_data["refresh_token"])

    _client.headers["Authorization"] = f"Bearer {_token_data['access_token']}"


# ─────────────────────────── HUBSPOT HELPERS ──────────────────────────
def _get_agent_ids() -> List[str]:
    """Return owner-IDs for every HubSpot user whose e-mail contains “agente”."""
    _refresh_token_if_needed()
    owners: List[Dict[str, Any]] = []
    after: str | None = None
    while True:
        params: Dict[str, Any] = {"archived": "false", "limit": 100}
        if after:
            params["after"] = after
        r = _client.get("/crm/v3/owners", params=params)
        r.raise_for_status()
        data = r.json()
        owners.extend(data.get("results", []))
        after = data.get("paging", {}).get("next", {}).get("after")
        if not after:
            break
    agent_ids = [o["id"] for o in owners if "agente" in o.get("email", "").lower()]
    print(f"👥  Found {len(agent_ids)} agente-owners")
    return agent_ids


def _get_or_create_contact_id(phone_number: str) -> str:
    """Return Contact-ID for phone; create contact if missing."""
    _refresh_token_if_needed()
    search = {
        "filterGroups": [{
            "filters": [{
                "propertyName": "phone",
                "operator": "EQ",
                "value": phone_number,
            }]
        }],
        "limit": 1,
    }
    r = _client.post("/crm/v3/objects/contacts/search", json=search)
    r.raise_for_status()
    data = r.json()
    if data["total"]:
        return data["results"][0]["id"]
    body = {"properties": {"phone": phone_number, "firstname": "Contacto"}}
    r = _client.post("/crm/v3/objects/contacts", json=body)
    r.raise_for_status()
    return r.json()["id"]


def _find_open_ticket(contact_id: str) -> str | None:
    """Return newest open ticket-ID for a contact, or None."""
    _refresh_token_if_needed()
    body = {
        "filterGroups": [{
            "filters": [
                {"propertyName": "associations.contact", "operator": "EQ",  "value": contact_id},
                {"propertyName": "hs_pipeline_stage",    "operator": "NEQ", "value": CLOSED_TICKET_STAGE_ID},
            ]
        }],
        "sorts": [{"propertyName": "lastmodifieddate", "direction": "DESCENDING"}],
        "limit": 1,
    }
    r = _client.post("/crm/v3/objects/tickets/search", json=body)
    r.raise_for_status()
    data = r.json()
    if data["total"]:
        return data["results"][0]["id"]
    return None


# ──────────────────────── PUBLIC ENTRY-POINT ──────────────────────────
def escalate_to_human_by_phone(
    phone_number: str,
    agent_user_id: str | None = None,
    *,
    awaiting_stage_id: str = AWAITING_STAGE_DEFAULT,
    internal_note: str | None = "🤖 Bot ceded control – please answer."
) -> Tuple[str, str, str | None]:
    """
    Escalate conversation **and** trigger admin hand-off workflow.

    Returns `(ticket_id, thread_id, task_id)`
    """
    # ── Agent selection ───────────────────────────────────────────────
    if agent_user_id is None:
        agent_ids = _get_agent_ids()
        if not agent_ids:
            raise RuntimeError("No agente users found in HubSpot.")
        agent_user_id = random.choice(agent_ids)
        print(f"🎲  Auto-assigned to agent {agent_user_id}")

    # ── Contact & Ticket ─────────────────────────────────────────────
    contact_id = _get_or_create_contact_id(phone_number)
    ticket_id  = _find_open_ticket(contact_id)
    if ticket_id is None:
        raise RuntimeError(f"No open ticket for contact {contact_id}")

    # Linked conversation thread
    r = _client.get(f"/crm/v3/objects/tickets/{ticket_id}/associations/conversations")
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        raise RuntimeError(f"Ticket {ticket_id} has no conversation attached.")
    thread_id = results[0]["id"]

    # ── 1) Re-open + assign thread ───────────────────────────────────
    _client.patch(
        f"/conversations/v3/conversations/threads/{thread_id}",
        json={"status": "OPEN", "assignedTo": agent_user_id},
    )

    # ── 2) Move ticket stage + owner ─────────────────────────────────
    _client.patch(
        f"/crm/v3/objects/tickets/{ticket_id}",
        json={"properties": {
            "hs_pipeline_stage": awaiting_stage_id,
            "hubspot_owner_id":  agent_user_id,
        }},
    )

    # ── 3) Optional internal note ────────────────────────────────────
    if internal_note:
        _client.post(
            f"/conversations/v3/conversations/threads/{thread_id}/messages",
            json={"recipientField": "AGENT", "text": internal_note},
        )

    # ── 4) High-priority Task  +  admin_responding flags ─────────────
    #     (behaviour copied *verbatim* from your create_handoff_task)
    try:
        # Ensure we know the contact's owner
        r = _client.get(
            f"/crm/v3/objects/contacts/{contact_id}",
            params={"properties": "hubspot_owner_id"},
        )
        r.raise_for_status()
        owner_id = r.json()["properties"].get("hubspot_owner_id") or FALLBACK_OWNER_ID
        if not r.json()["properties"].get("hubspot_owner_id"):
            # Assign fallback owner if contact had none
            _client.patch(
                f"/crm/v3/objects/contacts/{contact_id}",
                json={"properties": {"hubspot_owner_id": owner_id}},
            )

        # Create the task
        due = int((datetime.now(timezone.utc) + timedelta(hours=8)).timestamp() * 1000)
        task_payload = {
            "properties": {
                "hs_task_subject":   "Human assistance requested via Chatbot",
                "hs_task_body":      "The chatbot has requested a human to take over.",
                "hs_task_status":    "NOT_STARTED",
                "hs_task_priority":  "HIGH",
                "hubspot_owner_id":  owner_id,
                "hs_timestamp":      due,
            },
            "associations": [{
                "to":   {"id": contact_id},
                "types": [{
                    "associationCategory": "HUBSPOT_DEFINED",
                    "associationTypeId":   204,
                }],
            }],
        }
        r = _client.post("/crm/v3/objects/tasks", json=task_payload)
        r.raise_for_status()
        task_id = r.json()["id"]

        # Toggle workflow flags on the contact
        ts_ms = str(int(time.time() * 1000))
        _client.patch(
            f"/crm/v3/objects/contacts/{contact_id}",
            json={"properties": {
                "admin_responding":            "true",
                "admin_responding_timestamp":  ts_ms,
            }},
        )
    except httpx.HTTPStatusError as e:
        print(f"⚠️  Task / flag creation failed: {e.response.text}")
        task_id = None

    # ── 5) Handy links ───────────────────────────────────────────────
    if PORTAL_ID:
        print("\n🔗  HubSpot links:")
        print(f"    • Ticket: https://app.hubspot.com/contacts/{PORTAL_ID}/ticket/{ticket_id}")
        print(f"    • Thread: https://app.hubspot.com/inbox/{PORTAL_ID}/view/thread/{thread_id}")
        if task_id:
            print(f"    • Task:   https://app.hubspot.com/contacts/{PORTAL_ID}/task/{task_id}")

    print("✅  Escalation + hand-off complete\n")
    return ticket_id, thread_id, task_id


def escalate_to_human_adk(
    phone_number: str,
    agent_user_id: str = "",          # empty == random agente
    internal_note: str = "🤖 Bot ceded control – please answer.",
) -> dict:
    """
    ADK-friendly wrapper around *escalate_to_human_by_phone*.

    • ADK can't parse Optional/Union annotations, so we use plain `str`
      with an empty-string sentinel.
    • Returns a dict so the assistant can display something useful.
    """
    ticket_id, thread_id, task_id = escalate_to_human_by_phone(
        phone_number,
        agent_user_id or None,        # convert "" → None
        internal_note=internal_note,
    )
    return {
        "ticket_id": ticket_id,
        "thread_id": thread_id,
        "task_id":   task_id,
    }