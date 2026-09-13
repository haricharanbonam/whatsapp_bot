import os
from datetime import datetime, time, timedelta, timezone
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.core.config import settings

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]


def _build_calendar_service():
    creds = None
    token_path = settings.GOOGLE_TOKEN_PATH
    credentials_path = settings.GOOGLE_CREDENTIALS_PATH

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def _parse_datetime(event: dict) -> Optional[datetime]:
    dt = event.get("start", {}).get("dateTime")
    if dt:
        return datetime.fromisoformat(dt.replace("Z", "+00:00"))
    date_only = event.get("start", {}).get("date")
    if date_only:
        return datetime.fromisoformat(date_only)
    return None


def fetch_daily_events(date: Optional[str] = None) -> list[dict]:
    service = _build_calendar_service()
    if date:
        search_date = datetime.fromisoformat(date)
    else:
        search_date = datetime.now()

    day_start = search_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    result = (service.events().list(
        calendarId=settings.GOOGLE_CALENDAR_ID,
        timeMin=day_start.isoformat() + "Z",
        timeMax=day_end.isoformat() + "Z",
        singleEvents=True,
        orderBy="startTime",
    ).execute())

    return result.get("items", [])


def format_events_message(events: list[dict], date: Optional[str] = None) -> str:
    if not events:
        return "No events on your Google Calendar today."

    lines = [f"📅 Today's schedule{f' ({date})' if date else ''}:"]
    for idx, event in enumerate(events, start=1):
        start_dt = _parse_datetime(event)
        time_str = start_dt.strftime("%I:%M %p") if start_dt else "All day"
        summary = event.get("summary", "Untitled")
        location = event.get("location")
        loc_str = f" 📍 {location}" if location else ""
        lines.append(f"{idx}. {time_str} - {summary}{loc_str}")

    return "\n".join(lines)


def today_events_message() -> str:
    events = fetch_daily_events()
    return format_events_message(events)