import asyncio
import base64
import json
import logging
import struct
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from agents.realtime import (
    RealtimeRunner,
    RealtimeSession,
    RealtimeSessionEvent,
    RealtimeAgent,
)
from agents.tool import FunctionTool
from typing_extensions import assert_never

from .agents.github_tools import GitHubTools


INSTRUCTIONS = """
You are a helpful AI assistant with access to the user's GitHub.
You can help manage emails, calendar events, GitHub repositories, issues, and pull requests.

Available capabilities:

GitHub:
- List and search repositories
- View and manage issues
- Create and update pull requests
- List commits and branches
- Get repository information
- Search across GitHub

Always confirm with the user before:
- Creating or modifying GitHub issues/PRs
- Making any changes to repositories

Be helpful, concise, and professional in your responses.
"""

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Agent")


class RealtimeWebSocketManager:
    def __init__(self):
        self.active_sessions: dict[str, RealtimeSession] = {}
        self.session_contexts: dict[str, Any] = {}
        self.websockets: dict[str, WebSocket] = {}
        self.github_tools: dict[str, GitHubTools] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.websockets[session_id] = websocket
        logger.info(f"Client connected: {session_id}")

        github_tools = GitHubTools()
        self.github_tools[session_id] = github_tools

        tools = []

        for func_def in github_tools.get_function_definitions():
            func_name = func_def["name"]

            def create_handler(name=func_name):
                async def handler(context, arguments_json):
                    args = json.loads(arguments_json)
                    result = await github_tools.execute_function(name, args)
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
        if session_id in self.github_tools:
            await self.github_tools[session_id].close()
            del self.github_tools[session_id]
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
            # Also send the last item as history_added for easier frontend handling
            if event.history:
                last_item = event.history[-1]
                if hasattr(last_item, "role") and last_item.role == "assistant":
                    # Extract text from the last assistant message
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
            logger.info(f"🔍 RAW_MODEL_EVENT: {event.data.type}")

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


@app.websocket("/ws/realtime")
async def realtime_proxy(websocket: WebSocket):
    session_id = f"session_{id(websocket)}"  # unique id for each session

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
