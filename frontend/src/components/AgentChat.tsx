import React, { useState, useEffect, useRef } from "react";
import { Mic, MicOff, Send, Volume2, VolumeX } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
}

interface AgentEvent {
  type: string;
  [key: string]: any;
}

const AgentChat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [agentStatus, setAgentStatus] = useState<string>("Disconnected");
  const [currentAssistantMessage, setCurrentAssistantMessage] =
    useState<string>("");

  const wsRef = useRef<WebSocket | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // WebSocket connection
  useEffect(() => {
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
      }
    };
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const connectWebSocket = () => {
    const ws = new WebSocket("ws://localhost:8000/ws/realtime");

    ws.onopen = () => {
      console.log("WebSocket connected");
      setIsConnected(true);
      setAgentStatus("Connected");
      addSystemMessage("Connected to AI agent");
    };

    ws.onclose = () => {
      console.log("WebSocket disconnected");
      setIsConnected(false);
      setAgentStatus("Disconnected");
      addSystemMessage("Disconnected from AI agent");
    };

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setAgentStatus("Error");
      addSystemMessage("Connection error occurred");
    };

    ws.onmessage = (event) => {
      try {
        const data: AgentEvent = JSON.parse(event.data);

        handleAgentEvent(data);
      } catch (error) {
        console.error("Error parsing message:", error, "Raw data:", event.data);
      }
    };

    wsRef.current = ws;
  };

  const handleAgentEvent = (event: AgentEvent) => {
    switch (event.type) {
      case "debug_text":
        addSystemMessage(event.text);
        break;

      case "agent_start":
        setAgentStatus("Thinking...");
        break;

      case "agent_end":
        setAgentStatus("Ready");
        break;

      case "tool_start":
        setAgentStatus(`Using tool: ${event.tool}`);
        addMessage("system", `🔧 Calling function: ${event.tool}`);
        break;

      case "tool_end":
        setAgentStatus("Processing...");
        const toolOutput = event.output;
        if (toolOutput) {
          try {
            const parsed = JSON.parse(toolOutput);
            if (parsed.error) {
              addMessage("system", `⚠️ Tool error: ${parsed.error}`);
            }
          } catch (e) {
            // Ignore parse errors
          }
        }
        break;

      case "audio":
        if (!isMuted) {
          playAudio(event.audio);
        }
        break;

      case "audio_end":
        setAgentStatus("Ready");
        break;

      case "history_updated":
        // PRIORITY 1: Check if there's a pre-extracted last assistant message
        if (event.last_assistant_message) {
          addMessage("assistant", event.last_assistant_message);
          setCurrentAssistantMessage("");
          return; // Exit early
        }

        // PRIORITY 2: Try to extract from history
        if (event.history && event.history.length > 0) {
          const lastItem = event.history[event.history.length - 1];

          if (lastItem.role === "assistant" && lastItem.content) {
            const content = lastItem.content
              ?.map((c: any) => {
                if (c.type === "text" && c.text) return c.text;
                if (c.type === "audio" && c.transcript) return c.transcript;
                if (c.text) return c.text;
                if (c.transcript) return c.transcript;
                return "";
              })
              .filter((text: string) => text.length > 0)
              .join(" ");

            if (content && content.trim()) {
              addMessage("assistant", content);
              setCurrentAssistantMessage("");
              return; // Exit early
            } else {
              console.warn("⚠️⚠️⚠️ NO TEXT FOUND IN HISTORY CONTENT");
            }
          }
        }
        break;

      case "history_added":
        // Check if there's pre-extracted text
        if (event.text) {
          addMessage("assistant", event.text);
          setCurrentAssistantMessage("");
          break;
        }

        if (event.item && event.item.role === "assistant") {
          // Extract all text content from assistant message
          const content = event.item.content
            ?.map((c: any) => {
              if (c.type === "text" && c.text) {
                return c.text;
              }
              if (c.type === "audio" && c.transcript) {
                return c.transcript;
              }
              if (c.text) {
                return c.text;
              }
              if (c.transcript) {
                return c.transcript;
              }
              return "";
            })
            .filter((text: string) => text.length > 0)
            .join(" ");

          if (content && content.trim()) {
            addMessage("assistant", content);
            setCurrentAssistantMessage("");
          } else {
            console.warn("⚠️ No text content extracted from assistant message");
          }
        } else if (event.item && event.item.role === "user") {
          // Show user message from history
          const content = event.item.content
            ?.map((c: any) => c.text || c.transcript || "")
            .filter((text: string) => text.length > 0)
            .join(" ");

          if (content && content.trim()) {
            // Only add if not already in messages
            const lastMessage = messages[messages.length - 1];
            if (!lastMessage || lastMessage.content !== content) {
              addMessage("user", content);
            }
          }
        }
        break;

      case "response.text.delta":
        // Handle streaming text responses
        if (event.delta) {
          setCurrentAssistantMessage((prev) => prev + event.delta);
        }
        break;

      case "response.text.done":
        // Finalize streaming text
        if (currentAssistantMessage) {
          addMessage("assistant", currentAssistantMessage);
          setCurrentAssistantMessage("");
        }
        break;

      case "response.audio_transcript.delta":
        // Handle audio transcription streaming
        if (event.delta) {
          setCurrentAssistantMessage((prev) => {
            const newMessage = prev + event.delta;
            console.log("Current message now:", newMessage);
            return newMessage;
          });
        } else {
          console.warn(
            "⚠️ response.audio_transcript.delta with no delta field",
          );
        }
        break;

      case "response.audio_transcript.done":
        // Finalize audio transcript
        if (event.transcript || currentAssistantMessage) {
          const finalText = event.transcript || currentAssistantMessage;
          if (finalText) {
            addMessage("assistant", finalText);
            setCurrentAssistantMessage("");
          }
        } else {
          console.warn("⚠️ response.audio_transcript.done with no transcript");
        }
        break;

      case "raw_model_event":
        // Handle raw events that might contain transcript deltas
        if (event.raw_event === "transcript_delta") {
          if (event.delta) {
            setCurrentAssistantMessage((prev) => {
              const newMessage = prev + event.delta;
              return newMessage;
            });
          } else {
            console.warn("⚠️ transcript_delta but no delta field", event);
          }
        } else if (event.raw_event === "transcript_done") {
          if (event.transcript || currentAssistantMessage) {
            const finalText = event.transcript || currentAssistantMessage;
            if (finalText) {
              addMessage("assistant", finalText);
              setCurrentAssistantMessage("");
            }
          } else {
            console.warn("⚠️ transcript_done but no transcript field", event);
          }
        }
        break;

      case "error":
        setAgentStatus("Error");
        addSystemMessage(`❌ Error: ${event.error}`);
        break;

      default:
        console.log("Unhandled event type:", event.type);
    }
  };

  const playAudio = async (base64Audio: string) => {
    try {
      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContext();
      }

      const audioData = atob(base64Audio);
      const arrayBuffer = new ArrayBuffer(audioData.length);
      const view = new Uint8Array(arrayBuffer);
      for (let i = 0; i < audioData.length; i++) {
        view[i] = audioData.charCodeAt(i);
      }

      const audioBuffer =
        await audioContextRef.current.decodeAudioData(arrayBuffer);
      const source = audioContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContextRef.current.destination);
      source.start();
    } catch (error) {
      console.error("Error playing audio:", error);
    }
  };

  const sendTextMessage = () => {
    if (!inputText.trim() || !wsRef.current || !isConnected) return;

    addMessage("user", inputText);

    wsRef.current.send(
      JSON.stringify({
        type: "text",
        text: inputText,
      }),
    );

    setInputText("");
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      const audioChunks: Blob[] = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
        const arrayBuffer = await audioBlob.arrayBuffer();
        const int16Array = new Int16Array(arrayBuffer);

        if (wsRef.current && isConnected) {
          wsRef.current.send(
            JSON.stringify({
              type: "audio",
              data: Array.from(int16Array),
            }),
          );
        }
      };

      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);
      setAgentStatus("Listening...");
    } catch (error) {
      console.error("Error accessing microphone:", error);
      addSystemMessage("❌ Could not access microphone");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream
        .getTracks()
        .forEach((track) => track.stop());
      setIsRecording(false);
      setAgentStatus("Processing...");
    }
  };

  const addMessage = (role: "user" | "assistant", content: string) => {
    setMessages((prev) => {
      if (content.includes("Previous conversation context")) {
        return prev;
      }

      const newMessages = [
        ...prev,
        {
          id: Date.now().toString(),
          role,
          content,
          timestamp: new Date(),
        },
      ];
      return newMessages;
    });
  };

  const addSystemMessage = (content: string) => {
    addMessage("system", content);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendTextMessage();
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">AI Agent Chat</h1>
            <p className="text-sm text-gray-500 mt-1">
              Status:{" "}
              <span
                className={`font-medium ${
                  isConnected ? "text-green-600" : "text-red-600"
                }`}
              >
                {agentStatus}
              </span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsMuted(!isMuted)}
              className={`p-2 rounded-lg transition-colors ${
                isMuted
                  ? "bg-red-100 text-red-600 hover:bg-red-200"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
              title={isMuted ? "Unmute audio" : "Mute audio"}
            >
              {isMuted ? <VolumeX size={20} /> : <Volume2 size={20} />}
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <svg
                className="mx-auto h-12 w-12"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Start a conversation
            </h3>
            <p className="text-gray-500 max-w-md mx-auto">
              Ask me about your emails, calendar, or anything else I can help
              with!
            </p>
            <div className="mt-6 space-y-2 text-sm text-gray-600">
              <p>Try asking:</p>
              <ul className="space-y-1">
                <li>"What are my unread emails?"</li>
                <li>"Show me today's calendar"</li>
                <li>"Send an email to john@example.com"</li>
              </ul>
            </div>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.role === "user"
                ? "justify-end"
                : message.role === "system"
                  ? "justify-center"
                  : "justify-start"
            }`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-3 ${
                message.role === "user"
                  ? "bg-blue-600 text-white"
                  : message.role === "system"
                    ? "bg-gray-100 text-gray-700 text-sm border border-gray-200"
                    : "bg-white text-gray-900 shadow-sm border"
              }`}
            >
              <p className="whitespace-pre-wrap">{message.content}</p>
              <p
                className={`text-xs mt-1 ${
                  message.role === "user"
                    ? "text-blue-100"
                    : message.role === "system"
                      ? "text-gray-500"
                      : "text-gray-400"
                }`}
              ></p>
            </div>
          </div>
        ))}

        {/* Show current streaming message */}
        {currentAssistantMessage && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-lg px-4 py-3 bg-white text-gray-900 shadow-sm border">
              <p className="whitespace-pre-wrap">{currentAssistantMessage}</p>
              <p className="text-xs mt-1 text-gray-400">
                <span className="animate-pulse">●</span> typing...
              </p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t px-6 py-4">
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type a message or use voice..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows={1}
              disabled={!isConnected}
            />
          </div>

          <button
            onClick={isRecording ? stopRecording : startRecording}
            className={`p-3 rounded-lg transition-colors ${
              isRecording
                ? "bg-red-600 text-white hover:bg-red-700 animate-pulse"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
            disabled={!isConnected}
            title={isRecording ? "Stop recording" : "Start recording"}
          >
            {isRecording ? <MicOff size={24} /> : <Mic size={24} />}
          </button>

          <button
            onClick={sendTextMessage}
            className="p-3 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={!isConnected || !inputText.trim()}
            title="Send message"
          >
            <Send size={24} />
          </button>
        </div>

        {!isConnected && (
          <p className="text-sm text-red-600 mt-2">
            Not connected. Please check if the backend is running.
          </p>
        )}
      </div>
    </div>
  );
};

export default AgentChat;
