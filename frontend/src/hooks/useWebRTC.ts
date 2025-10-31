import { useState, useRef, useCallback } from "react";

interface UseWebRTCOptions {
  onTranscript?: (text: string, role: "user" | "ai") => void;
  onAudio?: (audioData: ArrayBuffer) => void;
}

export function useWebRTC(options: UseWebRTCOptions = {}) {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const processedItemsRef = useRef<Set<string>>(new Set());
  const playbackAudioContextRef = useRef<AudioContext | null>(null);
  const audioQueueRef = useRef<AudioBuffer[]>([]);
  const isPlayingRef = useRef(false);
  const gainNodeRef = useRef<GainNode | null>(null);
  const isBotMutedRef = useRef(false);
  const isMutedRef = useRef(false);
  const currentSourceRef = useRef<AudioBufferSourceNode | null>(null);

  const connect = useCallback(async () => {
    try {
      processedItemsRef.current.clear();

      const ws = new WebSocket(
        import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/realtime",
      );
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connected");
        setIsConnected(true);
      };

      ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        console.log("Received event:", data.type, data);

        // Handle different event types from backend
        if (data.type === "audio" && data.audio) {
          // Decode base64 audio and play it
          try {
            const binaryString = atob(data.audio);
            const bytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i);
            }
            console.log("Received audio chunk:", bytes.length, "bytes");
            options.onAudio?.(bytes.buffer);
            playAudio(bytes.buffer);
          } catch (error) {
            console.error("Error decoding audio:", error);
          }
        } else if (data.type === "history_updated") {
          console.log("🎯 history_updated event received");

          // PRIORITY 1: Check for pre-extracted last_assistant_message
          if (data.last_assistant_message) {
            console.log(
              "✅ Found last_assistant_message:",
              data.last_assistant_message,
            );
            options.onTranscript?.(data.last_assistant_message, "ai");
          } else {
            console.log(
              "⚠️ No last_assistant_message, extracting from history array",
            );
            // PRIORITY 2: Extract transcripts from history - only process new items
            if (data.history && Array.isArray(data.history)) {
              data.history.forEach((item: any) => {
                if (
                  item.item_id &&
                  !processedItemsRef.current.has(item.item_id)
                ) {
                  processHistoryItem(item);
                  processedItemsRef.current.add(item.item_id);
                }
              });
            }
          }
        } else if (data.type === "history_added") {
          // Handle newly added items
          const item = data.item;
          if (
            item &&
            item.item_id &&
            !processedItemsRef.current.has(item.item_id)
          ) {
            processHistoryItem(item);
            processedItemsRef.current.add(item.item_id);
          }
        } else if (data.type === "history_loaded") {
          console.log("📜 Loading saved context");
          if (data.history && Array.isArray(data.history)) {
            data.history.forEach((item: any) => {
              processHistoryItem(item);
            });
          }
        } else if (data.type === "error") {
          console.error("Backend error:", data.error);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected");
        setIsConnected(false);
      };

      // Setup audio capture
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 24000,
        },
      });
      streamRef.current = stream;

      // Create audio context for processing
      const audioContext = new AudioContext({ sampleRate: 24000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);

      // Use ScriptProcessorNode for better compatibility
      const processor = audioContext.createScriptProcessor(2048, 1, 1);
      scriptProcessorRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (ws.readyState === WebSocket.OPEN && !isMutedRef.current) {
          const inputData = e.inputBuffer.getChannelData(0);
          const int16Data = new Int16Array(inputData.length);

          for (let i = 0; i < inputData.length; i++) {
            const sample = Math.max(-1, Math.min(1, inputData[i]));
            int16Data[i] = sample * 32767;
          }

          ws.send(
            JSON.stringify({
              type: "audio",
              data: Array.from(int16Data),
            }),
          );
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);
    } catch (error) {
      console.error("Failed to connect:", error);
      setIsConnected(false);
    }
  }, [options]);

  const processHistoryItem = (item: any) => {
    if (item && item.type === "message" && item.content) {
      item.content.forEach((content: any) => {
        if (content.transcript && content.transcript.trim()) {
          const role = item.role === "user" ? "user" : "ai";
          options.onTranscript?.(content.transcript, role);
        } else if (content.text && content.text.trim()) {
          const role = item.role === "user" ? "user" : "ai";
          options.onTranscript?.(content.text, role);
        }
      });
    }
  };

  const disconnect = useCallback(() => {
    if (scriptProcessorRef.current) {
      scriptProcessorRef.current.disconnect();
      scriptProcessorRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    if (playbackAudioContextRef.current) {
      playbackAudioContextRef.current.close();
      playbackAudioContextRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    audioQueueRef.current = [];
    isPlayingRef.current = false;
    processedItemsRef.current.clear();
    setIsConnected(false);
  }, []);

  const sendText = useCallback((text: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "text",
          text: text,
        }),
      );
    }
  }, []);

  const playAudio = (audioData: ArrayBuffer) => {
    try {
      console.log("Playing audio chunk, size:", audioData.byteLength);
      // Create playback audio context if it doesn't exist
      if (!playbackAudioContextRef.current) {
        playbackAudioContextRef.current = new AudioContext({
          sampleRate: 24000,
        });

        // Create gain node for volume control
        gainNodeRef.current = playbackAudioContextRef.current.createGain();
        gainNodeRef.current.connect(
          playbackAudioContextRef.current.destination,
        );
        gainNodeRef.current.gain.value = isBotMutedRef.current ? 0 : 1;
      }

      // Update gain based on mute status
      if (gainNodeRef.current) {
        gainNodeRef.current.gain.value = isBotMutedRef.current ? 0 : 1;
      }

      const audioContext = playbackAudioContextRef.current;

      // Decode the PCM data as int16
      const int16Array = new Int16Array(audioData);
      const float32Array = new Float32Array(int16Array.length);

      // Convert int16 to float32
      for (let i = 0; i < int16Array.length; i++) {
        float32Array[i] = int16Array[i] / 32768.0;
      }

      // Create audio buffer
      const audioBuffer = audioContext.createBuffer(
        1,
        float32Array.length,
        24000,
      );
      audioBuffer.copyToChannel(float32Array, 0);

      // Add to queue
      audioQueueRef.current.push(audioBuffer);
      console.log("Audio queue size:", audioQueueRef.current.length);

      // Start playing if not already playing
      if (!isPlayingRef.current) {
        console.log("Starting audio playback");
        playNextInQueue();
      }
    } catch (error) {
      console.error("Error playing audio:", error);
    }
  };

  const playNextInQueue = () => {
    if (
      audioQueueRef.current.length === 0 ||
      !playbackAudioContextRef.current
    ) {
      isPlayingRef.current = false;
      return;
    }

    isPlayingRef.current = true;
    const audioBuffer = audioQueueRef.current.shift()!;
    const audioContext = playbackAudioContextRef.current;

    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;

    // Connect through gain node for volume control
    if (gainNodeRef.current) {
      source.connect(gainNodeRef.current);
    } else {
      source.connect(audioContext.destination);
    }

    source.onended = () => {
      console.log(
        "Audio chunk finished, queue size:",
        audioQueueRef.current.length,
      );
      playNextInQueue();
    };

    console.log("Starting audio source");
    source.start();
  };

  const setBotMuted = useCallback((muted: boolean) => {
    isBotMutedRef.current = muted;
    if (gainNodeRef.current) {
      gainNodeRef.current.gain.value = muted ? 0 : 1;
    }
  }, []);

  const setMuted = useCallback((muted: boolean) => {
    isMutedRef.current = muted;
  }, []);

  return {
    connect,
    disconnect,
    sendText,
    isConnected,
    setBotMuted,
    setMuted,
  };
}
