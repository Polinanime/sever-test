import { useEffect, useRef } from "react";

interface AudioVisualizerProps {
  isActive: boolean;
  audioLevel: number;
}

export function AudioVisualizer({
  isActive,
  audioLevel,
}: AudioVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const barsRef = useRef<number[]>(Array(48).fill(0));
  const phaseRef = useRef<number[]>(
    Array(48)
      .fill(0)
      .map(() => Math.random() * Math.PI * 2),
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const bars = barsRef.current;
    const phases = phaseRef.current;
    const barCount = bars.length;

    const animate = () => {
      const width = canvas.width;
      const height = canvas.height;

      ctx.clearRect(0, 0, width, height);

      const barWidth = width / barCount;
      const centerY = height / 2;
      const time = Date.now() / 1000;

      for (let i = 0; i < barCount; i++) {
        if (isActive) {
          const wave1 = Math.sin(time * 2 + i * 0.3 + phases[i]) * 0.3;
          const wave2 = Math.sin(time * 1.5 + i * 0.15) * 0.2;
          const normalizedPos = (i - barCount / 2) / (barCount / 2);
          const centerBias = 1 - Math.abs(normalizedPos) * 0.3;

          const targetHeight =
            (audioLevel * 0.7 + 0.15) * (wave1 + wave2 + 0.5) * centerBias;
          bars[i] += (targetHeight - bars[i]) * 0.2;
        } else {
          bars[i] *= 0.92;
        }

        const barHeight = Math.max(bars[i] * height * 0.7, 4);
        const x = i * barWidth + barWidth / 2;

        const gradient = ctx.createLinearGradient(
          0,
          centerY - barHeight / 2,
          0,
          centerY + barHeight / 2,
        );

        if (isActive) {
          gradient.addColorStop(0, "rgba(16, 185, 129, 0.8)");
          gradient.addColorStop(0.5, "rgba(52, 211, 153, 0.9)");
          gradient.addColorStop(1, "rgba(16, 185, 129, 0.8)");
        } else {
          gradient.addColorStop(0, "rgba(148, 163, 184, 0.3)");
          gradient.addColorStop(0.5, "rgba(148, 163, 184, 0.4)");
          gradient.addColorStop(1, "rgba(148, 163, 184, 0.3)");
        }

        ctx.fillStyle = gradient;
        ctx.shadowBlur = isActive ? 15 : 0;
        ctx.shadowColor = isActive ? "rgba(16, 185, 129, 0.5)" : "transparent";

        const radius = 3;
        const barW = barWidth * 0.6;
        ctx.beginPath();
        ctx.roundRect(
          x - barW / 2,
          centerY - barHeight / 2,
          barW,
          barHeight,
          radius,
        );
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isActive, audioLevel]);

  return (
    <div className="relative">
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div className="relative">
          <div
            className={`w-40 h-40 rounded-full transition-all duration-700 ease-out ${
              isActive
                ? "bg-gradient-to-br from-emerald-400/20 to-teal-400/20"
                : "bg-slate-600/10"
            }`}
            style={{
              transform: isActive
                ? `scale(${1 + audioLevel * 0.25})`
                : "scale(1)",
              filter: isActive ? "blur(20px)" : "blur(10px)",
            }}
          />
          <div
            className={`absolute inset-0 rounded-full transition-all duration-500 ${
              isActive
                ? "bg-gradient-to-br from-emerald-300/10 to-teal-300/10"
                : "bg-slate-500/5"
            }`}
            style={{
              transform: isActive
                ? `scale(${1 + audioLevel * 0.15})`
                : "scale(0.8)",
              filter: "blur(30px)",
            }}
          />
        </div>
      </div>
      <canvas
        ref={canvasRef}
        width={1200}
        height={180}
        className="w-full h-[280px]"
        style={{ imageRendering: "crisp-edges" }}
      />
    </div>
  );
}
