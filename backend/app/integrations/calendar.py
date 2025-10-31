import os
from typing import Optional, List, Dict, Any
from pathlib import Path
import httpx
from pydantic import BaseModel
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


class CalendarConfig(BaseModel):
    credentials_path: Optional[str] = None
    token_path: Optional[str] = None


class CalendarEvent(BaseModel):
    id: str
    summary: str
    description: Optional[str] = None
    start_time: str
    end_time: str
    location: Optional[str] = None
    attendees: List[str] = []
    status: str
    html_link: str


class GoogleCalendarClient:
    API_ENDPOINT = "https://www.googleapis.com/calendar/v3"
    SCOPES = ["https://www.googleapis.com/auth/calendar"]

    def __init__(self, config: Optional[CalendarConfig] = None):
        self.config = config or self._load_config_from_env()
        self.credentials = None
        self.client = httpx.AsyncClient()
        self._load_credentials()

    def _load_config_from_env(self) -> CalendarConfig:
        return CalendarConfig(
            credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json"),
            token_path=os.getenv("GOOGLE_TOKEN_PATH", "token.json"),
        )

    def _load_credentials(self):
        token_path = Path(self.config.token_path)

        if token_path.exists():
            self.credentials = Credentials.from_authorized_user_file(
                str(token_path), self.SCOPES
            )

        if (
            self.credentials
            and self.credentials.expired
            and self.credentials.refresh_token
        ):
            self.credentials.refresh(Request())
            with open(token_path, "w") as token:
                token.write(self.credentials.to_json())

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.credentials and self.credentials.token:
            headers["Authorization"] = f"Bearer {self.credentials.token}"
        return headers

    async def list_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
        max_results: int = 10,
        query: Optional[str] = None,
    ) -> List[CalendarEvent]:
        url = f"{self.API_ENDPOINT}/calendars/{calendar_id}/events"
        params = {
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }

        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        if query:
            params["q"] = query

        response = await self.client.get(
            url, headers=self._get_headers(), params=params
        )
        response.raise_for_status()

        data = response.json()
        events = []

        for item in data.get("items", []):
            start = item.get("start", {})
            end = item.get("end", {})

            events.append(
                CalendarEvent(
                    id=item["id"],
                    summary=item.get("summary", "No Title"),
                    description=item.get("description"),
                    start_time=start.get("dateTime", start.get("date", "")),
                    end_time=end.get("dateTime", end.get("date", "")),
                    location=item.get("location"),
                    attendees=[
                        attendee.get("email", "")
                        for attendee in item.get("attendees", [])
                    ],
                    status=item.get("status", "confirmed"),
                    html_link=item.get("htmlLink", ""),
                )
            )

        return events

    async def get_event(
        self, event_id: str, calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        url = f"{self.API_ENDPOINT}/calendars/{calendar_id}/events/{event_id}"
        response = await self.client.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    async def create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        calendar_id: str = "primary",
    ) -> Dict[str, Any]:
        url = f"{self.API_ENDPOINT}/calendars/{calendar_id}/events"

        event_data = {
            "summary": summary,
            "start": {"dateTime": start_time, "timeZone": "UTC"},
            "end": {"dateTime": end_time, "timeZone": "UTC"},
        }

        if description:
            event_data["description"] = description
        if location:
            event_data["location"] = location
        if attendees:
            event_data["attendees"] = [{"email": email} for email in attendees]

        response = await self.client.post(
            url, headers=self._get_headers(), json=event_data
        )
        response.raise_for_status()

        return response.json()

    async def update_event(
        self,
        event_id: str,
        summary: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        calendar_id: str = "primary",
    ) -> Dict[str, Any]:
        url = f"{self.API_ENDPOINT}/calendars/{calendar_id}/events/{event_id}"

        event_data = {}
        if summary:
            event_data["summary"] = summary
        if start_time:
            event_data["start"] = {"dateTime": start_time, "timeZone": "UTC"}
        if end_time:
            event_data["end"] = {"dateTime": end_time, "timeZone": "UTC"}
        if description is not None:
            event_data["description"] = description
        if location is not None:
            event_data["location"] = location

        response = await self.client.patch(
            url, headers=self._get_headers(), json=event_data
        )
        response.raise_for_status()

        return response.json()

    async def delete_event(self, event_id: str, calendar_id: str = "primary") -> None:
        url = f"{self.API_ENDPOINT}/calendars/{calendar_id}/events/{event_id}"
        response = await self.client.delete(url, headers=self._get_headers())
        response.raise_for_status()

    async def search_events(
        self,
        query: str,
        calendar_id: str = "primary",
        max_results: int = 10,
    ) -> List[CalendarEvent]:
        return await self.list_events(
            calendar_id=calendar_id, query=query, max_results=max_results
        )

    async def close(self):
        await self.client.aclose()
