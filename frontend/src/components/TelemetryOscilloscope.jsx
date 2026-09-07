import React, { useEffect, useRef, useState } from 'react';
import { Activity } from 'lucide-react';

export default function TelemetryOscilloscope({ currentTelemetry, history = [] }) {
  const canvasRef = useRef(null);
  const [activeChannel, setActiveChannel] = useState('all');

  // Draw real-time oscilloscope telemetry waveforms
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationId;

    let resizeObserver;
    const resize = () => {
      if (canvas.parentElement) {
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = canvas.parentElement.clientHeight;
      }
    };
    resize();
    window.addEventListener('resize', resize);
    if (canvas.parentElement && typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(resize);
      resizeObserver.observe(canvas.parentElement);
    }

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const width = canvas.width;
      const height = canvas.height;

      // 1. Subtle, ultra-thin grid lines (Tufte data-ink ratio)
      ctx.strokeStyle = 'rgba(39, 39, 42, 0.35)'; // zinc-800
      ctx.lineWidth = 1;
      const gridStep = 40;
      for (let x = 0; x < width; x += gridStep) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += gridStep) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Horizontal center reference baseline
      ctx.strokeStyle = 'rgba(63, 63, 70, 0.4)';
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(0, height / 2);
      ctx.lineTo(width, height / 2);
      ctx.stroke();
      ctx.setLineDash([]);

      if (!history || history.length < 2) {
        animationId = requestAnimationFrame(render);
        return;
      }

      const points = history.slice(-60);
      const stepX = width / Math.max(points.length - 1, 1);

      const drawChannelWave = (channelKey, color, scaleMax, offsetY, heightRatio) => {
        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.6; // Crisp, non-blurry line

        points.forEach((pt, idx) => {
          const val = pt[channelKey] !== undefined ? pt[channelKey] : 0;
          const normalized = Math.min(Math.max(val / scaleMax, 0), 1);
          const x = idx * stepX;
          const y = offsetY + (1 - normalized) * heightRatio;

          if (idx === 0) {
            ctx.moveTo(x, y);
          } else {
            const prevVal = points[idx - 1][channelKey] || 0;
            const prevNorm = Math.min(Math.max(prevVal / scaleMax, 0), 1);
            const prevX = (idx - 1) * stepX;
            const prevY = offsetY + (1 - prevNorm) * heightRatio;
            const midX = (prevX + x) / 2;
            ctx.bezierCurveTo(midX, prevY, midX, y, x, y);
          }
        });
        ctx.stroke();

        // Discrete lead point at the most recent real-time value
        if (points.length > 0) {
          const last = points[points.length - 1];
          const lastVal = last[channelKey] || 0;
          const lastNorm = Math.min(Math.max(lastVal / scaleMax, 0), 1);
          const headX = (points.length - 1) * stepX;
          const headY = offsetY + (1 - lastNorm) * heightRatio;

          ctx.beginPath();
          ctx.arc(headX, headY, 2.5, 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.fill();
        }
      };

      if (activeChannel === 'all' || activeChannel === 'iat') {
        drawChannelWave('iat', '#10b981', 5.0, 16, height * 0.42);
      }
      if (activeChannel === 'all' || activeChannel === 'bytes') {
        drawChannelWave('bytes', '#38bdf8', 1500, height * 0.22, height * 0.45);
      }
      if (activeChannel === 'all' || activeChannel === 'entropy') {
        drawChannelWave('entropy', '#f59e0b', 8.0, height * 0.42, height * 0.45);
      }
      if (activeChannel === 'all' || activeChannel === 'burst') {
        drawChannelWave('burst', '#f43f5e', 10.0, height * 0.08, height * 0.38);
      }

      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', resize);
      if (resizeObserver) resizeObserver.disconnect();
      cancelAnimationFrame(animationId);
    };
  }, [history, activeChannel]);

  return (
    <div className="rounded-xl border border-zinc-800 bg-[#090a0f] p-4 flex flex-col h-full min-h-0 justify-between">
      {/* Header & Channel Selector */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-zinc-200 tracking-wider uppercase font-mono">
              Telemetry Oscilloscope
            </h3>
            <p className="text-[11px] text-zinc-400">
              Irregular continuous time-series · Runge-Kutta neural ODE input waveform
            </p>
          </div>
        </div>

        {/* Channel Filter Pills */}
        <div className="flex items-center gap-1 p-1 rounded-md bg-zinc-950 border border-zinc-800 text-xs font-mono">
          <button
            onClick={() => setActiveChannel('all')}
            className={`px-2 py-0.5 rounded transition-colors ${
              activeChannel === 'all' ? 'bg-zinc-800 text-zinc-100 font-medium' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            All Channels
          </button>
          <button
            onClick={() => setActiveChannel('iat')}
            className={`px-2 py-0.5 rounded transition-colors ${
              activeChannel === 'iat' ? 'bg-zinc-800 text-emerald-400 font-medium' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            ● IAT
          </button>
          <button
            onClick={() => setActiveChannel('bytes')}
            className={`px-2 py-0.5 rounded transition-colors ${
              activeChannel === 'bytes' ? 'bg-zinc-800 text-sky-400 font-medium' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            ● Bytes
          </button>
          <button
            onClick={() => setActiveChannel('entropy')}
            className={`px-2 py-0.5 rounded transition-colors ${
              activeChannel === 'entropy' ? 'bg-zinc-800 text-amber-400 font-medium' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            ● Entropy
          </button>
        </div>
      </div>

      {/* Oscilloscope Canvas Area */}
      <div className="relative flex-1 min-h-[220px] w-full bg-[#07090e] rounded-lg border border-zinc-800 overflow-hidden">
        <canvas ref={canvasRef} className="w-full h-full block" />
        <div className="absolute bottom-2 right-3 text-[10px] font-mono text-zinc-400 pointer-events-none">
          SWEEP: 60 FPS · 30.0s HORIZON
        </div>
      </div>

      {/* Live Numeric Readout Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 font-mono text-xs flex-shrink-0">
        <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800 flex flex-col">
          <span className="text-[10px] text-zinc-400 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            IAT (Inter-Arrival)
          </span>
          <span className="text-sm font-semibold text-zinc-200 mt-1">
            {currentTelemetry?.iat !== undefined ? `${currentTelemetry.iat.toFixed(3)}s` : '—'}
          </span>
        </div>

        <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800 flex flex-col">
          <span className="text-[10px] text-zinc-400 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-sky-400"></span>
            Bytes (Volume)
          </span>
          <span className="text-sm font-semibold text-zinc-200 mt-1">
            {currentTelemetry?.bytes !== undefined ? `${Math.round(currentTelemetry.bytes)} B` : '—'}
          </span>
        </div>

        <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800 flex flex-col">
          <span className="text-[10px] text-zinc-400 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            Shannon Entropy
          </span>
          <span className="text-sm font-semibold text-zinc-200 mt-1">
            {currentTelemetry?.entropy !== undefined ? `${currentTelemetry.entropy.toFixed(2)} bits` : '—'}
          </span>
        </div>

        <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800 flex flex-col">
          <span className="text-[10px] text-zinc-400 flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
            Burst Intensity
          </span>
          <span className="text-sm font-semibold text-zinc-200 mt-1">
            {currentTelemetry?.burst !== undefined ? currentTelemetry.burst.toFixed(2) : '—'}
          </span>
        </div>
      </div>
    </div>
  );
}
