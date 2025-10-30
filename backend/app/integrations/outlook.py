"""
Outlook Integration using Microsoft Graph API
Provides functions to interact with Outlook emails, calendar, and contacts
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import httpx
from pydantic import BaseModel


class OutlookConfig(BaseModel):
    """Configuration for Outlook/Microsoft Graph API"""

    client_id: str
    client_secret: str
    tenant_id: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class Email(BaseModel):
    """Email message model"""

    id: str
    subject: str
    sender: str
    received_datetime: str
    body_preview: str
    is_read: bool
    has_attachments: bool


class CalendarEvent(BaseModel):
    """Calendar event model"""

    id: str
    subject: str
    start: str
    end: str
    location: Optional[str] = None
    attendees: List[str] = []
    body_preview: Optional[str] = None


class OutlookClient:
    """Client for interacting with Microsoft Graph API for Outlook"""

    GRAPH_API_ENDPOINT = "https://graph.microsoft.com/v1.0"
    AUTH_ENDPOINT = "https://login.microsoftonline.com"

    def __init__(self, config: Optional[OutlookConfig] = None):
        """Initialize Outlook client with configuration"""
        self.config = config or self._load_config_from_env()
        self.access_token = self.config.access_token
        self.client = httpx.AsyncClient()

    def _load_config_from_env(self) -> OutlookConfig:
        """Load configuration from environment variables"""
        return OutlookConfig(
            client_id=os.getenv("MICROSOFT_CLIENT_ID", ""),
            client_secret=os.getenv("MICROSOFT_CLIENT_SECRET", ""),
            tenant_id=os.getenv("MICROSOFT_TENANT_ID", ""),
            access_token=os.getenv("MICROSOFT_ACCESS_TOKEN"),
            refresh_token=os.getenv("MICROSOFT_REFRESH_TOKEN"),
        )

    async def get_access_token(
        self, authorization_code: str, redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token

        Args:
            authorization_code: OAuth authorization code
            redirect_uri: Redirect URI used in authorization request

        Returns:
            Dictionary containing access_token, refresh_token, etc.
        """
        token_url = f"{self.AUTH_ENDPOINT}/{self.config.tenant_id}/oauth2/v2.0/token"

        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": authorization_code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "scope": "https://graph.microsoft.com/.default",
        }

        response = await self.client.post(token_url, data=data)
        response.raise_for_status()
        token_data = response.json()

        self.access_token = token_data["access_token"]
        self.config.access_token = self.access_token

        return token_data

    async def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh the access token using refresh token

        Returns:
            Dictionary containing new access_token
        """
        if not self.config.refresh_token:
            raise ValueError("No refresh token available")

        token_url = f"{self.AUTH_ENDPOINT}/{self.config.tenant_id}/oauth2/v2.0/token"

        data = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": self.config.refresh_token,
            "grant_type": "refresh_token",
            "scope": "https://graph.microsoft.com/.default",
        }

        response = await self.client.post(token_url, data=data)
        response.raise_for_status()
        token_data = response.json()

        self.access_token = token_data["access_token"]
        self.config.access_token = self.access_token

        return token_data

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Graph API requests"""
        if not self.access_token:
            raise ValueError("No access token available. Please authenticate first.")

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def get_emails(
        self,
        folder: str = "inbox",
        top: int = 10,
        filter_query: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[Email]:
        """
        Get emails from a specific folder

        Args:
            folder: Folder name (inbox, sent, drafts, etc.)
            top: Number of emails to retrieve
            filter_query: OData filter query (e.g., "isRead eq false")
            search_query: Search query string

        Returns:
            List of Email objects
        """
        url = f"{self.GRAPH_API_ENDPOINT}/me/mailFolders/{folder}/messages"

        params = {
            "$top": top,
            "$select": "id,subject,from,receivedDateTime,bodyPreview,isRead,hasAttachments",
            "$orderby": "receivedDateTime DESC",
        }

        if filter_query:
            params["$filter"] = filter_query

        if search_query:
            params["$search"] = f'"{search_query}"'

        response = await self.client.get(
            url, headers=self._get_headers(), params=params
        )
        response.raise_for_status()

        data = response.json()
        emails = []

        for item in data.get("value", []):
            emails.append(
                Email(
                    id=item["id"],
                    subject=item.get("subject", ""),
                    sender=item.get("from", {})
                    .get("emailAddress", {})
                    .get("address", ""),
                    received_datetime=item.get("receivedDateTime", ""),
                    body_preview=item.get("bodyPreview", ""),
                    is_read=item.get("isRead", False),
                    has_attachments=item.get("hasAttachments", False),
                )
            )

        return emails

    async def get_unread_emails(self, top: int = 10) -> List[Email]:
        """Get unread emails from inbox"""
        return await self.get_emails(
            folder="inbox", top=top, filter_query="isRead eq false"
        )

    async def search_emails(self, query: str, top: int = 10) -> List[Email]:
        """
        Search emails

        Args:
            query: Search query string
            top: Number of results to return

        Returns:
            List of matching Email objects
        """
        return await self.get_emails(folder="inbox", top=top, search_query=query)

    async def get_email_details(self, email_id: str) -> Dict[str, Any]:
        """
        Get full details of a specific email

        Args:
            email_id: The email ID

        Returns:
            Full email details
        """
        url = f"{self.GRAPH_API_ENDPOINT}/me/messages/{email_id}"

        response = await self.client.get(url, headers=self._get_headers())
        response.raise_for_status()

        return response.json()

    async def send_email(
        self,
        to_recipients: List[str],
        subject: str,
        body: str,
        body_type: str = "HTML",
        cc_recipients: Optional[List[str]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Send an email

        Args:
            to_recipients: List of recipient email addresses
            subject: Email subject
            body: Email body content
            body_type: Content type ("HTML" or "Text")
            cc_recipients: List of CC email addresses
            attachments: List of attachment dictionaries

        Returns:
            Response from API
        """
        url = f"{self.GRAPH_API_ENDPOINT}/me/sendMail"

        message = {
            "message": {
                "subject": subject,
                "body": {"contentType": body_type, "content": body},
                "toRecipients": [
                    {"emailAddress": {"address": email}} for email in to_recipients
                ],
            }
        }

        if cc_recipients:
            message["message"]["ccRecipients"] = [
                {"emailAddress": {"address": email}} for email in cc_recipients
            ]

        if attachments:
            message["message"]["attachments"] = attachments

        response = await self.client.post(
            url, headers=self._get_headers(), json=message
        )
        response.raise_for_status()

        return {"status": "sent", "message": "Email sent successfully"}

    async def reply_to_email(self, email_id: str, comment: str) -> Dict[str, Any]:
        """
        Reply to an email

        Args:
            email_id: The ID of the email to reply to
            comment: Reply message content

        Returns:
            Response from API
        """
        url = f"{self.GRAPH_API_ENDPOINT}/me/messages/{email_id}/reply"

        data = {"comment": comment}

        response = await self.client.post(url, headers=self._get_headers(), json=data)
        response.raise_for_status()

        return {"status": "sent", "message": "Reply sent successfully"}

    async def mark_as_read(self, email_id: str) -> Dict[str, Any]:
        """
        Mark an email as read

        Args:
            email_id: The email ID

        Returns:
            Response from API
        """
        url = f"{self.GRAPH_API_ENDPOINT}/me/messages/{email_id}"

        data = {"isRead": True}

        response = await self.client.patch(url, headers=self._get_headers(), json=data)
        response.raise_for_status()

        return {"status": "success", "message": "Email marked as read"}

    async def delete_email(self, email_id: str) -> Dict[str, Any]:
        """
        Delete an email

        Args:
            email_id: The email ID

        Returns:
            Response from API
        """
        url = f"{self.GRAPH_API_ENDPOINT}/me/messages/{email_id}"

        response = await self.client.delete(url, headers=self._get_headers())
        response.raise_for_status()

        return {"status": "success", "message": "Email deleted"}

    async def get_calendar_events(
        self,
        start_datetime: Optional[datetime] = None,
        end_datetime: Optional[datetime] = None,
        top: int = 10,
    ) -> List[CalendarEvent]:
        """
        Get calendar events

        Args:
            start_datetime: Start date/time filter
            end_datetime: End date/time filter
            top: Number of events to retrieve

        Returns:
            List of CalendarEvent objects
        """
        url = f"{self.GRAPH_API_ENDPOINT}/me/calendar/events"

        params = {
            "$top": top,
            "$select": "id,subject,start,end,location,attendees,bodyPreview",
            "$orderby": "start/dateTime",
        }

        if start_datetime and end_datetime:
            start_str = start_datetime.isoformat()
            end_str = end_datetime.isoformat()
            params["$filter"] = (
                f"start/dateTime ge '{start_str}' and end/dateTime le '{end_str}'"
            )

        response = await self.client.get(
            url, headers=self._get_headers(), params=params
        )
        response.raise_for_status()

        data = response.json()
        events = []

        for item in data.get("value", []):
            attendees = [
                attendee.get("emailAddress", {}).get("address", "")
                for attendee in item.get("attendees", [])
            ]

            events.append(
                CalendarEvent(
                    id=item["id"],
                    subject=item.get("subject", ""),
                    start=item.get("start", {}).get("dateTime", ""),
                    end=item.get("end", {}).get("dateTime", ""),
                    location=item.get("location", {}).get("displayName"),
                    attendees=attendees,
                    body_preview=item.get("bodyPreview"),
                )
            )

        return events

    async def get_today_events(self) -> List[CalendarEvent]:
        """Get today's calendar events"""
        now = datetime.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        return await self.get_calendar_events(
            start_datetime=start_of_day, end_datetime=end_of_day
        )

    async def create_calendar_event(
        self,
        subject: str,
        start_datetime: datetime,
        end_datetime: datetime,
        location: Optional[str] = None,
        attendees: Optional[List[str]] = None,
        body: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a calendar event

        Args:
            subject: Event subject
            start_datetime: Event start time
            end_datetime: Event end time
            location: Event location
            attendees: List of attendee email addresses
            body: Event description

        Returns:
            Created event details
        """
        url = f"{self.GRAPH_API_ENDPOINT}/me/calendar/events"

        event_data = {
            "subject": subject,
            "start": {"dateTime": start_datetime.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_datetime.isoformat(), "timeZone": "UTC"},
        }

        if location:
            event_data["location"] = {"displayName": location}

        if attendees:
            event_data["attendees"] = [
                {"emailAddress": {"address": email}, "type": "required"}
                for email in attendees
            ]

        if body:
            event_data["body"] = {"contentType": "HTML", "content": body}

        response = await self.client.post(
            url, headers=self._get_headers(), json=event_data
        )
        response.raise_for_status()

        return response.json()

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
