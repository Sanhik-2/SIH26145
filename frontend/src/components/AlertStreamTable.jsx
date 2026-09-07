import React, { useState } from 'react';
import { ShieldAlert, AlertTriangle, CheckCircle2, ChevronRight, FileJson, Filter } from 'lucide-react';

export default function AlertStreamTable({ alerts = [] }) {
  const [filter, setFilter] = useState('all');
  const [selectedAlert, setSelectedAlert] = useState(null);

  const filtered = alerts.filter(a => {
    if (filter === 'confirmed') return a.is_anomaly && a.confirmed;
    if (filter === 'suspected') return a.is_anomaly && !a.confirmed;
    if (filter === 'calm') return !a.is_anomaly;
    return true;
  });

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl p-5 shadow-2xl">
      {/* Header & Filter Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white tracking-wide uppercase font-mono">
              Live Alert Event Stream
            </h3>
            <p className="text-xs text-slate-400">
              Decoupled LiveFeeder alert events · Independent anomaly & confirmation audit log
            </p>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-950/80 border border-slate-800 text-xs font-mono">
          <button
            onClick={() => setFilter('all')}
            className={`px-2.5 py-1 rounded-lg transition-all ${
              filter === 'all' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40' : 'text-slate-400 hover:text-white'
            }`}
          >
            All ({alerts.length})
          </button>
          <button
            onClick={() => setFilter('confirmed')}
            className={`px-2.5 py-1 rounded-lg transition-all ${
              filter === 'confirmed' ? 'bg-red-500/20 text-red-300 border border-red-500/40' : 'text-slate-400 hover:text-white'
            }`}
          >
            Confirmed ({alerts.filter(a => a.is_anomaly && a.confirmed).length})
          </button>
          <button
            onClick={() => setFilter('suspected')}
            className={`px-2.5 py-1 rounded-lg transition-all ${
              filter === 'suspected' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'text-slate-400 hover:text-white'
            }`}
          >
            Suspected ({alerts.filter(a => a.is_anomaly && !a.confirmed).length})
          </button>
        </div>
      </div>

      {/* Table Frame */}
      <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/70 max-h-80 overflow-y-auto">
        <table className="w-full text-left border-collapse font-mono text-xs">
          <thead>
            <tr className="border-b border-slate-800 bg-slate-900/90 text-slate-400 uppercase text-[11px] sticky top-0 z-10">
              <th className="py-2.5 px-4">Timestamp</th>
              <th className="py-2.5 px-4">Window Range</th>
              <th className="py-2.5 px-4 text-right">Peak Score</th>
              <th className="py-2.5 px-4 text-center">τ Threshold</th>
              <th className="py-2.5 px-4 text-center">Status</th>
              <th className="py-2.5 px-4">Top Channel</th>
              <th className="py-2.5 px-4">Threat Classification</th>
              <th className="py-2.5 px-4 text-center">Inspect</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-slate-500">
                  No alert events logged yet. Use the scenario triggers above to inject traffic.
                </td>
              </tr>
            ) : (
              filtered.slice().reverse().map((a, idx) => {
                const isConfirmed = a.is_anomaly && a.confirmed;
                const isSuspected = a.is_anomaly && !a.confirmed;
                return (
                  <tr
                    key={idx}
                    className={`hover:bg-slate-800/40 transition-colors ${
                      isConfirmed ? 'bg-red-950/20' : isSuspected ? 'bg-amber-950/15' : ''
                    }`}
                  >
                    <td className="py-2.5 px-4 text-slate-300 font-semibold">{a.ts || 'T+?'}</td>
                    <td className="py-2.5 px-4 text-slate-400">
                      [{a.window_t0?.toFixed(1) || '0.0'}s → {a.window_t1?.toFixed(1) || '10.0'}s]
                    </td>
                    <td className={`py-2.5 px-4 text-right font-bold ${
                      isConfirmed ? 'text-red-400' : isSuspected ? 'text-amber-400' : 'text-slate-300'
                    }`}>
                      {(a.peak_score || 0).toFixed(2)}
                    </td>
                    <td className="py-2.5 px-4 text-center text-slate-400">
                      {(a.threshold || 2.81).toFixed(2)}
                    </td>
                    <td className="py-2.5 px-4 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                        isConfirmed
                          ? 'bg-red-500/20 text-red-300 border-red-500/40'
                          : isSuspected
                          ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                          : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                      }`}>
                        {isConfirmed ? 'CONFIRMED' : isSuspected ? 'SUSPECTED' : 'CALM'}
                      </span>
                    </td>
                    <td className="py-2.5 px-4">
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300 text-[11px]">
                        {a.attribution?.top_channel || '—'}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-slate-300">
                      {a.attribution?.threat_type || '—'}
                    </td>
                    <td className="py-2.5 px-4 text-center">
                      <button
                        onClick={() => setSelectedAlert(a)}
                        className="p-1 rounded bg-slate-800 hover:bg-cyan-500/20 text-slate-400 hover:text-cyan-300 transition-colors"
                        title="View Raw JSON"
                      >
                        <FileJson className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Detail JSON Modal */}
      {selectedAlert && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-xl w-full p-6 shadow-2xl relative font-mono text-xs">
            <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800">
              <h4 className="text-sm font-bold text-white uppercase flex items-center gap-2">
                <FileJson className="w-4 h-4 text-cyan-400" />
                Alert Event Schema Inspector
              </h4>
              <button
                onClick={() => setSelectedAlert(null)}
                className="text-slate-400 hover:text-white px-2 py-1 rounded bg-slate-800"
              >
                ✕ Close
              </button>
            </div>
            <pre className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-cyan-300 max-h-96 overflow-y-auto">
              {JSON.stringify(selectedAlert, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
