import React, { useEffect, useRef, useState } from 'react';
import { Activity, Radio, BarChart3, Database, Sparkles } from 'lucide-react';

export default function TelemetryOscilloscope({ currentTelemetry, history = [] }) {
  const canvasRef = useRef(null);
  const [activeChannel, setActiveChannel] = useState('all');

  // Draw real-time oscilloscope telemetry waveforms
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationId;

    const resize = () => {
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = canvas.parentElement.clientHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const width = canvas.width;
      const height = canvas.height;

      // Draw cyber radar grid lines
      ctx.strokeStyle = 'rgba(30, 41, 59, 0.45)';
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

      // Draw horizontal center guideline
      ctx.strokeStyle = 'rgba(14, 165, 233, 0.2)';
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
        ctx.lineWidth = 2.2;
        ctx.shadowColor = color;
        ctx.shadowBlur = 8;

        points.forEach((pt, idx) => {
          const val = pt[channelKey] !== undefined ? pt[channelKey] : 0;
          const normalized = Math.min(Math.max(val / scaleMax, 0), 1);
          const x = idx * stepX;
          const y = offsetY + (1 - normalized) * heightRatio;

          if (idx === 0) {
            ctx.moveTo(x, y);
          } else {
            // Smooth bezier interpolation
            const prevVal = points[idx - 1][channelKey] || 0;
            const prevNorm = Math.min(Math.max(prevVal / scaleMax, 0), 1);
            const prevX = (idx - 1) * stepX;
            const prevY = offsetY + (1 - prevNorm) * heightRatio;
            const midX = (prevX + x) / 2;
            ctx.bezierCurveTo(midX, prevY, midX, y, x, y);
          }
        });
        ctx.stroke();
        ctx.shadowBlur = 0;

        // Glowing dot at the most recent real-time point
        if (points.length > 0) {
          const last = points[points.length - 1];
          const lastVal = last[channelKey] || 0;
          const lastNorm = Math.min(Math.max(lastVal / scaleMax, 0), 1);
          const headX = (points.length - 1) * stepX;
          const headY = offsetY + (1 - lastNorm) * heightRatio;

          ctx.beginPath();
          ctx.arc(headX, headY, 4, 0, Math.PI * 2);
          ctx.fillStyle = '#ffffff';
          ctx.fill();
          ctx.beginPath();
          ctx.arc(headX, headY, 8, 0, Math.PI * 2);
          ctx.fillStyle = color;
          ctx.globalAlpha = 0.5;
          ctx.fill();
          ctx.globalAlpha = 1.0;
        }
      };

      if (activeChannel === 'all' || activeChannel === 'iat') {
        drawChannelWave('iat', '#10b981', 5.0, 20, height * 0.4);
      }
      if (activeChannel === 'all' || activeChannel === 'bytes') {
        drawChannelWave('bytes', '#f59e0b', 1500, height * 0.25, height * 0.45);
      }
      if (activeChannel === 'all' || activeChannel === 'entropy') {
        drawChannelWave('entropy', '#00f0ff', 8.0, height * 0.45, height * 0.45);
      }
      if (activeChannel === 'all' || activeChannel === 'burst') {
        drawChannelWave('burst', '#ec4899', 10.0, height * 0.1, height * 0.35);
      }

      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationId);
    };
  }, [history, activeChannel]);

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl p-5 shadow-2xl flex flex-col justify-between">
      {/* Header & Channel Selector */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Activity className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white tracking-wide uppercase font-mono">
              Fluid Telemetry Oscilloscope
            </h3>
            <p className="text-xs text-slate-400">
              Irregular continuous time-series · Runge-Kutta neural ODE input waveform
            </p>
          </div>
        </div>

        {/* Channel Filter Pills */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-950/80 border border-slate-800 text-xs font-mono">
          <button
            onClick={() => setActiveChannel('all')}
            className={`px-2.5 py-1 rounded-lg transition-all ${
              activeChannel === 'all' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:text-white'
            }`}
          >
            All Channels
          </button>
          <button
            onClick={() => setActiveChannel('iat')}
            className={`px-2 py-1 rounded-lg transition-all ${
              activeChannel === 'iat' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'text-slate-400 hover:text-white'
            }`}
          >
            ● IAT
          </button>
          <button
            onClick={() => setActiveChannel('bytes')}
            className={`px-2 py-1 rounded-lg transition-all ${
              activeChannel === 'bytes' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'text-slate-400 hover:text-white'
            }`}
          >
            ● Bytes
          </button>
          <button
            onClick={() => setActiveChannel('entropy')}
            className={`px-2 py-1 rounded-lg transition-all ${
              activeChannel === 'entropy' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:text-white'
            }`}
          >
            ● Entropy
          </button>
        </div>
      </div>

      {/* Oscilloscope Canvas Area */}
      <div className="relative h-48 w-full bg-slate-950/90 rounded-xl border border-slate-800/80 overflow-hidden">
        <canvas ref={canvasRef} className="w-full h-full" />
        <div className="absolute bottom-2 right-3 text-[10px] font-mono text-slate-500 pointer-events-none">
          SWEEP RATE: 60 FPS · 30.0s HORIZON
        </div>
      </div>

      {/* Live Numeric Readout Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4 font-mono text-xs">
        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-emerald-500/20 flex flex-col">
          <span className="text-[11px] text-emerald-400 font-semibold flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            IAT (Inter-Arrival)
          </span>
          <span className="text-base font-bold text-white mt-1">
            {currentTelemetry?.iat !== undefined ? `${currentTelemetry.iat.toFixed(3)}s` : '—'}
          </span>
        </div>

        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-amber-500/20 flex flex-col">
          <span className="text-[11px] text-amber-400 font-semibold flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            Bytes (Volume)
          </span>
          <span className="text-base font-bold text-white mt-1">
            {currentTelemetry?.bytes !== undefined ? `${Math.round(currentTelemetry.bytes)} B` : '—'}
          </span>
        </div>

        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-cyan-500/20 flex flex-col">
          <span className="text-[11px] text-cyan-400 font-semibold flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400"></span>
            Shannon Entropy (H)
          </span>
          <span className="text-base font-bold text-white mt-1">
            {currentTelemetry?.entropy !== undefined ? `${currentTelemetry.entropy.toFixed(2)} bits` : '—'}
          </span>
        </div>

        <div className="p-2.5 rounded-xl bg-slate-950/60 border border-pink-500/20 flex flex-col">
          <span className="text-[11px] text-pink-400 font-semibold flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-pink-400"></span>
            Burst Intensity
          </span>
          <span className="text-base font-bold text-white mt-1">
            {currentTelemetry?.burst !== undefined ? currentTelemetry.burst.toFixed(2) : '—'}
          </span>
        </div>
      </div>
    </div>
  );
}
