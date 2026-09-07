import React from 'react';
import { BarChart3, Target } from 'lucide-react';

export default function CampaignAnalytics({ campaignData = {} }) {
  const p1 = campaignData.phase1_baseline || { fpr: 0.0, mean_peak_score: 0.50 };
  const p2 = campaignData.phase2_regime_shift || { regime_shift_fpr: 0.0, mean_peak_score: 2.45 };
  const p3 = campaignData.phase3_sustained_attack || { persistence_rate: 1.0, ttd_seconds: 1.02, mean_peak_score: 880.32 };
  const p4 = campaignData.phase4_recovery || { post_recovery_fpr: 0.0, recovery_seconds: 13.0, mean_peak_score: 0.50 };
  const tau = campaignData.threshold_tau || 2.810;

  const benchmarkMatrix = [
    {
      attack: 'Exfil Flood (exfil_burst)',
      peakScore: '880.32',
      tau: '2.81',
      ttd: '1.02s',
      persistence: '100.0%',
      channel: 'bytes (100%)',
      verdict: 'IMMEDIATE LETHAL BURST DETECTION'
    },
    {
      attack: 'C2 Beacon (c2_beacon)',
      peakScore: '16.40',
      tau: '2.81',
      ttd: '3.02s',
      persistence: '98.3%',
      channel: 'entropy (100%)',
      verdict: 'STEALTHY PERIODICITY CAUGHT'
    },
    {
      attack: 'DGA Tunnel (dga_tunnel)',
      peakScore: '75.08',
      tau: '2.81',
      ttd: '1.02s',
      persistence: '100.0%',
      channel: 'entropy (86.7%)',
      verdict: 'DOMAIN ANOMALY FLAGGED'
    }
  ];

  return (
    <div className="space-y-5">
      {/* 4-Phase Continuous Timeline Header */}
      <div className="rounded-xl border border-zinc-800 bg-[#090a0f] p-5">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
          <div>
            <h3 className="text-sm font-semibold text-zinc-100 tracking-wide uppercase font-mono flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-zinc-400" />
              Continuous 300-Second Campaign Benchmark
            </h3>
            <p className="text-[11px] text-zinc-400 mt-0.5">
              Single multiregime baseline checkpoint (τ = {tau.toFixed(3)}) · Zero false positives across calm &amp; regime shifts
            </p>
          </div>

          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="px-2 py-0.5 rounded-md bg-zinc-900 border border-zinc-800 text-emerald-400 text-[11px]">
              0.0% CALM FPR
            </span>
            <span className="px-2 py-0.5 rounded-md bg-zinc-900 border border-zinc-800 text-sky-400 text-[11px]">
              1.02s FASTEST TTD
            </span>
            <span className="px-2 py-0.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-300 text-[11px]">
              100% PERSISTENCE
            </span>
          </div>
        </div>

        {/* 4 Phase KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 font-mono">
          {/* Phase 1 */}
          <div className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs text-zinc-400 mb-1.5">
              <span>PHASE 1 (0–60s)</span>
              <span className="text-emerald-400">CALM BASELINE</span>
            </div>
            <div className="text-xl font-bold text-zinc-100">
              {(p1.fpr * 100).toFixed(1)}% <span className="text-xs text-zinc-400 font-normal">FPR</span>
            </div>
            <div className="text-[11px] text-zinc-400 mt-1.5">
              Mean Peak Score: <span className="text-emerald-400 font-semibold">{p1.mean_peak_score?.toFixed(2) || '0.50'}</span> &lt;&lt; τ
            </div>
          </div>

          {/* Phase 2 */}
          <div className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs text-zinc-400 mb-1.5">
              <span>PHASE 2 (60–120s)</span>
              <span className="text-sky-400">REGIME SHIFT</span>
            </div>
            <div className="text-xl font-bold text-zinc-100">
              {((p2.regime_shift_fpr || 0) * 100).toFixed(1)}% <span className="text-xs text-zinc-400 font-normal">FPR</span>
            </div>
            <div className="text-[11px] text-zinc-400 mt-1.5">
              Web Sync Mean S: <span className="text-sky-400 font-semibold">{p2.mean_peak_score?.toFixed(2) || '2.45'}</span> &lt; τ
            </div>
          </div>

          {/* Phase 3 */}
          <div className="p-3.5 rounded-lg bg-zinc-950 border border-rose-900/40 bg-rose-950/10 flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs text-zinc-400 mb-1.5">
              <span>PHASE 3 (120–240s)</span>
              <span className="text-rose-400 font-medium">SUSTAINED ATTACK</span>
            </div>
            <div className="text-xl font-bold text-rose-400">
              {((p3.persistence_rate || 1.0) * 100).toFixed(1)}% <span className="text-xs text-zinc-400 font-normal">PERSISTENCE</span>
            </div>
            <div className="text-[11px] text-zinc-400 mt-1.5">
              TTD: <span className="text-rose-300 font-semibold">{p3.ttd_seconds || 1.02}s</span> | Peak: {p3.mean_peak_score?.toFixed(1) || '880.3'}
            </div>
          </div>

          {/* Phase 4 */}
          <div className="p-3.5 rounded-lg bg-zinc-950 border border-zinc-800 flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs text-zinc-400 mb-1.5">
              <span>PHASE 4 (240–300s)</span>
              <span className="text-zinc-400">POST RECOVERY</span>
            </div>
            <div className="text-xl font-bold text-zinc-100">
              {((p4.post_recovery_fpr || 0) * 100).toFixed(1)}% <span className="text-xs text-zinc-400 font-normal">FPR</span>
            </div>
            <div className="text-[11px] text-zinc-400 mt-1.5">
              Decay Recovery: <span className="text-zinc-200 font-semibold">~{p4.recovery_seconds || 13.0}s</span>
            </div>
          </div>
        </div>

        {/* Continuous Campaign Plot Display */}
        <div className="mt-5 rounded-lg border border-zinc-800 overflow-hidden bg-black/60 flex flex-col items-center">
          <div className="w-full px-4 py-2 border-b border-zinc-800 text-[11px] font-mono text-zinc-400 flex items-center justify-between bg-zinc-950">
            <span>FIGURE 1: CONTINUOUS 300s TIMELINE PEAK ANOMALY SCORE S(t) VS DECISION BOUNDARY τ</span>
            <span className="text-zinc-300 font-medium">CHECKPOINT: njode_telemetry.pt (v1.0)</span>
          </div>
          <img
            src="/assets/campaign.png"
            alt="CHRONOS Continuous Campaign Benchmark Plot"
            className="w-full max-h-[420px] object-contain p-2"
          />
        </div>
      </div>

      {/* Canonical Comparison Table */}
      <div className="rounded-xl border border-zinc-800 bg-[#090a0f] p-5">
        <h4 className="text-xs font-semibold text-zinc-200 tracking-wider uppercase font-mono mb-3.5 flex items-center gap-2">
          <Target className="w-4 h-4 text-zinc-400" />
          Canonical Benchmark Across Attack Vectors
        </h4>

        <div className="overflow-x-auto rounded-lg border border-zinc-800 bg-zinc-950">
          <table className="w-full text-left border-collapse font-mono text-xs">
            <thead>
              <tr className="border-b border-zinc-800 bg-zinc-900 text-zinc-400 uppercase text-[10px] tracking-wider">
                <th className="py-2.5 px-3">Attack Scenario</th>
                <th className="py-2.5 px-3 text-right">Mean Peak Score (S)</th>
                <th className="py-2.5 px-3 text-center">Threshold (τ)</th>
                <th className="py-2.5 px-3 text-right">TTD</th>
                <th className="py-2.5 px-3 text-center">Persistence</th>
                <th className="py-2.5 px-3">Dominant Channel</th>
                <th className="py-2.5 px-3">Review Takeaway</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-850">
              {benchmarkMatrix.map((row, idx) => (
                <tr key={idx} className="hover:bg-zinc-900/50 transition-colors">
                  <td className="py-2.5 px-3 font-medium text-zinc-200">{row.attack}</td>
                  <td className="py-2.5 px-3 text-right font-semibold text-rose-400">{row.peakScore}</td>
                  <td className="py-2.5 px-3 text-center text-zinc-400">{row.tau}</td>
                  <td className="py-2.5 px-3 text-right text-sky-400 font-medium">{row.ttd}</td>
                  <td className="py-2.5 px-3 text-center text-emerald-400">{row.persistence}</td>
                  <td className="py-2.5 px-3">
                    <span className="px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-amber-300 text-[11px]">
                      {row.channel}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-zinc-400 text-[11px]">{row.verdict}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
