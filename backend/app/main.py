import asyncio
import base64
import json
import logging
import os
import struct
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from agents.realtime import (
    RealtimeRunner,
    RealtimeSession,
    RealtimeSessionEvent,
    RealtimeAgent,
)
from agents.tool import FunctionTool
from typing_extensions import assert_never

from .agents.outlook_tools import OutlookTools
from .integrations.outlook import OutlookClient

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent with Outlook Integration")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000"
    ).split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RealtimeWebSocketManager:
    def __init__(self):
        self.active_sessions: dict[str, RealtimeSession] = {}
        self.session_contexts: dict[str, Any] = {}
        self.websockets: dict[str, WebSocket] = {}
        self.outlook_tools: dict[str, OutlookTools] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.websockets[session_id] = websocket
        logger.info(f"Client connected: {session_id}")

        # Initialize Outlook tools
        outlook_tools = OutlookTools()
        self.outlook_tools[session_id] = outlook_tools

        # Get function definitions from outlook_tools
        function_defs = outlook_tools.get_function_definitions()

        # Create FunctionTool objects for each function
        tools = []
        for func_def in function_defs:
            func_name = func_def["name"]

            # Create async handler that calls the appropriate function
            # Use default argument to capture func_name value in closure
            def create_handler(name=func_name):
                async def handler(context, arguments_json):
                    args = json.loads(arguments_json)
                    result = await outlook_tools.execute_function(name, args)
                    return result

                return handler

            tool = FunctionTool(
                name=func_def["name"],
                description=func_def["description"],
                params_json_schema=func_def["parameters"],
                on_invoke_tool=create_handler(),
            )
            tools.append(tool)

        # Create agent with Outlook integration capabilities
        agent = RealtimeAgent(
            name="Assistant",
            instructions="""You are a helpful AI assistant with access to the user's Outlook account.
            You can help manage emails, calendar events, and provide information about their schedule.

            Available capabilities:
            - Read and search emails
            - Send and reply to emails
            - Mark emails as read or delete them
            - View calendar events and schedule
            - Create new calendar events

            Always confirm with the user before sending emails or creating calendar events.
            Be helpful, concise, and professional in your responses.""",
            tools=tools,
        )

        runner = RealtimeRunner(agent)

        session_context = await runner.run()
        session = await session_context.__aenter__()

        self.active_sessions[session_id] = session
        self.session_contexts[session_id] = session_context

        asyncio.create_task(self._process_events(session_id))
        logger.info(f"Session started: {session_id}")

    async def disconnect(self, session_id: str):
        if session_id in self.session_contexts:
            await self.session_contexts[session_id].__aexit__(None, None, None)
            del self.session_contexts[session_id]
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.websockets:
            del self.websockets[session_id]
        if session_id in self.outlook_tools:
            await self.outlook_tools[session_id].close()
            del self.outlook_tools[session_id]
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

        logger.debug(f"Serializing event: {event}")

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
        elif event.type == "history_added":
            base_event["item"] = event.item.model_dump()
        elif event.type == "guardrail_tripped":
            base_event["message"] = event.message
        elif event.type == "raw_model_event":
            base_event["raw_event"] = event.data.type
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


@app.websocket("/ws/realtime")
async def realtime_proxy(websocket: WebSocket):
    session_id = f"session_{id(websocket)}"  # unique id for each session

    await manager.connect(websocket, session_id)

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


@app.get("/auth/login")
async def auth_login():
    """Redirect to Microsoft login for OAuth authentication"""
    client_id = os.getenv("MICROSOFT_CLIENT_ID")
    tenant_id = os.getenv("MICROSOFT_TENANT_ID")

    if not client_id or not tenant_id:
        raise HTTPException(
            status_code=500,
            detail="Microsoft OAuth credentials not configured. Please set MICROSOFT_CLIENT_ID and MICROSOFT_TENANT_ID environment variables.",
        )

    redirect_uri = os.getenv("REDIRECT_URI", "http://localhost:8000/auth/callback")

    scopes = [
        "https://graph.microsoft.com/Mail.Read",
        "https://graph.microsoft.com/Mail.ReadWrite",
        "https://graph.microsoft.com/Mail.Send",
        "https://graph.microsoft.com/Calendars.Read",
        "https://graph.microsoft.com/Calendars.ReadWrite",
        "https://graph.microsoft.com/User.Read",
        "offline_access",  # Required for refresh tokens
    ]

    auth_url = (
        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?"
        f"client_id={client_id}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&scope={' '.join(scopes)}"
        f"&response_mode=query"
    )

    return RedirectResponse(auth_url)


@app.get("/auth/callback")
async def auth_callback(code: str = None, error: str = None):
    """Handle OAuth callback from Microsoft"""
    if error:
        raise HTTPException(status_code=400, detail=f"Auth error: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received")

    # Exchange code for tokens
    outlook_client = OutlookClient()
    redirect_uri = os.getenv("REDIRECT_URI", "http://localhost:8000/auth/callback")

    try:
        token_data = await outlook_client.get_access_token(code, redirect_uri)

        # In production, you should:
        # 1. Store these tokens securely in a database
        # 2. Associate them with the authenticated user
        # 3. Encrypt the tokens
        # 4. Implement token refresh logic

        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in")

        logger.info("Authentication successful")

        # Return success page or redirect to frontend
        return {
            "status": "success",
            "message": "Authentication successful! You can now close this window.",
            "token_info": {
                "expires_in": expires_in,
                "has_refresh_token": refresh_token is not None,
            },
            # For development only - in production, don't return tokens in response
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
    except Exception as e:
        logger.error(f"Token exchange failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {str(e)}")


@app.post("/auth/refresh")
async def refresh_token(refresh_token: str):
    """Refresh an expired access token"""
    outlook_client = OutlookClient()
    outlook_client.config.refresh_token = refresh_token

    try:
        token_data = await outlook_client.refresh_access_token()

        return {
            "status": "success",
            "access_token": token_data["access_token"],
            "expires_in": token_data.get("expires_in"),
        }
    except Exception as e:
        logger.error(f"Token refresh failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")
