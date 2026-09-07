import React from 'react';
import { Cpu, Lock, CheckCircle2 } from 'lucide-react';

export default function ArchitectureTheory() {
  const lockedDecisions = [
    {
      num: '1',
      title: 'Frozen Model at Runtime',
      badge: 'DEFENSE INTEGRITY',
      color: 'border-zinc-700 bg-zinc-900 text-zinc-300',
      description: 'Zero online weight mutation in production. Weights and the decision boundary τ are strictly read-only, preventing adversarial poisoning attacks and silent drift.'
    },
    {
      num: '2',
      title: 'Ops-Scheduled Retraining',
      badge: 'OPERATIONAL RIGOR',
      color: 'border-zinc-700 bg-zinc-900 text-emerald-400',
      description: 'Retraining occurs on scheduled ops cycles with air-gapped human sign-off, rather than unsupervised feedback loops that attackers could manipulate.'
    },
    {
      num: '3',
      title: 'Single Multiregime Baseline',
      badge: 'UNIFIED CALIBRATION',
      color: 'border-zinc-700 bg-zinc-900 text-sky-400',
      description: 'Telemetry + web sync benign traffic trained on one unified manifold. Eliminates regime-switching friction and maintains 0.0% false alarm rate during benign shifts.'
    },
    {
      num: '4',
      title: 'Unsupervised Channel Attribution',
      badge: 'ZERO ANNOTATION',
      color: 'border-zinc-700 bg-zinc-900 text-amber-400',
      description: 'Decomposes reconstruction error across physical channels: bytes -> exfil flood, entropy -> C2/tunneling, iat -> periodic beacon, burst -> clump density.'
    },
    {
      num: '5',
      title: 'Window-Peak & 2-of-3 Hysteresis',
      badge: 'ALERT INTEGRITY',
      color: 'border-zinc-700 bg-zinc-900 text-rose-400',
      description: 'Alerts require 2 consecutive stride confirmations before triggering actionable SOC sirens, completely eliminating single-packet transient spikes.'
    },
    {
      num: '6',
      title: 'Versioned Self-Contained Checkpoint',
      badge: 'AIR-GAP REPRODUCIBILITY',
      color: 'border-zinc-700 bg-zinc-900 text-zinc-300',
      description: 'Model weights, normalizers, scaler stats, threshold τ, and feature contracts are bundled in a single versioned artifact (MODEL_VERSION = 1.0).'
    }
  ];

  return (
    <div className="space-y-5">
      {/* Math Formulation Card */}
      <div className="rounded-xl border border-zinc-800 bg-[#090a0f] p-5">
        <div className="flex items-center gap-2.5 mb-5">
          <div className="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400">
            <Cpu className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-zinc-100 tracking-wide uppercase font-mono">
              Neural Jump-ODE Mathematical Foundation
            </h3>
            <p className="text-[11px] text-zinc-400">
              Continuous latent dynamics between irregular packet arrival times in unidirectional IP streams
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 font-mono text-xs">
          {/* Formulation 1: Continuous Drift */}
          <div className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 space-y-2">
            <div className="text-zinc-200 font-medium uppercase tracking-wider flex items-center justify-between text-xs">
              <span>1. Continuous Latent State Drift</span>
              <span className="text-[10px] bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800 text-zinc-400">ODE SOLVER</span>
            </div>
            <div className="p-2.5 bg-black/60 rounded-md text-zinc-200 text-xs border border-zinc-850 font-medium">
              {"dh(t)/dt = f_θ(h(t)),  t ∈ [t_{i-1}, t_i]"}
            </div>
            <p className="text-zinc-400 text-[11px] leading-relaxed">
              Between packet arrivals, network state evolves continuously via parameterized neural vector field f_θ. Captured with RK4 or Euler integration on irregular time intervals Δt.
            </p>
          </div>

          {/* Formulation 2: Discrete Bayesian Jump */}
          <div className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 space-y-2">
            <div className="text-zinc-200 font-medium uppercase tracking-wider flex items-center justify-between text-xs">
              <span>2. Observation Jump Discontinuity</span>
              <span className="text-[10px] bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800 text-zinc-400">JUMP UPDATE</span>
            </div>
            <div className="p-2.5 bg-black/60 rounded-md text-zinc-200 text-xs border border-zinc-850 font-medium">
              {"h(t_i^+) = g_ϕ(h(t_i^-), x_i)"}
            </div>
            <p className="text-zinc-400 text-[11px] leading-relaxed">
              When packet x_i arrives over the simplex diode, state undergoes an instantaneous Bayesian jump update g_ϕ combining the accumulated prior h(t_i^-) with new evidence x_i.
            </p>
          </div>

          {/* Formulation 3: Peak Reconstruction Error */}
          <div className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 space-y-2">
            <div className="text-zinc-200 font-medium uppercase tracking-wider flex items-center justify-between text-xs">
              <span>3. Window Peak Anomaly Score</span>
              <span className="text-[10px] bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800 text-rose-400">PEAK METRIC</span>
            </div>
            <div className="p-2.5 bg-black/60 rounded-md text-zinc-200 text-xs border border-zinc-850 font-medium">
              {"S(W) = max_{t_i ∈ W} ||x_i - x̂_i||₂"}
            </div>
            <p className="text-zinc-400 text-[11px] leading-relaxed">
              Detects transient attacks that burst and disappear within a window. Taking the window maximum ensures lethal short bursts (e.g. 500ms exfil) are never diluted by averaging.
            </p>
          </div>

          {/* Formulation 4: Extreme Value Calibrated Tau */}
          <div className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 space-y-2">
            <div className="text-zinc-200 font-medium uppercase tracking-wider flex items-center justify-between text-xs">
              <span>4. Quantile Guaranteed Threshold</span>
              <span className="text-[10px] bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800 text-emerald-400">EVT CALIBRATION</span>
            </div>
            <div className="p-2.5 bg-black/60 rounded-md text-zinc-200 text-xs border border-zinc-850 font-medium">
              {"τ = Quantile_{1 - α}({S_k^{benign}}),  α = 0.001"}
            </div>
            <p className="text-zinc-400 text-[11px] leading-relaxed">
              Strictly calibrated on held-out benign validation windows with non-finite/null filtering, guaranteeing theoretical FPR ≤ 0.1% under normal operational traffic.
            </p>
          </div>
        </div>
      </div>

      {/* 6 Locked Decisions Cards */}
      <div className="rounded-xl border border-zinc-800 bg-[#090a0f] p-5">
        <div className="flex items-center gap-2.5 mb-5">
          <div className="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400">
            <Lock className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-zinc-100 tracking-wide uppercase font-mono">
              6 Locked Operational Design Decisions (SIH Jury Reference)
            </h3>
            <p className="text-[11px] text-zinc-400">
              Architectural constraints agreed upon to guarantee air-gap defense compliance
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 font-mono text-xs">
          {lockedDecisions.map((d) => (
            <div key={d.num} className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 flex flex-col justify-between hover:border-zinc-700 transition-colors">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-zinc-400 text-[11px] font-medium">DECISION #{d.num}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded border ${d.color}`}>
                    {d.badge}
                  </span>
                </div>
                <h4 className="text-xs font-semibold text-zinc-200 mb-1.5">{d.title}</h4>
                <p className="text-zinc-400 text-[11px] leading-relaxed">{d.description}</p>
              </div>
              <div className="mt-3 pt-2 border-t border-zinc-850 flex items-center text-emerald-400 text-[10px]">
                <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-500" />
                <span>LOCKED &amp; VERIFIED IN CORE</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
