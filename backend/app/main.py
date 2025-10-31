import asyncio
import base64
import json
import logging
import struct
import os
from typing import Any
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from agents.realtime import (
    RealtimeRunner,
    RealtimeSession,
    RealtimeSessionEvent,
    RealtimeAgent,
)
from agents.tool import FunctionTool
from typing_extensions import assert_never

from .agents.email_tools import EmailTools
from .agents.calendar_tools import CalendarTools

from google_auth_oauthlib.flow import Flow

INSTRUCTIONS = """
You are a helpful AI assistant with access to user's email, and calendar.
You can help manage emails, calendar events.

Available capabilities:

Email:
- List and search emails
- Send emails
- Mark emails as read
- Get unread messages

Calendar:
- List upcoming events
- Create new events
- Update existing events
- Search events

Always confirm with the user before:
- Sending emails
- Creating calendar events

Be helpful, concise, and professional in your responses.
Make sure, your voice AND text are well understandable.
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
]

REDIRECT_URI = "http://localhost:8000/auth/google/callback"


class ContextManager:
    def __init__(self, context_file: str = "data/conversation_context.json"):
        self.context_file = Path(context_file)

    def save_context(
        self, history: list[dict[str, Any]], metadata: dict[str, Any] = None
    ):
        try:
            context_data = {
                "saved_at": datetime.now().isoformat(),
                "metadata": metadata or {},
                "history": history,
            }

            with open(self.context_file, "w") as f:
                json.dump(context_data, f, indent=2, default=str)

            logger.info(f"Context saved successfully to {self.context_file}")
        except Exception as e:
            logger.error(f"Failed to save context: {e}", exc_info=True)

    def load_context(self) -> dict[str, Any] | None:
        try:
            if not self.context_file.exists():
                logger.info("No saved context found")
                return None

            with open(self.context_file, "r") as f:
                context_data = json.load(f)

            logger.info(f"Context loaded successfully from {self.context_file}")
            return context_data
        except Exception as e:
            logger.error(f"Failed to load context: {e}", exc_info=True)
            return None

    def clear_context(self):
        try:
            if self.context_file.exists():
                self.context_file.unlink()
                logger.info("Context cleared successfully")
        except Exception as e:
            logger.error(f"Failed to clear context: {e}", exc_info=True)


class RealtimeWebSocketManager:
    def __init__(self):
        self.active_sessions: dict[str, RealtimeSession] = {}
        self.session_contexts: dict[str, Any] = {}
        self.websockets: dict[str, WebSocket] = {}
        self.email_tools: dict[str, EmailTools] = {}
        self.calendar_tools: dict[str, CalendarTools] = {}
        self.context_manager = ContextManager()
        self.current_history: list[dict[str, Any]] = []

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.websockets[session_id] = websocket
        logger.info(f"Client connected: {session_id}")

        email_tools = EmailTools()
        calendar_tools = CalendarTools()

        self.email_tools[session_id] = email_tools
        self.calendar_tools[session_id] = calendar_tools

        tools = []

        for func_def in email_tools.get_function_definitions():
            func_name = func_def["name"]

            def create_handler(tool_instance=email_tools, name=func_name):
                async def handler(context, arguments_json):
                    args = json.loads(arguments_json)
                    result = await tool_instance.execute_function(name, args)
                    return result

                return handler

            tool = FunctionTool(
                name=func_def["name"],
                description=func_def["description"],
                params_json_schema=func_def["parameters"],
                on_invoke_tool=create_handler(),
            )
            tools.append(tool)

        for func_def in calendar_tools.get_function_definitions():
            func_name = func_def["name"]

            def create_handler(tool_instance=calendar_tools, name=func_name):
                async def handler(context, arguments_json):
                    args = json.loads(arguments_json)
                    result = await tool_instance.execute_function(name, args)
                    return result

                return handler

            tool = FunctionTool(
                name=func_def["name"],
                description=func_def["description"],
                params_json_schema=func_def["parameters"],
                on_invoke_tool=create_handler(),
            )
            tools.append(tool)

        agent = RealtimeAgent(
            name="Assistant",
            instructions=INSTRUCTIONS,
            tools=tools,
        )

        runner = RealtimeRunner(
            agent,
            config={
                "model_settings": {
                    "model_name": "gpt-realtime-mini",
                    "voice": "ash",
                    "modalities": ["audio", "text"],
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "input_audio_transcription": {"model": "gpt-4o-mini-transcribe"},
                    "turn_detection": {
                        "type": "semantic_vad",
                        "interrupt_response": True,
                    },
                }
            },
        )

        session_context = await runner.run()
        session = await session_context.__aenter__()

        self.active_sessions[session_id] = session
        self.session_contexts[session_id] = session_context

        asyncio.create_task(self._process_events(session_id))
        logger.info(f"Session started: {session_id}")

        saved_context = self.context_manager.load_context()
        if saved_context and saved_context.get("history"):
            self.current_history = saved_context["history"]
            logger.info(
                f"Loaded {len(self.current_history)} history items from previous session"
            )

            try:
                await websocket.send_text(
                    json.dumps(
                        {"type": "history_loaded", "history": self.current_history}
                    )
                )
            except Exception as e:
                logger.error(f"Failed to send loaded history: {e}")

            context_summary = self._build_context_summary(self.current_history)
            if context_summary:
                logger.info(
                    f"Sending context summary to OpenAI: {context_summary[:100]}..."
                )
                await session.send_message(context_summary)

    async def disconnect(self, session_id: str):
        if self.current_history:
            self.context_manager.save_context(
                self.current_history,
                metadata={
                    "session_id": session_id,
                    "disconnected_at": datetime.now().isoformat(),
                },
            )

        if session_id in self.session_contexts:
            await self.session_contexts[session_id].__aexit__(None, None, None)
            del self.session_contexts[session_id]
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.websockets:
            del self.websockets[session_id]
        if session_id in self.email_tools:
            await self.email_tools[session_id].close()
            del self.email_tools[session_id]
        if session_id in self.calendar_tools:
            await self.calendar_tools[session_id].close()
            del self.calendar_tools[session_id]
        logger.info(f"Session disconnected: {session_id}")

    async def send_audio(self, session_id: str, audio_bytes: bytes):
        if session_id in self.active_sessions:
            await self.active_sessions[session_id].send_audio(audio_bytes)

    async def send_message(self, session_id: str, message: str):
        if session_id in self.active_sessions:
            await self.active_sessions[session_id].send_message(message)

    async def interrupt(self, session_id: str):
        if session_id in self.active_sessions:
            await self.active_sessions[session_id].interrupt()

    def _build_context_summary(self, history: list[dict[str, Any]]) -> str:
        messages = []
        for item in history:
            if item.get("type") == "message" and item.get("content"):
                role = item.get("role", "unknown")
                texts = []
                for content_item in item["content"]:
                    if isinstance(content_item, dict):
                        text = content_item.get("text") or content_item.get(
                            "transcript"
                        )
                        if text:
                            texts.append(text)
                if texts:
                    combined_text = " ".join(texts)
                    messages.append(f"{role}: {combined_text}")

        if not messages:
            return ""

        summary = "Previous conversation context:\n" + "\n".join(messages[-10:])
        return summary

    async def _process_events(self, session_id: str):
        try:
            session = self.active_sessions.get(session_id)
            websocket = self.websockets.get(session_id)

            if not session or not websocket:
                return

            async for event in session:
                event_data = await self._serialize_event(event)
                await websocket.send_text(json.dumps(event_data))

        except Exception as e:
            logger.error(
                f"Error processing events for session {session_id}: {e}", exc_info=True
            )

    async def _serialize_event(self, event: RealtimeSessionEvent) -> dict[str, Any]:
        base_event: dict[str, Any] = {
            "type": event.type,
        }

        if event.type == "agent_start":
            base_event["agent"] = event.agent.name
        elif event.type == "agent_end":
            base_event["agent"] = event.agent.name
        elif event.type == "handoff":
            base_event["from"] = event.from_agent.name
            base_event["to"] = event.to_agent.name
        elif event.type == "tool_start":
            base_event["tool"] = event.tool.name
            base_event["tool_call_id"] = getattr(event, "tool_call_id", None)
        elif event.type == "tool_end":
            base_event["tool"] = event.tool.name
            base_event["output"] = str(event.output)
            base_event["tool_call_id"] = getattr(event, "tool_call_id", None)
        elif event.type == "audio":
            base_event["audio"] = base64.b64encode(event.audio.data).decode("utf-8")
            base_event["item_id"] = event.item_id
        elif event.type == "audio_interrupted":
            base_event["item_id"] = event.item_id
        elif event.type == "audio_end":
            base_event["item_id"] = event.item_id
        elif event.type == "history_updated":
            base_event["history"] = [item.model_dump() for item in event.history]

            self.current_history = base_event["history"]

            if event.history:
                last_item = event.history[-1]
                if hasattr(last_item, "role") and last_item.role == "assistant":
                    text_parts = []
                    if hasattr(last_item, "content") and last_item.content:
                        for content_item in last_item.content:
                            if hasattr(content_item, "text") and content_item.text:
                                text_parts.append(content_item.text)
                            elif (
                                hasattr(content_item, "transcript")
                                and content_item.transcript
                            ):
                                text_parts.append(content_item.transcript)
                    if text_parts:
                        final_text = " ".join(text_parts)
                        base_event["last_assistant_message"] = final_text
                        logger.info(f"Last assistant message: {final_text}")
        elif event.type == "history_added":
            base_event["item"] = event.item.model_dump()
            if hasattr(event.item, "content") and event.item.content:
                text_parts = []
                for content_item in event.item.content:
                    if hasattr(content_item, "text") and content_item.text:
                        text_parts.append(content_item.text)
                    elif (
                        hasattr(content_item, "transcript") and content_item.transcript
                    ):
                        text_parts.append(content_item.transcript)
                if text_parts:
                    base_event["text"] = " ".join(text_parts)
        elif event.type == "guardrail_tripped":
            base_event["message"] = event.message
        elif event.type == "raw_model_event":
            base_event["raw_event"] = event.data.type

            if event.data.type == "transcript_delta":
                delta = None
                transcript = None
                item_id = None

                if hasattr(event.data, "delta"):
                    delta = event.data.delta

                if hasattr(event.data, "transcript"):
                    transcript = event.data.transcript

                if hasattr(event.data, "item_id"):
                    item_id = event.data.item_id

                if not delta or not transcript:
                    event_dict = (
                        event.data.model_dump()
                        if hasattr(event.data, "model_dump")
                        else {}
                    )

                    if not delta:
                        delta = event_dict.get("delta", "")
                    if not transcript:
                        transcript = event_dict.get("transcript", "")
                    if not item_id:
                        item_id = event_dict.get("item_id", "")

                if not delta and isinstance(event.data, dict):
                    delta = event.data.get("delta", "")
                    transcript = event.data.get("transcript", "")
                    item_id = event.data.get("item_id", "")

                if delta:
                    base_event["delta"] = delta
                    base_event["type"] = "response.audio_transcript.delta"
                if transcript:
                    base_event["transcript"] = transcript
                if item_id:
                    base_event["item_id"] = item_id

            elif event.data.type == "transcript_done":
                transcript = None
                item_id = None

                if hasattr(event.data, "transcript"):
                    transcript = event.data.transcript

                if hasattr(event.data, "item_id"):
                    item_id = event.data.item_id

                if not transcript:
                    event_dict = (
                        event.data.model_dump()
                        if hasattr(event.data, "model_dump")
                        else {}
                    )

                    if not transcript:
                        transcript = event_dict.get("transcript", "")
                    if not item_id:
                        item_id = event_dict.get("item_id", "")

                if not transcript and isinstance(event.data, dict):
                    transcript = event.data.get("transcript", "")
                    item_id = event.data.get("item_id", "")

                if transcript:
                    base_event["transcript"] = transcript
                    base_event["type"] = "response.audio_transcript.done"
                    base_event["text"] = transcript
                if item_id:
                    base_event["item_id"] = item_id

            else:
                logger.info(
                    f"🔍 Other raw_model_event type: {event.data.type}, attributes: {dir(event.data) if hasattr(event.data, '__dir__') else 'N/A'}"
                )
        elif event.type == "error":
            base_event["error"] = (
                str(event.error) if hasattr(event, "error") else "Unknown error"
            )
        elif event.type == "input_audio_timeout_triggered":
            pass
        else:
            assert_never(event)

        return base_event


manager = RealtimeWebSocketManager()


@app.get("/")
async def root():
    return HTMLResponse(
        content="""
    <!DOCTYPE html>
    <html>
        <head>
            <title>AI Agent</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                }
                .status {
                    padding: 10px;
                    margin: 10px 0;
                    border-radius: 5px;
                }
                .success {
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    color: #155724;
                }
                .error {
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    color: #721c24;
                }
                button {
                    background-color: #007bff;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                }
                button:hover {
                    background-color: #0056b3;
                }
            </style>
        </head>
        <body>
            <h1>AI Agent Server</h1>
            <p>Status: Running ✓</p>
            <p>WebSocket endpoint: <code>ws://localhost:8000/ws/realtime</code></p>
            <hr>
            <h2>Google Authentication</h2>
            <button onclick="window.location.href='/auth/google'">
                Authenticate with Google
            </button>
            <button onclick="window.location.href='http://localhost:3000'">
                Go to UI
            </button>
        </body>
    </html>
    """
    )


@app.get("/auth/google")
async def auth_google(request: Request):
    credentials_path = Path("credentials.json")
    if not credentials_path.exists():
        return HTMLResponse(
            content="<h1>Error: credentials.json not found</h1>"
            "<p>Please download your OAuth 2.0 credentials from Google Cloud Console</p>"
        )

    flow = Flow.from_client_secrets_file(
        "credentials.json",
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )

    return RedirectResponse(url=authorization_url)


@app.get("/auth/google/callback")
async def auth_google_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return HTMLResponse(content="<h1>Error: No authorization code received</h1>")

    try:
        flow = Flow.from_client_secrets_file(
            "credentials.json",
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
        )

        flow.fetch_token(code=code)

        credentials = flow.credentials

        token_data = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
        }

        with open("token.json", "w") as token_file:
            json.dump(token_data, token_file)

        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html>
                <head>
                    <title>Authentication Success</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            max-width: 600px;
                            margin: 50px auto;
                            padding: 20px;
                            text-align: center;
                        }
                        .success {
                            background-color: #d4edda;
                            border: 1px solid #c3e6cb;
                            color: #155724;
                            padding: 20px;
                            border-radius: 5px;
                            margin: 20px 0;
                        }
                    </style>
                </head>
                <body>
                    <h1>✓ Authentication Successful</h1>
                    <div class="success">
                        <p>Your Google account has been successfully linked!</p>
                        <p>You can now use email and calendar features.</p>
                    </div>
                    <p>You can close this window and return to the application.</p>
                </body>
            </html>
            """
        )

    except Exception as e:
        logger.error(f"Error during OAuth callback: {e}", exc_info=True)
        return HTMLResponse(
            content=f"<h1>Error during authentication</h1><p>{str(e)}</p>"
        )


@app.websocket("/ws/realtime")
async def realtime_proxy(websocket: WebSocket):
    # session_id = f"session_{id(websocket)}"
    session_id = f"session_1"  # Do not create new session every time

    await manager.connect(websocket, session_id)

    try:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "debug_text",
                    "text": "WebSocket connected - text path working",
                }
            )
        )
        logger.info(f"Sent test message to {session_id}")
    except Exception as e:
        logger.error(f"Failed to send test message: {e}")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            logger.debug(f"Received message: {message}")

            message_type = message.get("type")

            if message_type == "audio":
                int16_data = message.get("data", [])
                audio_bytes = struct.pack(f"{len(int16_data)}h", *int16_data)
                await manager.send_audio(session_id, audio_bytes)

            elif message_type == "text":
                text = message.get("text", "")
                await manager.send_message(session_id, text)

            elif message_type == "interrupt":
                await manager.interrupt(session_id)

            else:
                logger.warning(f"Unknown message type: {message_type}")

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {session_id}")
        await manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"Error in websocket handler: {e}", exc_info=True)
        await manager.disconnect(session_id)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/context")
async def get_context():
    context = manager.context_manager.load_context()
    if context:
        return context
    return {"message": "No saved context found"}


@app.delete("/api/context")
async def clear_context():
    manager.context_manager.clear_context()
    manager.current_history = []
    return {"message": "Context cleared successfully"}


@app.get("/api/context/status")
async def context_status():
    context = manager.context_manager.load_context()
    if context:
        history_count = len(context.get("history", []))
        return {
            "exists": True,
            "saved_at": context.get("saved_at"),
            "history_count": history_count,
            "metadata": context.get("metadata", {}),
        }
    return {"exists": False}
