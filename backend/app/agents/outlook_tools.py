"""
Outlook Tools for OpenAI Realtime Agents
Provides function definitions and handlers for Outlook integration
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import json
import logging

from ..integrations.outlook import OutlookClient, OutlookConfig

logger = logging.getLogger(__name__)


class OutlookTools:
    """Tools for Outlook integration with OpenAI agents"""

    def __init__(self, outlook_client: Optional[OutlookClient] = None):
        """Initialize Outlook tools with a client"""
        self.outlook_client = outlook_client or OutlookClient()

    def get_function_definitions(self) -> List[Dict[str, Any]]:
        """
        Get OpenAI function definitions for Outlook tools

        Returns:
            List of function definition dictionaries for OpenAI API
        """
        return [
            {
                "type": "function",
                "name": "get_unread_emails",
                "description": "Get unread emails from the user's inbox. Returns the most recent unread emails with sender, subject, and preview.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of unread emails to retrieve",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        }
                    },
                },
            },
            {
                "type": "function",
                "name": "get_recent_emails",
                "description": "Get recent emails from the user's inbox, including both read and unread messages.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "count": {
                            "type": "integer",
                            "description": "Number of emails to retrieve",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        }
                    },
                },
            },
            {
                "type": "function",
                "name": "search_emails",
                "description": "Search for emails by keyword or phrase in the user's mailbox. Searches in subject, body, and sender fields.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to find emails",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 10,
                            "minimum": 1,
                            "maximum": 50,
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "type": "function",
                "name": "get_email_details",
                "description": "Get the full content and details of a specific email by its ID. Use this to read the complete email body.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "The unique identifier of the email",
                        }
                    },
                    "required": ["email_id"],
                },
            },
            {
                "type": "function",
                "name": "send_email",
                "description": "Send a new email to one or more recipients. Can include HTML formatting and CC recipients.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of recipient email addresses",
                        },
                        "subject": {
                            "type": "string",
                            "description": "The email subject line",
                        },
                        "body": {
                            "type": "string",
                            "description": "The email body content (can include HTML)",
                        },
                        "cc": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional list of CC recipient email addresses",
                        },
                    },
                    "required": ["to", "subject", "body"],
                },
            },
            {
                "type": "function",
                "name": "reply_to_email",
                "description": "Reply to an existing email. The reply will be sent to the original sender and include the original message thread.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "The ID of the email to reply to",
                        },
                        "message": {
                            "type": "string",
                            "description": "The reply message content",
                        },
                    },
                    "required": ["email_id", "message"],
                },
            },
            {
                "type": "function",
                "name": "mark_email_as_read",
                "description": "Mark a specific email as read in the user's mailbox.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "The ID of the email to mark as read",
                        }
                    },
                    "required": ["email_id"],
                },
            },
            {
                "type": "function",
                "name": "delete_email",
                "description": "Delete a specific email from the user's mailbox. Use with caution as this action cannot be undone.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email_id": {
                            "type": "string",
                            "description": "The ID of the email to delete",
                        }
                    },
                    "required": ["email_id"],
                },
            },
            {
                "type": "function",
                "name": "get_today_calendar",
                "description": "Get all calendar events scheduled for today. Returns event details including time, location, and attendees.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "type": "function",
                "name": "get_calendar_events",
                "description": "Get calendar events within a specific date range. Useful for checking availability or upcoming meetings.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date in ISO format (YYYY-MM-DD) or relative like 'today', 'tomorrow'",
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in ISO format (YYYY-MM-DD) or relative like 'today', 'tomorrow'",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Maximum number of events to return",
                            "default": 20,
                            "minimum": 1,
                            "maximum": 100,
                        },
                    },
                    "required": ["start_date", "end_date"],
                },
            },
            {
                "type": "function",
                "name": "create_calendar_event",
                "description": "Create a new calendar event or meeting. Can include attendees, location, and description.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "The event or meeting subject/title",
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS)",
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time in ISO format (YYYY-MM-DDTHH:MM:SS)",
                        },
                        "location": {
                            "type": "string",
                            "description": "Event location (can be physical location or meeting link)",
                        },
                        "attendees": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of attendee email addresses",
                        },
                        "description": {
                            "type": "string",
                            "description": "Event description or meeting agenda",
                        },
                    },
                    "required": ["subject", "start_time", "end_time"],
                },
            },
        ]

    async def execute_function(
        self, function_name: str, arguments: Dict[str, Any]
    ) -> str:
        """
        Execute a function call from the agent

        Args:
            function_name: Name of the function to execute
            arguments: Dictionary of function arguments

        Returns:
            JSON string with function result
        """
        try:
            logger.info(f"Executing function: {function_name} with args: {arguments}")

            # Email functions
            if function_name == "get_unread_emails":
                return await self._get_unread_emails(arguments.get("count", 10))

            elif function_name == "get_recent_emails":
                return await self._get_recent_emails(arguments.get("count", 10))

            elif function_name == "search_emails":
                return await self._search_emails(
                    arguments["query"], arguments.get("count", 10)
                )

            elif function_name == "get_email_details":
                return await self._get_email_details(arguments["email_id"])

            elif function_name == "send_email":
                return await self._send_email(
                    arguments["to"],
                    arguments["subject"],
                    arguments["body"],
                    arguments.get("cc"),
                )

            elif function_name == "reply_to_email":
                return await self._reply_to_email(
                    arguments["email_id"], arguments["message"]
                )

            elif function_name == "mark_email_as_read":
                return await self._mark_email_as_read(arguments["email_id"])

            elif function_name == "delete_email":
                return await self._delete_email(arguments["email_id"])

            # Calendar functions
            elif function_name == "get_today_calendar":
                return await self._get_today_calendar()

            elif function_name == "get_calendar_events":
                return await self._get_calendar_events(
                    arguments["start_date"],
                    arguments["end_date"],
                    arguments.get("count", 20),
                )

            elif function_name == "create_calendar_event":
                return await self._create_calendar_event(
                    arguments["subject"],
                    arguments["start_time"],
                    arguments["end_time"],
                    arguments.get("location"),
                    arguments.get("attendees"),
                    arguments.get("description"),
                )

            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})

        except Exception as e:
            logger.error(f"Error executing {function_name}: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    # Email tool implementations
    async def _get_unread_emails(self, count: int) -> str:
        """Get unread emails"""
        emails = await self.outlook_client.get_unread_emails(top=count)
        result = {
            "count": len(emails),
            "emails": [
                {
                    "id": email.id,
                    "subject": email.subject,
                    "sender": email.sender,
                    "received": email.received_datetime,
                    "preview": email.body_preview,
                }
                for email in emails
            ],
        }
        return json.dumps(result)

    async def _get_recent_emails(self, count: int) -> str:
        """Get recent emails"""
        emails = await self.outlook_client.get_emails(top=count)
        result = {
            "count": len(emails),
            "emails": [
                {
                    "id": email.id,
                    "subject": email.subject,
                    "sender": email.sender,
                    "received": email.received_datetime,
                    "preview": email.body_preview,
                    "is_read": email.is_read,
                }
                for email in emails
            ],
        }
        return json.dumps(result)

    async def _search_emails(self, query: str, count: int) -> str:
        """Search emails"""
        emails = await self.outlook_client.search_emails(query=query, top=count)
        result = {
            "query": query,
            "count": len(emails),
            "emails": [
                {
                    "id": email.id,
                    "subject": email.subject,
                    "sender": email.sender,
                    "received": email.received_datetime,
                    "preview": email.body_preview,
                }
                for email in emails
            ],
        }
        return json.dumps(result)

    async def _get_email_details(self, email_id: str) -> str:
        """Get full email details"""
        email = await self.outlook_client.get_email_details(email_id)
        result = {
            "id": email.get("id"),
            "subject": email.get("subject"),
            "sender": email.get("from", {}).get("emailAddress", {}).get("address"),
            "received": email.get("receivedDateTime"),
            "body": email.get("body", {}).get("content"),
            "body_type": email.get("body", {}).get("contentType"),
            "is_read": email.get("isRead"),
            "has_attachments": email.get("hasAttachments"),
        }
        return json.dumps(result)

    async def _send_email(
        self,
        to: List[str],
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
    ) -> str:
        """Send an email"""
        result = await self.outlook_client.send_email(
            to_recipients=to,
            subject=subject,
            body=body,
            cc_recipients=cc,
        )
        return json.dumps(result)

    async def _reply_to_email(self, email_id: str, message: str) -> str:
        """Reply to an email"""
        result = await self.outlook_client.reply_to_email(email_id, message)
        return json.dumps(result)

    async def _mark_email_as_read(self, email_id: str) -> str:
        """Mark email as read"""
        result = await self.outlook_client.mark_as_read(email_id)
        return json.dumps(result)

    async def _delete_email(self, email_id: str) -> str:
        """Delete an email"""
        result = await self.outlook_client.delete_email(email_id)
        return json.dumps(result)

    # Calendar tool implementations
    async def _get_today_calendar(self) -> str:
        """Get today's calendar events"""
        events = await self.outlook_client.get_today_events()
        result = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "count": len(events),
            "events": [
                {
                    "id": event.id,
                    "subject": event.subject,
                    "start": event.start,
                    "end": event.end,
                    "location": event.location,
                    "attendees": event.attendees,
                }
                for event in events
            ],
        }
        return json.dumps(result)

    async def _get_calendar_events(
        self, start_date: str, end_date: str, count: int
    ) -> str:
        """Get calendar events in date range"""
        # Parse dates (handle relative dates like 'today', 'tomorrow')
        start_dt = self._parse_date(start_date)
        end_dt = self._parse_date(end_date)

        events = await self.outlook_client.get_calendar_events(
            start_datetime=start_dt,
            end_datetime=end_dt,
            top=count,
        )

        result = {
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
            "count": len(events),
            "events": [
                {
                    "id": event.id,
                    "subject": event.subject,
                    "start": event.start,
                    "end": event.end,
                    "location": event.location,
                    "attendees": event.attendees,
                }
                for event in events
            ],
        }
        return json.dumps(result)

    async def _create_calendar_event(
        self,
        subject: str,
        start_time: str,
        end_time: str,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> str:
        """Create a calendar event"""
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)

        result = await self.outlook_client.create_calendar_event(
            subject=subject,
            start_datetime=start_dt,
            end_datetime=end_dt,
            location=location,
            attendees=attendees,
            body=description,
        )

        return json.dumps(
            {
                "status": "created",
                "event_id": result.get("id"),
                "subject": result.get("subject"),
                "start": result.get("start", {}).get("dateTime"),
                "end": result.get("end", {}).get("dateTime"),
            }
        )

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string, handling relative dates"""
        date_str_lower = date_str.lower()

        if date_str_lower == "today":
            return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        elif date_str_lower == "tomorrow":
            return (datetime.now() + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif date_str_lower == "yesterday":
            return (datetime.now() - timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            # Try to parse as ISO format
            try:
                return datetime.fromisoformat(date_str)
            except ValueError:
                # Try date only format
                return datetime.strptime(date_str, "%Y-%m-%d")

    async def close(self):
        """Close the Outlook client"""
        await self.outlook_client.close()
