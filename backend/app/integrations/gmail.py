import os
import base64
from typing import Optional, List, Dict, Any
from pathlib import Path
import httpx
from pydantic import BaseModel
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request


class GmailConfig(BaseModel):
    credentials_path: Optional[str] = None
    token_path: Optional[str] = None


class Email(BaseModel):
    id: str
    thread_id: str
    subject: str
    sender: str
    recipient: str
    snippet: str
    body: Optional[str] = None
    date: str
    is_unread: bool
    labels: List[str] = []


class GmailClient:
    API_ENDPOINT = "https://gmail.googleapis.com/gmail/v1"
    SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

    def __init__(self, config: Optional[GmailConfig] = None):
        self.config = config or self._load_config_from_env()
        self.credentials = None
        self.client = httpx.AsyncClient()
        self._load_credentials()

    def _load_config_from_env(self) -> GmailConfig:
        return GmailConfig(
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

    async def list_messages(
        self,
        query: Optional[str] = None,
        max_results: int = 10,
        label_ids: Optional[List[str]] = None,
    ) -> List[Email]:
        url = f"{self.API_ENDPOINT}/users/me/messages"
        params = {"maxResults": max_results}

        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = label_ids

        response = await self.client.get(
            url, headers=self._get_headers(), params=params
        )
        response.raise_for_status()

        messages_data = response.json()
        messages = []

        for msg in messages_data.get("messages", []):
            message_detail = await self.get_message(msg["id"])
            if message_detail:
                messages.append(message_detail)

        return messages

    async def get_message(self, message_id: str) -> Optional[Email]:
        url = f"{self.API_ENDPOINT}/users/me/messages/{message_id}"
        params = {"format": "full"}

        response = await self.client.get(
            url, headers=self._get_headers(), params=params
        )
        response.raise_for_status()

        data = response.json()
        headers = {
            h["name"]: h["value"] for h in data.get("payload", {}).get("headers", [])
        }

        snippet = data.get("snippet", "")
        body = self._extract_body(data.get("payload", {}))

        return Email(
            id=data["id"],
            thread_id=data["threadId"],
            subject=headers.get("Subject", "No Subject"),
            sender=headers.get("From", "Unknown"),
            recipient=headers.get("To", "Unknown"),
            snippet=snippet,
            body=body,
            date=headers.get("Date", ""),
            is_unread="UNREAD" in data.get("labelIds", []),
            labels=data.get("labelIds", []),
        )

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        if "body" in payload and payload["body"].get("data"):
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain":
                    if part.get("body", {}).get("data"):
                        return base64.urlsafe_b64decode(part["body"]["data"]).decode(
                            "utf-8"
                        )

        return ""

    async def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        import email.message

        msg = email.message.EmailMessage()
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = ", ".join(cc)
        msg.set_content(body)

        encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

        url = f"{self.API_ENDPOINT}/users/me/messages/send"
        data = {"raw": encoded_message}

        response = await self.client.post(url, headers=self._get_headers(), json=data)
        response.raise_for_status()

        return response.json()

    async def search_messages(self, query: str, max_results: int = 10) -> List[Email]:
        return await self.list_messages(query=query, max_results=max_results)

    async def get_unread_messages(self, max_results: int = 10) -> List[Email]:
        return await self.list_messages(label_ids=["UNREAD"], max_results=max_results)

    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        url = f"{self.API_ENDPOINT}/users/me/messages/{message_id}/modify"
        data = {"removeLabelIds": ["UNREAD"]}

        response = await self.client.post(url, headers=self._get_headers(), json=data)
        response.raise_for_status()

        return response.json()

    async def delete_message(self, message_id: str) -> None:
        url = f"{self.API_ENDPOINT}/users/me/messages/{message_id}"
        response = await self.client.delete(url, headers=self._get_headers())
        response.raise_for_status()

    async def close(self):
        await self.client.aclose()
