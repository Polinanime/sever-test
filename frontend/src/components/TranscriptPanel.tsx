import { useEffect, useRef } from 'react';
import { User, Bot } from 'lucide-react';

interface Message {
  role: 'user' | 'ai';
  text: string;
  timestamp: Date;
}

interface TranscriptPanelProps {
  transcript: Message[];
}

export function TranscriptPanel({ transcript }: TranscriptPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [transcript]);

  if (transcript.length === 0) {
    return (
      <div className="bg-slate-100/60 rounded-2xl p-6 h-64 flex items-center justify-center border border-slate-200/50">
        <p className="text-slate-400 text-sm">Waiting for conversation...</p>
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      className="bg-slate-100/60 rounded-2xl p-6 h-64 overflow-y-auto space-y-4 scrollbar-thin scrollbar-thumb-slate-300 scrollbar-track-transparent border border-slate-200/50"
    >
      {transcript.map((message, index) => (
        <div
          key={index}
          className={`flex gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300 ${
            message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
          }`}
        >
          <div
            className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center shadow-sm ${
              message.role === 'user'
                ? 'bg-gradient-to-br from-blue-400 to-blue-500'
                : 'bg-gradient-to-br from-emerald-400 to-emerald-500'
            }`}
          >
            {message.role === 'user' ? (
              <User className="w-4 h-4 text-white" />
            ) : (
              <Bot className="w-4 h-4 text-white" />
            )}
          </div>
          <div
            className={`flex-1 ${
              message.role === 'user' ? 'text-right' : 'text-left'
            }`}
          >
            <div
              className={`inline-block px-4 py-3 rounded-2xl shadow-sm ${
                message.role === 'user'
                  ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white'
                  : 'bg-white text-slate-700 border border-slate-200'
              }`}
            >
              <p className="text-sm leading-relaxed">{message.text}</p>
            </div>
            <p className="text-xs text-slate-400 mt-1.5 px-2">
              {message.timestamp.toLocaleTimeString()}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
