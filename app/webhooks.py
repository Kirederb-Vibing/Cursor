from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.models import HouseholdSettings

logger = logging.getLogger(__name__)


def item_payload(item) -> dict:
    return {
        "id": item.id,
        "kind": item.kind,
        "name": item.name,
        "amount_ore": item.amount_ore,
        "cadence": item.cadence,
        "charge_rule": item.charge_rule,
        "charge_day": item.charge_day,
        "anchor_month": item.anchor_month,
        "starts_on": item.starts_on.isoformat() if item.starts_on else None,
        "ends_on": item.ends_on.isoformat() if item.ends_on else None,
        "person_id": item.person_id,
        "from_account_id": item.from_account_id,
        "to_account_id": item.to_account_id,
        "category": item.category,
        "notes": item.notes,
        "active": item.active,
        "external_id": item.external_id,
    }


def emit_event(session: Session, event: str, payload: dict) -> None:
    settings = session.get(HouseholdSettings, 1)
    url = (settings.n8n_webhook_url if settings else "") or ""
    if not url.strip():
        return
    body = {
        "event": event,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": "faelleskassen",
        "payload": payload,
    }
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                url.strip(),
                json=body,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — n8n må ikke vælte brugerens gem
        logger.warning("n8n webhook fejlede (%s): %s", event, exc)


def dumps(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)
