import { useState, useRef } from "react";
import { Phone, PhoneOff, Mic, MicOff, Send } from "lucide-react";
import { AudioVisualizer } from "./components/AudioVisualizer";
import { TranscriptPanel } from "./components/TranscriptPanel";
import { useWebRTC } from "./hooks/useWebRTC";
import { useAudioLevel } from "./hooks/useAudioLevel";

function App() {
  const [isCallActive, setIsCallActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [transcript, setTranscript] = useState<
    Array<{ role: "user" | "ai"; text: string; timestamp: Date }>
  >([]);
  const [textInput, setTextInput] = useState("");
  const transcriptMapRef = useRef(new Map<string, boolean>());

  const { connect, disconnect, sendText, isConnected } = useWebRTC({
    onTranscript: (text: string, role: "user" | "ai") => {
      // Deduplicate transcripts using a map
      const key = `${role}-${text}`;
      if (!transcriptMapRef.current.has(key)) {
        transcriptMapRef.current.set(key, true);
        setTranscript((prev) => [
          ...prev,
          { role, text, timestamp: new Date() },
        ]);
      }
    },
    onAudio: (audioData: ArrayBuffer) => {
      console.log("Received audio data:", audioData.byteLength);
    },
  });

  const { audioLevel, startListening, stopListening } = useAudioLevel();

  const handleStartCall = async () => {
    try {
      await connect();
      await startListening();
      setIsCallActive(true);
    } catch (error) {
      console.error("Failed to start call:", error);
    }
  };

  const handleEndCall = () => {
    disconnect();
    stopListening();
    setIsCallActive(false);
    setTranscript([]);
    transcriptMapRef.current.clear();
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
    if (!isMuted) {
      stopListening();
    } else {
      startListening();
    }
  };

  const handleSendText = (e: React.FormEvent) => {
    e.preventDefault();
    if (textInput.trim() && isConnected) {
      sendText(textInput);
      // Add to transcript immediately
      setTranscript((prev) => [
        ...prev,
        {
          role: "user",
          text: textInput,
          timestamp: new Date(),
        },
      ]);
      setTextInput("");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100 to-slate-50 flex items-center justify-center p-6">
      <div className="w-full max-w-2xl">
        {/* Main Call Interface */}
        <div className="bg-white/80 backdrop-blur-xl rounded-[2rem] shadow-xl border border-slate-200/60 overflow-hidden">
          {/* Header */}
          <div className="px-8 py-6 border-b border-slate-200/60">
            <h1 className="text-2xl font-medium text-slate-800 mb-1">
              Voice AI Assistant
            </h1>
            <p className="text-slate-500 text-sm">
              {isCallActive ? "Connected" : "Ready to connect"}
            </p>
          </div>

          {/* Audio Visualizer */}
          <div className="px-4 py-8 bg-gradient-to-b from-slate-50/50 to-white">
            <AudioVisualizer
              isActive={isCallActive && !isMuted}
              audioLevel={audioLevel}
            />
          </div>

          {/* Transcript Panel */}
          {isCallActive && (
            <div className="px-8 pb-6">
              <TranscriptPanel transcript={transcript} />
            </div>
          )}

          {/* Text Input */}
          {isCallActive && (
            <div className="px-8 pb-6">
              <form onSubmit={handleSendText} className="relative">
                <input
                  type="text"
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  placeholder="Type a message..."
                  className="w-full px-5 py-3 pr-14 rounded-2xl border border-slate-200 bg-white/80 backdrop-blur-sm focus:outline-none focus:ring-2 focus:ring-blue-400 focus:border-transparent text-slate-700 placeholder-slate-400 text-sm transition-all"
                  disabled={!isConnected}
                />
                <button
                  type="submit"
                  disabled={!textInput.trim() || !isConnected}
                  className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-xl bg-blue-500 hover:bg-blue-600 disabled:bg-slate-300 disabled:cursor-not-allowed flex items-center justify-center transition-all duration-200 transform hover:scale-105 active:scale-95"
                >
                  <Send className="w-5 h-5 text-white" />
                </button>
              </form>
            </div>
          )}

          {/* Controls */}
          <div className="px-8 py-8 bg-slate-50/50">
            <div className="flex items-center justify-center gap-6">
              {/* Mute Button */}
              {isCallActive && (
                <button
                  onClick={toggleMute}
                  className={`w-14 h-14 rounded-full flex items-center justify-center transition-all duration-300 shadow-md ${
                    isMuted
                      ? "bg-slate-300 hover:bg-slate-400 shadow-slate-300/50"
                      : "bg-white hover:bg-slate-50 shadow-slate-200/80 border border-slate-200"
                  }`}
                >
                  {isMuted ? (
                    <MicOff className="w-6 h-6 text-slate-600" />
                  ) : (
                    <Mic className="w-6 h-6 text-slate-700" />
                  )}
                </button>
              )}

              {/* Call/End Button */}
              <button
                onClick={isCallActive ? handleEndCall : handleStartCall}
                className={`w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 transform hover:scale-105 active:scale-95 ${
                  isCallActive
                    ? "bg-rose-500 hover:bg-rose-600 shadow-lg shadow-rose-500/40"
                    : "bg-emerald-500 hover:bg-emerald-600 shadow-lg shadow-emerald-500/40"
                }`}
              >
                {isCallActive ? (
                  <PhoneOff className="w-8 h-8 text-white" />
                ) : (
                  <Phone className="w-8 h-8 text-white" />
                )}
              </button>
            </div>

            {/* Status Text */}
            <div className="text-center mt-5">
              <p className="text-slate-500 text-sm font-medium">
                {isCallActive
                  ? isMuted
                    ? "Microphone muted"
                    : "Listening..."
                  : "Tap to start call"}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
