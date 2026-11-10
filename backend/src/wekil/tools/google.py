"""Gmail (send + read thread replies) and Google Calendar (due dates, reviews) for Wekil's own mailbox."""

import base64
from datetime import date, timedelta
from email.message import EmailMessage
from functools import lru_cache

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from ..config import settings

MARK = "X-Wekil"  # header on every message Wekil sends, to tell its own messages from replies


@lru_cache
def _svc(name: str, version: str):
    s = settings()
    creds = Credentials(None, refresh_token=s.google_refresh_token, client_id=s.google_client_id,
                        client_secret=s.google_client_secret, token_uri="https://oauth2.googleapis.com/token")
    return build(name, version, credentials=creds, cache_discovery=False)


def enabled() -> bool:
    return bool(settings().google_refresh_token)


def send(to: str, subject: str, body: str, thread_id: str | None = None) -> str | None:
    """Send a plain-text email; returns the Gmail thread id (None when Google isn't configured)."""
    if not enabled():
        return None
    msg = EmailMessage()
    msg["To"], msg["From"], msg["Subject"] = to, f"Wekil Compliance <{settings().agent_email}>", subject
    msg[MARK] = "1"
    if thread_id:
        last = _svc("gmail", "v1").users().threads().get(userId="me", id=thread_id, format="metadata",
                                                         metadataHeaders=["Message-ID"]).execute()["messages"][-1]
        if mid := _header(last, "Message-ID"):
            msg["In-Reply-To"] = msg["References"] = mid
    msg.set_content(body)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    payload = {"raw": raw} | ({"threadId": thread_id} if thread_id else {})
    return _svc("gmail", "v1").users().messages().send(userId="me", body=payload).execute()["threadId"]


def replies(thread_id: str) -> list[dict]:
    """Messages in the thread that Wekil did not send: [{id, from, text}]."""
    if not enabled():
        return []
    thread = _svc("gmail", "v1").users().threads().get(userId="me", id=thread_id, format="full").execute()
    out = []
    for m in thread["messages"]:
        if _header(m, MARK):
            continue
        out.append({"id": m["id"], "from": _header(m, "From"), "text": _text(m["payload"])[:4000]})
    return out


def _header(msg: dict, name: str) -> str | None:
    return next((h["value"] for h in msg["payload"].get("headers", []) if h["name"].lower() == name.lower()), None)


def _text(part: dict) -> str:
    if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
        text = base64.urlsafe_b64decode(part["body"]["data"]).decode(errors="replace")
        return text.split("\nOn ")[0]  # drop the quoted original
    return "".join(_text(p) for p in part.get("parts", []))


def event(title: str, day: date, description: str = "") -> str | None:
    """All-day event on Wekil's calendar; returns the event link."""
    if not enabled():
        return None
    body = {"summary": title, "description": description, "start": {"date": day.isoformat()},
            "end": {"date": (day + timedelta(days=1)).isoformat()},
            "reminders": {"useDefault": False, "overrides": [{"method": "email", "minutes": 9 * 60}]}}
    return _svc("calendar", "v3").events().insert(calendarId="primary", body=body).execute().get("htmlLink")
