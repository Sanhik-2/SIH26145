import React, { useState } from 'react';
import { ShieldAlert, FileJson } from 'lucide-react';

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
    <div className="rounded-xl border border-zinc-800 bg-[#090a0f] p-4 h-full flex flex-col min-h-0">
      {/* Header & Filter Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3.5 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400">
            <ShieldAlert className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-zinc-200 tracking-wider uppercase font-mono">
              Alert Event Audit Stream
            </h3>
            <p className="text-[11px] text-zinc-400">
              Decoupled LiveFeeder alert events · Independent anomaly &amp; confirmation audit log
            </p>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1 p-1 rounded-md bg-zinc-950 border border-zinc-800 text-xs font-mono">
          <button
            onClick={() => setFilter('all')}
            className={`px-2 py-0.5 rounded transition-colors ${
              filter === 'all' ? 'bg-zinc-800 text-zinc-100 font-medium' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            All ({alerts.length})
          </button>
          <button
            onClick={() => setFilter('confirmed')}
            className={`px-2 py-0.5 rounded transition-colors ${
              filter === 'confirmed' ? 'bg-zinc-800 text-rose-400 font-medium' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Confirmed ({alerts.filter(a => a.is_anomaly && a.confirmed).length})
          </button>
          <button
            onClick={() => setFilter('suspected')}
            className={`px-2 py-0.5 rounded transition-colors ${
              filter === 'suspected' ? 'bg-zinc-800 text-amber-400 font-medium' : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Suspected ({alerts.filter(a => a.is_anomaly && !a.confirmed).length})
          </button>
        </div>
      </div>

      {/* High-Density Table Frame */}
      <div className="overflow-x-auto rounded-lg border border-zinc-800 bg-zinc-950 flex-1 min-h-0 overflow-y-auto">
        <table className="w-full text-left border-collapse font-mono text-xs">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900/90 text-zinc-400 uppercase text-[10px] tracking-wider sticky top-0 z-10">
              <th className="py-2 px-3">Timestamp</th>
              <th className="py-2 px-3">Window</th>
              <th className="py-2 px-3 text-center">Severity</th>
              <th className="py-2 px-3">Threat Class</th>
              <th className="py-2 px-3 text-center">Confidence</th>
              <th className="py-2 px-3 text-right">Peak Score</th>
              <th className="py-2 px-3 text-center">Status</th>
              <th className="py-2 px-3">Top Channel</th>
              <th className="py-2 px-3">Flow Evidence</th>
              <th className="py-2 px-3 text-center">Inspect</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-850">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={10} className="py-8 text-center text-zinc-400">
                  No alert events logged yet. Use the scenario triggers above to inject traffic.
                </td>
              </tr>
            ) : (
              filtered.slice().reverse().map((a, idx) => {
                const isConfirmed = a.is_anomaly && a.confirmed;
                const isSuspected = a.is_anomaly && !a.confirmed;
                const sev = a.severity || (isConfirmed ? 'HIGH' : isSuspected ? 'MEDIUM' : 'LOW');
                const confPct = ((a.confidence !== undefined ? a.confidence : (a.peak_score / (a.threshold || 2.81))) * 100).toFixed(1);
                
                const sevColor = 
                  sev === 'CRITICAL' ? 'bg-rose-950/40 text-rose-300 border-rose-800/40' :
                  sev === 'HIGH' ? 'bg-zinc-900 text-rose-400 border-zinc-700' :
                  sev === 'MEDIUM' ? 'bg-amber-950/40 text-amber-300 border-amber-800/40' :
                  'bg-zinc-900 text-emerald-400 border-zinc-800';

                return (
                  <tr
                    key={idx}
                    className={`hover:bg-zinc-900/50 transition-colors ${
                      isConfirmed ? 'bg-rose-950/15' : isSuspected ? 'bg-amber-950/10' : ''
                    }`}
                  >
                    <td className="py-2 px-3 text-zinc-300 font-medium">{a.ts || 'T+?'}</td>
                    <td className="py-2 px-3 text-zinc-400">
                      [{a.window_t0?.toFixed(1) || '0.0'}s → {a.window_t1?.toFixed(1) || '10.0'}s]
                    </td>
                    <td className="py-2 px-3 text-center">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${sevColor}`}>
                        {sev}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-zinc-200">
                      <span className="font-medium text-zinc-200">
                        {a.threat_class || a.attribution?.threat_type || 'calm-baseline'}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-center">
                      <span className={a.is_anomaly ? 'text-amber-400 font-medium' : 'text-zinc-400'}>
                        {confPct}%
                      </span>
                    </td>
                    <td className={`py-2 px-3 text-right font-medium ${
                      isConfirmed ? 'text-rose-400' : isSuspected ? 'text-amber-400' : 'text-zinc-300'
                    }`}>
                      {(a.peak_score || 0).toFixed(2)}
                      <span className="text-[10px] text-zinc-400 block font-normal">τ={(a.threshold || 2.81).toFixed(2)}</span>
                    </td>
                    <td className="py-2 px-3 text-center">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium border ${
                        isConfirmed
                          ? 'bg-rose-950/40 text-rose-300 border-rose-800/40'
                          : isSuspected
                          ? 'bg-amber-950/40 text-amber-300 border-amber-800/40'
                          : 'bg-zinc-900 text-emerald-400 border-zinc-800'
                      }`}>
                        {isConfirmed ? 'CONFIRMED' : isSuspected ? 'SUSPECTED' : 'CALM'}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <span className="px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-300 text-[11px] border border-zinc-800">
                        {a.attribution?.top_channel || '—'}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-zinc-400 text-[11px]">
                      {a.evidence ? (
                        <span>
                          {a.evidence.distinct_flows} flows · H={a.evidence.flow_entropy?.toFixed(1)}b
                          {a.evidence.top_flow_ids && a.evidence.top_flow_ids.length > 0 && (
                            <span className="text-zinc-400 block text-[10px]">
                              0x{a.evidence.top_flow_ids[0].toString(16).toUpperCase()}
                            </span>
                          )}
                        </span>
                      ) : (
                        <span>1 flow</span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-center">
                      <button
                        onClick={() => setSelectedAlert(a)}
                        className="p-1 rounded bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-100 border border-zinc-800 transition-colors"
                        title="Inspect Schema"
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
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl max-w-2xl w-full p-5 shadow-2xl relative font-mono text-xs">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-zinc-800">
              <h4 className="text-xs font-semibold text-zinc-200 uppercase flex items-center gap-2">
                <FileJson className="w-4 h-4 text-zinc-400" />
                Alert Event Schema Inspector
              </h4>
              <button
                onClick={() => setSelectedAlert(null)}
                className="text-zinc-400 hover:text-zinc-100 px-2 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 transition-colors"
              >
                ✕ Close
              </button>
            </div>

            {/* Quick Evidence Card */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-3">
              <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                <span className="text-zinc-400 text-[10px] block">THREAT CLASS</span>
                <span className="font-semibold text-zinc-200 text-xs mt-0.5 block">
                  {selectedAlert.threat_class || selectedAlert.attribution?.threat_type || 'calm-baseline'}
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                <span className="text-zinc-400 text-[10px] block">CONFIDENCE</span>
                <span className="font-semibold text-amber-400 text-xs mt-0.5 block">
                  {((selectedAlert.confidence || 0) * 100).toFixed(1)}%
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                <span className="text-zinc-400 text-[10px] block">DISTINCT FLOWS</span>
                <span className="font-semibold text-zinc-200 text-xs mt-0.5 block">
                  {selectedAlert.evidence?.distinct_flows || 1} active
                </span>
              </div>
              <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                <span className="text-zinc-400 text-[10px] block">FLOW ENTROPY</span>
                <span className="font-semibold text-zinc-200 text-xs mt-0.5 block">
                  {selectedAlert.evidence?.flow_entropy?.toFixed(2) || '0.00'} bits
                </span>
              </div>
            </div>

            <pre className="bg-zinc-950 p-3 rounded-lg border border-zinc-800 text-zinc-300 max-h-80 overflow-y-auto text-[11px] leading-relaxed">
              {JSON.stringify(selectedAlert, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
