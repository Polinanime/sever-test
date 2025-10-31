from typing import Any, Dict, List, Optional
import json
import logging
from datetime import datetime, timedelta

from ..integrations.gmail import GmailClient

logger = logging.getLogger(__name__)


class EmailTools:
    def __init__(self, gmail_client: Optional[GmailClient] = None):
        self.gmail_client = gmail_client or GmailClient()

    def get_function_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "list_emails",
                "description": "List recent emails from inbox",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of emails to return",
                            "default": 10,
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query (e.g., 'from:user@example.com', 'subject:meeting')",
                        },
                    },
                },
            },
            {
                "name": "search_emails",
                "description": "Search emails by query (supports from:, to:, subject:, after:, before:)",
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
                "name": "get_unread_emails",
                "description": "Get unread emails from inbox",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of emails to return",
                            "default": 10,
                        },
                    },
                },
            },
            {
                "name": "send_email",
                "description": "Send an email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email address",
                        },
                        "subject": {
                            "type": "string",
                            "description": "Email subject",
                        },
                        "body": {
                            "type": "string",
                            "description": "Email body content",
                        },
                        "cc": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "CC recipients",
                        },
                    },
                    "required": ["to", "subject", "body"],
                },
            },
            {
                "name": "mark_email_as_read",
                "description": "Mark an email as read",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "Email message ID",
                        },
                    },
                    "required": ["message_id"],
                },
            },
        ]

    async def execute_function(
        self, function_name: str, arguments: Dict[str, Any]
    ) -> str:
        try:
            if function_name == "list_emails":
                return await self._list_emails(**arguments)
            elif function_name == "search_emails":
                return await self._search_emails(**arguments)
            elif function_name == "get_unread_emails":
                return await self._get_unread_emails(**arguments)
            elif function_name == "send_email":
                return await self._send_email(**arguments)
            elif function_name == "mark_email_as_read":
                return await self._mark_email_as_read(**arguments)
            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})
        except Exception as e:
            logger.error(f"Error executing {function_name}: {e}", exc_info=True)
            return json.dumps({"error": str(e)})

    async def _list_emails(
        self, max_results: int = 10, query: Optional[str] = None
    ) -> str:
        emails = await self.gmail_client.list_messages(
            query=query, max_results=max_results
        )

        result = {
            "count": len(emails),
            "emails": [
                {
                    "id": email.id,
                    "subject": email.subject,
                    "sender": email.sender,
                    "date": email.date,
                    "snippet": email.snippet,
                    "is_unread": email.is_unread,
                }
                for email in emails
            ],
        }

        return json.dumps(result, ensure_ascii=False)

    async def _search_emails(self, query: str, max_results: int = 10) -> str:
        emails = await self.gmail_client.search_messages(
            query=query, max_results=max_results
        )

        result = {
            "count": len(emails),
            "query": query,
            "emails": [
                {
                    "id": email.id,
                    "subject": email.subject,
                    "sender": email.sender,
                    "recipient": email.recipient,
                    "date": email.date,
                    "snippet": email.snippet,
                    "is_unread": email.is_unread,
                }
                for email in emails
            ],
        }

        return json.dumps(result, ensure_ascii=False)

    async def _get_unread_emails(self, max_results: int = 10) -> str:
        emails = await self.gmail_client.get_unread_messages(max_results=max_results)

        result = {
            "count": len(emails),
            "emails": [
                {
                    "id": email.id,
                    "subject": email.subject,
                    "sender": email.sender,
                    "date": email.date,
                    "snippet": email.snippet,
                }
                for email in emails
            ],
        }

        return json.dumps(result, ensure_ascii=False)

    async def _send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
    ) -> str:
        response = await self.gmail_client.send_message(
            to=to, subject=subject, body=body, cc=cc
        )

        result = {
            "status": "sent",
            "message_id": response.get("id"),
            "to": to,
            "subject": subject,
        }

        return json.dumps(result, ensure_ascii=False)

    async def _mark_email_as_read(self, message_id: str) -> str:
        await self.gmail_client.mark_as_read(message_id)

        result = {"status": "success", "message_id": message_id}

        return json.dumps(result, ensure_ascii=False)

    async def close(self):
        await self.gmail_client.close()
