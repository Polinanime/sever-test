from typing import Any, Dict, List, Optional
import json
import logging
from datetime import datetime, timedelta

from ..integrations.calendar import GoogleCalendarClient

logger = logging.getLogger(__name__)


class CalendarTools:
    def __init__(self, calendar_client: Optional[GoogleCalendarClient] = None):
        self.calendar_client = calendar_client or GoogleCalendarClient()

    def get_function_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "list_calendar_events",
                "description": "List upcoming calendar events",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of events to return",
                            "default": 10,
                        },
                        "time_min": {
                            "type": "string",
                            "description": "Start date-time (ISO 8601 format)",
                        },
                        "time_max": {
                            "type": "string",
                            "description": "End date-time (ISO 8601 format)",
                        },
                    },
                },
            },
            {
                "name": "search_calendar_events",
                "description": "Search calendar events by query",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "create_calendar_event",
                "description": "Create a new calendar event",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Event title/summary",
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start date-time (ISO 8601 format)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End date-time (ISO 8601 format)",
                        },
                        "description": {
                            "type": "string",
                            "description": "Event description",
                        },
                        "location": {
                            "type": "string",
                            "description": "Event location",
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Attendee email addresses",
                        },
                    },
                    "required": ["summary", "start_time", "end_time"],
                },
            },
            {
                "name": "update_calendar_event",
                "description": "Update an existing calendar event",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {
                            "type": "string",
                            "description": "Event ID",
                        },
                        "summary": {
                            "type": "string",
                            "description": "New event title",
                        },
                        "start_time": {
                            "type": "string",
                            "description": "New start time (ISO 8601)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "New end time (ISO 8601)",
                        },
                        "description": {
                            "type": "string",
                            "description": "New description",
                        },
                        "location": {
                            "type": "string",
                            "description": "New location",
                        },
                    },
                    "required": ["event_id"],
                },
            },
            {
                "name": "delete_calendar_event",
                "description": "Delete a calendar event",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "event_id": {
                            "type": "string",
                            "description": "Event ID to delete",
                        },
                    },
                    "required": ["event_id"],
                },
            },
        ]

    async def execute_function(
        self, function_name: str, arguments: Dict[str, Any]
    ) -> str:
        try:
            if function_name == "list_calendar_events":
                return await self._list_events(**arguments)
            elif function_name == "search_calendar_events":
                return await self._search_events(**arguments)
            elif function_name == "create_calendar_event":
                return await self._create_event(**arguments)
            elif function_name == "update_calendar_event":
                return await self._update_event(**arguments)
            elif function_name == "delete_calendar_event":
                return await self._delete_event(**arguments)
            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})
        except Exception as e:
            logger.error(f"Error executing {function_name}: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    async def _list_events(
        self,
        max_results: int = 10,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None,
    ) -> str:
        events = await self.calendar_client.list_events(
            max_results=max_results, time_min=time_min, time_max=time_max
        )

        result = {
            "count": len(events),
            "events": [
                {
                    "id": event.id,
                    "summary": event.summary,
                    "start_time": event.start_time,
                    "end_time": event.end_time,
                    "location": event.location,
                    "description": event.description,
                    "attendees": event.attendees,
                    "status": event.status,
                }
                for event in events
            ],
        }

        return json.dumps(result, ensure_ascii=False)

    async def _search_events(self, query: str, max_results: int = 10) -> str:
        events = await self.calendar_client.search_events(
            query=query, max_results=max_results
        )

        result = {
            "count": len(events),
            "query": query,
            "events": [
                {
                    "id": event.id,
                    "summary": event.summary,
                    "start_time": event.start_time,
                    "end_time": event.end_time,
                    "location": event.location,
                }
                for event in events
            ],
        }

        return json.dumps(result, ensure_ascii=False)

    async def _create_event(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
    ) -> str:
        response = await self.calendar_client.create_event(
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
            attendees=attendees,
        )

        result = {
            "status": "created",
            "event_id": response.get("id"),
            "summary": summary,
            "start_time": start_time,
            "end_time": end_time,
            "html_link": response.get("htmlLink"),
        }

        return json.dumps(result, ensure_ascii=False)

    async def _update_event(
        self,
        event_id: str,
        summary: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
    ) -> str:
        response = await self.calendar_client.update_event(
            event_id=event_id,
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
        )

        result = {
            "status": "updated",
            "event_id": event_id,
            "html_link": response.get("htmlLink"),
        }

        return json.dumps(result, ensure_ascii=False)

    async def _delete_event(self, event_id: str) -> str:
        await self.calendar_client.delete_event(event_id)

        result = {"status": "deleted", "event_id": event_id}

        return json.dumps(result, ensure_ascii=False)

    async def close(self):
        await self.calendar_client.close()
