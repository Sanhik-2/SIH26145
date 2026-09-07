import React, { useEffect, useRef } from 'react';
import { ShieldCheck, Lock, Radio, Cpu, Zap } from 'lucide-react';

export default function HardwareDiodeTopology({ isStreaming, isAttacking, packetRate = 12 }) {
  const canvasRef = useRef(null);

  // Animated optical photon flow simulation on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationId;
    let particles = [];

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

    // Constant-velocity particle generator
    const spawnRate = isAttacking ? 4 : (isStreaming ? 1.5 : 0.4);
    const particleSpeed = 2.5; // Steady, non-racing speed

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (Math.random() < spawnRate * 0.12) {
        particles.push({
          x: canvas.width * 0.20,
          y: canvas.height * 0.50 + (Math.random() - 0.5) * 12,
          vx: particleSpeed,
          vy: 0,
          size: 2.0,
          color: isAttacking ? '#f43f5e' : '#38bdf8',
          trail: []
        });
      }

      // Update and draw particles
      particles.forEach((p, idx) => {
        p.trail.push({ x: p.x, y: p.y });
        if (p.trail.length > 6) p.trail.shift();

        p.x += p.vx;

        // Draw crisp laser trail (no heavy blur)
        for (let i = 0; i < p.trail.length - 1; i++) {
          ctx.beginPath();
          ctx.strokeStyle = p.color;
          ctx.globalAlpha = (i / p.trail.length) * 0.45;
          ctx.lineWidth = 1.2;
          ctx.moveTo(p.trail[i].x, p.trail[i].y);
          ctx.lineTo(p.trail[i + 1].x, p.trail[i + 1].y);
          ctx.stroke();
        }

        // Draw photon head
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = 0.9;
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
      if (resizeObserver) resizeObserver.disconnect();
      cancelAnimationFrame(animationId);
    };
  }, [isStreaming, isAttacking]);

  return (
    <div className="relative rounded-xl border border-zinc-800 bg-[#090a0f] overflow-hidden h-full flex flex-col min-h-0 justify-between">
      {/* Top Banner Ribbon */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800 bg-zinc-950/60 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400">
            <Radio className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-zinc-200 tracking-wider uppercase font-mono">
              Hardware Simplex Data Diode Architecture
            </h3>
            <p className="text-[11px] text-zinc-400">
              Galvanic air-gap isolation · Unidirectional laser transmitter to photodiode detector
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-emerald-400 text-xs font-mono">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>0.00% REVERSE FLOW</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 text-xs font-mono">
            <Zap className="w-3.5 h-3.5 text-sky-400" />
            <span>INFERENCE: 1.1ms</span>
          </div>
        </div>
      </div>

      {/* Main Visual Frame with Embedded Image and Canvas Overlay */}
      <div className="relative flex-1 min-h-[260px] w-full bg-[#07090e] overflow-hidden flex items-center justify-center">
        {/* Hardware Schematic Image */}
        <img
          src="/assets/hardware_data_diode.jpg"
          alt="Hardware Optical Data Diode Schematic"
          className="w-full h-full object-cover object-center opacity-75 filter brightness-90 contrast-110"
        />

        {/* Dynamic Canvas for Real-time Optical Photons */}
        <canvas
          ref={canvasRef}
          className="absolute inset-0 pointer-events-none z-10 w-full h-full"
        />

        {/* Subtle vignette */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#090a0f] via-transparent to-[#090a0f]/40 pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#090a0f]/80 via-transparent to-[#090a0f]/80 pointer-events-none" />

        {/* Node Labels Overlaid */}
        <div className="absolute left-5 top-5 z-20 flex flex-col gap-1 p-2.5 rounded-lg bg-zinc-950/90 border border-zinc-800 font-mono text-xs max-w-xs shadow-md">
          <div className="flex items-center gap-1.5 text-zinc-200 font-semibold text-[11px]">
            <Lock className="w-3.5 h-3.5 text-emerald-400" />
            <span>ZONE A · IN-ZONE HIGH SECURITY</span>
          </div>
          <p className="text-[10px] text-zinc-400">
            Protected air-gapped industrial SCADA network. Generates telemetry &amp; unacknowledged UDP datagrams.
          </p>
        </div>

        <div className="absolute right-5 bottom-5 z-20 flex flex-col gap-1 p-2.5 rounded-lg bg-zinc-950/90 border border-zinc-800 font-mono text-xs max-w-xs shadow-md">
          <div className="flex items-center gap-1.5 text-zinc-200 font-semibold text-[11px]">
            <Cpu className="w-3.5 h-3.5 text-sky-400" />
            <span>ZONE B · CHRONOS SCANNER SIDE</span>
          </div>
          <p className="text-[10px] text-zinc-400">
            Photodiode receiver captures packet timing &amp; features into continuous Neural Jump-ODE core.
          </p>
        </div>

        {/* Center Transmission Pulse */}
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 px-3 py-1 rounded-md bg-zinc-950/90 border border-zinc-800 text-zinc-300 font-mono text-xs flex items-center gap-2">
          <span className={`w-1.5 h-1.5 rounded-full ${isAttacking ? 'bg-rose-500' : 'bg-emerald-400'}`}></span>
          <span>OPTICAL SIMPLEX: {isAttacking ? 'ANOMALOUS BURST' : 'PASSIVE MONITORING'}</span>
        </div>
      </div>

      {/* Interactive Bottom Stat Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-zinc-800/80 border-t border-zinc-800 bg-zinc-950 text-xs font-mono">
        <div className="p-3 flex items-center justify-between">
          <span className="text-zinc-400">Medium:</span>
          <span className="text-zinc-200 font-medium">Single-Mode Fiber</span>
        </div>
        <div className="p-3 flex items-center justify-between">
          <span className="text-zinc-400">Isolation:</span>
          <span className="text-zinc-200 font-medium">Class-1 Simplex Laser</span>
        </div>
        <div className="p-3 flex items-center justify-between">
          <span className="text-zinc-400">Transport:</span>
          <span className="text-zinc-200 font-medium">Simplex UDP / QR Diode</span>
        </div>
        <div className="p-3 flex items-center justify-between">
          <span className="text-zinc-400">Reverse Path:</span>
          <span className="text-emerald-400 font-medium">Physically None (0 dB)</span>
        </div>
      </div>
    </div>
  );
}
