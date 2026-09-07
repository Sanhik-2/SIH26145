import React, { useEffect, useRef } from 'react';
import { ShieldCheck, ArrowRight, Lock, Radio, Cpu, Activity, Zap } from 'lucide-react';

export default function HardwareDiodeTopology({ isStreaming, isAttacking, packetRate = 12 }) {
  const canvasRef = useRef(null);

  // Animated optical photon flow simulation on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationId;
    let particles = [];

    const resize = () => {
      canvas.width = canvas.parentElement.clientWidth;
      canvas.height = canvas.parentElement.clientHeight;
    };
    resize();
    window.addEventListener('resize', resize);

    // Particle generator
    const spawnRate = isAttacking ? 6 : (isStreaming ? 2 : 0.5);
    const particleSpeed = isAttacking ? 6.5 : 3.0;

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (Math.random() < spawnRate * 0.15) {
        particles.push({
          x: canvas.width * 0.20,
          y: canvas.height * 0.50 + (Math.random() - 0.5) * 16,
          vx: particleSpeed + Math.random() * 1.5,
          vy: (Math.random() - 0.5) * 0.4,
          size: isAttacking ? 3.5 : 2.5,
          color: isAttacking ? '#ef4444' : '#00f0ff',
          alpha: 1.0,
          trail: []
        });
      }

      // Update and draw particles
      particles.forEach((p, idx) => {
        p.trail.push({ x: p.x, y: p.y });
        if (p.trail.length > 8) p.trail.shift();

        p.x += p.vx;
        p.y += p.vy;

        // Draw laser trail
        ctx.beginPath();
        for (let i = 0; i < p.trail.length - 1; i++) {
          ctx.strokeStyle = p.color;
          ctx.globalAlpha = (i / p.trail.length) * 0.6;
          ctx.lineWidth = p.size * 0.8;
          ctx.moveTo(p.trail[i].x, p.trail[i].y);
          ctx.lineTo(p.trail[i + 1].x, p.trail[i + 1].y);
          ctx.stroke();
        }

        // Draw glowing photon head
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.globalAlpha = 0.95;
        ctx.fill();

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * 2.2, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = 0.4;
        ctx.fill();

        // Destination reached
        if (p.x > canvas.width * 0.82) {
          particles.splice(idx, 1);
        }
      });

      ctx.globalAlpha = 1.0;
      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationId);
    };
  }, [isStreaming, isAttacking]);

  return (
    <div className="relative rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl overflow-hidden shadow-2xl transition-all hover:border-slate-700">
      {/* Top Banner Ribbon */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-slate-800/80 bg-slate-950/70">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Radio className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white tracking-wide uppercase font-mono">
              Hardware Simplex Data Diode Architecture
            </h3>
            <p className="text-xs text-slate-400">
              Galvanic air-gap isolation · Unidirectional laser transmitter to photodiode detector
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>0.00% REVERSE FLOW (PHYSICALLY PREVENTED)</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-mono">
            <Zap className="w-3.5 h-3.5" />
            <span>LATENCY: 1.1ms</span>
          </div>
        </div>
      </div>

      {/* Main Visual Frame with Embedded Image and Canvas Overlay */}
      <div className="relative h-64 md:h-80 w-full bg-black overflow-hidden flex items-center justify-center">
        {/* Hardware Schematic Image */}
        <img
          src="/assets/hardware_data_diode.jpg"
          alt="Hardware Optical Data Diode Schematic"
          className="w-full h-full object-cover object-center opacity-85 hover:opacity-95 transition-opacity duration-500 filter brightness-95 contrast-110"
        />

        {/* Dynamic Canvas for Real-time Optical Photons */}
        <canvas
          ref={canvasRef}
          className="absolute inset-0 pointer-events-none z-10 w-full h-full"
        />

        {/* Subtle grid and overlay vignette */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#070b12] via-transparent to-transparent pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#070b12]/80 via-transparent to-[#070b12]/80 pointer-events-none" />

        {/* Node Labels Overlaid */}
        <div className="absolute left-6 top-6 z-20 flex flex-col gap-1 p-3 rounded-xl bg-slate-950/85 border border-cyan-500/30 backdrop-blur-md max-w-xs shadow-lg">
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs font-bold">
            <Lock className="w-3.5 h-3.5" />
            <span>IN-ZONE HIGH SECURITY</span>
          </div>
          <p className="text-[11px] text-slate-300">
            Protected air-gapped industrial SCADA network. Generates telemetry & unacknowledged UDP datagrams.
          </p>
        </div>

        <div className="absolute right-6 bottom-6 z-20 flex flex-col gap-1 p-3 rounded-xl bg-slate-950/85 border border-purple-500/30 backdrop-blur-md max-w-xs shadow-lg">
          <div className="flex items-center gap-2 text-purple-400 font-mono text-xs font-bold">
            <Cpu className="w-3.5 h-3.5" />
            <span>CHRONOS SCANNER SIDE</span>
          </div>
          <p className="text-[11px] text-slate-300">
            Photodiode receiver captures raw packet timing & features into Neural Jump-ODE inference core.
          </p>
        </div>

        {/* Center Transmission Pulse */}
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 px-3 py-1 rounded-full bg-slate-900/90 border border-slate-700 text-slate-300 font-mono text-xs flex items-center gap-2 shadow-xl">
          <span className={`w-2 h-2 rounded-full ${isAttacking ? 'bg-red-500 animate-ping' : 'bg-cyan-400 animate-pulse'}`}></span>
          <span>OPTICAL LASER SIMPLEX: {isAttacking ? 'THREAT INJECTION BURST' : 'PASSIVE MONITORING'}</span>
        </div>
      </div>

      {/* Interactive Bottom Stat Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-slate-800/80 border-t border-slate-800 bg-slate-950/50 text-xs font-mono">
        <div className="p-3.5 flex items-center justify-between">
          <span className="text-slate-400">Transmission Medium:</span>
          <span className="text-cyan-300 font-semibold">Single-Mode Fiber</span>
        </div>
        <div className="p-3.5 flex items-center justify-between">
          <span className="text-slate-400">Diode Isolation:</span>
          <span className="text-emerald-400 font-semibold">Class-1 Laser Isolator</span>
        </div>
        <div className="p-3.5 flex items-center justify-between">
          <span className="text-slate-400">Transport:</span>
          <span className="text-purple-300 font-semibold">Simplex UDP / QR Diode</span>
        </div>
        <div className="p-3.5 flex items-center justify-between">
          <span className="text-slate-400">Physical Feedback:</span>
          <span className="text-amber-300 font-semibold">Strictly Forbidden (0 dB)</span>
        </div>
      </div>
    </div>
  );
}
