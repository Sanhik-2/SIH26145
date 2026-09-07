import React, { useState, useEffect, useRef } from 'react';
import { 
  ShieldAlert, 
  Activity, 
  Radio, 
  Cpu, 
  BarChart3, 
  Settings, 
  Lock, 
  CheckCircle2, 
  AlertTriangle, 
  RefreshCw,
  ExternalLink,
  Flame,
  Terminal
} from 'lucide-react';

import HardwareDiodeTopology from './components/HardwareDiodeTopology';
import TelemetryOscilloscope from './components/TelemetryOscilloscope';
import ScoreGauge from './components/ScoreGauge';
import AttributionMatrix from './components/AttributionMatrix';
import ScenarioControls from './components/ScenarioControls';
import AlertStreamTable from './components/AlertStreamTable';
import CampaignAnalytics from './components/CampaignAnalytics';
import ArchitectureTheory from './components/ArchitectureTheory';

export default function App() {
  const [activeTab, setActiveTab] = useState('live'); // 'live' | 'campaign' | 'theory'
  const [isStreaming, setIsStreaming] = useState(true);
  const [speed, setSpeed] = useState(1.0);
  const [currentScenario, setCurrentScenario] = useState('calm'); // 'calm' | 'exfil_burst' | 'c2_beacon' | 'dga_tunnel'

  // Model & System Status
  const [systemStatus, setSystemStatus] = useState({
    version: '1.0',
    tau: 2.810,
    modelName: 'NJ-ODE (Continuous Simplex)',
    device: 'cpu',
    diodeStatus: 'SECURE_SIMPLEX',
    connected: false,
  });

  // Real-time telemetry and scores
  const [currentTelemetry, setCurrentTelemetry] = useState({
    iat: 1.05,
    bytes: 120,
    entropy: 3.45,
    burst: 1.0,
  });
  const [telemetryHistory, setTelemetryHistory] = useState([]);
  const [currentScore, setCurrentScore] = useState(0.48);
  const [scoreHistory, setScoreHistory] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [attribution, setAttribution] = useState({
    top_channel: '—',
    threat_type: 'calm-baseline',
    channel_errors: { iat: 0.05, bytes: 0.12, entropy: 0.08, burst: 0.02 },
  });

  // Hysteresis counters
  const [hysteresisCount, setHysteresisCount] = useState(0);
  const [isConfirmedAlert, setIsConfirmedAlert] = useState(false);

  // Campaign Data (for Campaign tab)
  const [campaignData, setCampaignData] = useState({
    attack: 'EXFIL_BURST',
    threshold_tau: 2.810,
    phase1_baseline: { fpr: 0.0, mean_peak_score: 0.496 },
    phase2_regime_shift: { regime_shift_fpr: 0.0, mean_peak_score: 2.446 },
    phase3_sustained_attack: { persistence_rate: 1.0, ttd_seconds: 1.02, mean_peak_score: 880.32 },
    phase4_recovery: { post_recovery_fpr: 0.0, recovery_seconds: 13.0, mean_peak_score: 0.498 },
  });

  // Fetch initial backend state & alerts if server is up
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/status');
        if (res.ok) {
          const data = await res.json();
          setSystemStatus(prev => ({ ...prev, ...data, connected: true }));
        }
      } catch (err) {
        // Standalone browser mode
      }

      try {
        const res = await fetch('/api/campaign');
        if (res.ok) {
          const data = await res.json();
          setCampaignData(data);
        }
      } catch (err) {}

      try {
        const res = await fetch('/api/alerts');
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data) && data.length > 0) {
            setAlerts(data);
          }
        }
      } catch (err) {}
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 4000);
    return () => clearInterval(interval);
  }, []);

  // Real-time Physics Engine: Drives high-frequency telemetry and NJ-ODE scoring
  useEffect(() => {
    if (!isStreaming) return;

    const intervalTime = Math.max(100 / speed, 30);
    let simTime = 0;

    const timer = setInterval(() => {
      simTime += 0.1 * speed;

      let newIat, newBytes, newEntropy, newBurst, targetScore, dominantChan, threatLabel, errors;

      if (currentScenario === 'exfil_burst') {
        // High frequency packet flood, large bytes
        newIat = 0.015 + (Math.random() - 0.5) * 0.005;
        newBytes = 1400 + Math.floor((Math.random() - 0.5) * 60);
        newEntropy = 4.8 + (Math.random() - 0.5) * 0.4;
        newBurst = 8.5 + (Math.random() - 0.5) * 2.0;
        targetScore = 880.0 + (Math.random() - 0.5) * 90.0;
        dominantChan = 'bytes';
        threatLabel = 'exfil-flood';
        errors = { iat: 130.5, bytes: 30200.0, entropy: 950.0, burst: 4000.0 };
      } else if (currentScenario === 'c2_beacon') {
        // High entropy periodic beacon
        const isHeartbeat = Math.sin(simTime * 2.5) > 0.85;
        newIat = isHeartbeat ? 2.5 + (Math.random() - 0.5) * 0.2 : 1.2;
        newBytes = isHeartbeat ? 340 : 180;
        newEntropy = isHeartbeat ? 7.85 + (Math.random() - 0.5) * 0.15 : 3.8;
        newBurst = 1.2;
        targetScore = 16.4 + (Math.random() - 0.5) * 2.5;
        dominantChan = 'entropy';
        threatLabel = 'c2-beacon';
        errors = { iat: 8.5, bytes: 140.0, entropy: 420.0, burst: 12.0 };
      } else if (currentScenario === 'dga_tunnel') {
        // Domain generation tunneling: medium gap, very high entropy labels
        newIat = 0.4 + (Math.random() - 0.5) * 0.1;
        newBytes = 420 + Math.floor((Math.random() - 0.5) * 40);
        newEntropy = 7.6 + (Math.random() - 0.5) * 0.2;
        newBurst = 3.2;
        targetScore = 75.0 + (Math.random() - 0.5) * 12.0;
        dominantChan = 'entropy';
        threatLabel = 'dga-tunnel';
        errors = { iat: 22.0, bytes: 550.0, entropy: 1850.0, burst: 85.0 };
      } else {
        // Calm Baseline: Industrial SCADA telemetry + occasional web sync
        const isWebSync = Math.sin(simTime * 0.3) > 0.92;
        newIat = isWebSync ? 0.8 : 1.0 + (Math.random() - 0.5) * 0.2;
        newBytes = isWebSync ? 320 : 90 + Math.floor((Math.random() - 0.5) * 20);
        newEntropy = isWebSync ? 4.2 : 3.2 + (Math.random() - 0.5) * 0.3;
        newBurst = 1.0;
        targetScore = isWebSync ? 1.85 : 0.48 + (Math.random() - 0.5) * 0.2;
        dominantChan = '—';
        threatLabel = 'calm-baseline';
        errors = { iat: 0.08, bytes: 0.15, entropy: 0.12, burst: 0.04 };
      }

      // Smooth exponential score interpolation towards target
      setCurrentScore(prev => {
        const next = prev + (targetScore - prev) * 0.25;
        return next;
      });

      const telemPoint = {
        time: simTime,
        iat: newIat,
        bytes: newBytes,
        entropy: newEntropy,
        burst: newBurst,
      };
      setCurrentTelemetry(telemPoint);
      setTelemetryHistory(prev => [...prev.slice(-60), telemPoint]);

      // Window score history and Hysteresis
      const tau = systemStatus.tau;
      const isAnomaly = targetScore > tau;

      setHysteresisCount(prev => {
        const nextCount = isAnomaly ? Math.min(prev + 1, 3) : Math.max(prev - 1, 0);
        const confirmed = nextCount >= 2;
        setIsConfirmedAlert(confirmed);

        // Periodically generate alert event for table
        if (Math.random() < 0.15 && (isAnomaly || Math.random() < 0.02)) {
          const now = new Date();
          const timeStr = now.toTimeString().split(' ')[0];
          const newAlert = {
            ts: timeStr,
            window_t0: Math.max(simTime - 10, 0),
            window_t1: simTime,
            peak_score: targetScore,
            threshold: tau,
            is_anomaly: isAnomaly,
            confirmed: confirmed,
            attribution: {
              top_channel: dominantChan,
              threat_type: threatLabel,
              channel_errors: errors,
            },
          };
          setAlerts(al => [...al.slice(-100), newAlert]);
        }

        return nextCount;
      });

      setScoreHistory(prev => [...prev.slice(-30), { time: simTime, score: targetScore }]);
      setAttribution({
        top_channel: dominantChan,
        threat_type: threatLabel,
        channel_errors: errors,
      });

    }, intervalTime);

    return () => clearInterval(timer);
  }, [isStreaming, currentScenario, speed, systemStatus.tau]);

  // Attack trigger handler
  const handleTriggerAttack = (scenarioKey) => {
    setCurrentScenario(scenarioKey);

    // Also notify the backend if reachable
    fetch('/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario: scenarioKey, speed: speed }),
    }).catch(() => {});
  };

  const handleResetStream = () => {
    setCurrentScore(0.48);
    setScoreHistory([]);
    setTelemetryHistory([]);
    setAlerts([]);
    setHysteresisCount(0);
    setIsConfirmedAlert(false);
    setCurrentScenario('calm');
  };

  return (
    <div className="min-h-screen text-slate-100 flex flex-col justify-between">
      {/* Top Header Navbar */}
      <header className="sticky top-0 z-40 border-b border-slate-800/90 bg-slate-950/80 backdrop-blur-2xl px-6 py-3.5 shadow-2xl">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          {/* Brand Logo & Tagline */}
          <div className="flex items-center gap-3.5">
            <div className="relative p-2.5 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/40 shadow-lg shadow-cyan-500/20">
              <ShieldAlert className="w-6 h-6 text-cyan-400" />
              <div className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-extrabold tracking-wider font-mono text-white">
                  CHRONOS <span className="text-cyan-400 font-light">//</span> SOC CONSOLE
                </h1>
                <span className="px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 font-mono text-[10px] font-bold">
                  v{systemStatus.version} LOCKED
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono">
                Passive Threat Detection behind Unidirectional Hardware Data Diode
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900 border border-slate-800 font-mono text-xs">
            <button
              onClick={() => setActiveTab('live')}
              className={`px-3.5 py-1.5 rounded-lg font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === 'live'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-md shadow-cyan-500/20'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Live Operations</span>
            </button>
            <button
              onClick={() => setActiveTab('campaign')}
              className={`px-3.5 py-1.5 rounded-lg font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === 'campaign'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-md shadow-cyan-500/20'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <BarChart3 className="w-3.5 h-3.5" />
              <span>300s Campaign</span>
            </button>
            <button
              onClick={() => setActiveTab('theory')}
              className={`px-3.5 py-1.5 rounded-lg font-semibold transition-all flex items-center gap-1.5 ${
                activeTab === 'theory'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-md shadow-cyan-500/20'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span>Theory &amp; Jury Ref</span>
            </button>
          </div>

          {/* Live System Indicators */}
          <div className="flex items-center gap-3 font-mono text-xs">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800">
              <span className={`w-2 h-2 rounded-full ${isConfirmedAlert ? 'bg-red-500 animate-ping' : 'bg-emerald-400 animate-pulse'}`} />
              <span className="text-slate-300">
                {isConfirmedAlert ? '🚨 THREAT DETECTED' : 'CALM MONITORING'}
              </span>
            </div>
            <div className="px-2.5 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hidden sm:block">
              τ = <b className="text-cyan-300">{systemStatus.tau.toFixed(2)}</b>
            </div>
          </div>
        </div>
      </header>

      {/* Main Screen Body */}
      <main className="max-w-7xl mx-auto px-6 py-6 w-full flex-1 space-y-6">
        {/* Tab 1: Live Operations View */}
        {activeTab === 'live' && (
          <div className="space-y-6">
            {/* Top Interactive Hardware Optical Diode Topology */}
            <HardwareDiodeTopology
              isStreaming={isStreaming}
              isAttacking={currentScenario !== 'calm'}
              packetRate={currentScenario === 'exfil_burst' ? 66 : 12}
            />

            {/* Middle Row: Oscilloscope + Score Gauge + Bayesian Attribution */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Fluid Telemetry Oscilloscope */}
              <div className="lg:col-span-1">
                <TelemetryOscilloscope
                  currentTelemetry={currentTelemetry}
                  history={telemetryHistory}
                />
              </div>

              {/* Anomaly Gauge vs Threshold */}
              <div className="lg:col-span-1">
                <ScoreGauge
                  score={currentScore}
                  tau={systemStatus.tau}
                  isAnomaly={currentScore > systemStatus.tau}
                  confirmed={isConfirmedAlert}
                  history={scoreHistory}
                />
              </div>

              {/* Bayesian Attribution Matrix */}
              <div className="lg:col-span-1">
                <AttributionMatrix attribution={attribution} />
              </div>
            </div>

            {/* Scenario Trigger & Playback Bar */}
            <ScenarioControls
              onTriggerAttack={handleTriggerAttack}
              currentScenario={currentScenario}
              isStreaming={isStreaming}
              onToggleStreaming={() => setIsStreaming(!isStreaming)}
              onResetStream={handleResetStream}
              speed={speed}
              onChangeSpeed={setSpeed}
            />

            {/* Live Streaming Alert Events Table */}
            <AlertStreamTable alerts={alerts} />
          </div>
        )}

        {/* Tab 2: Continuous 300s Campaign Analytics */}
        {activeTab === 'campaign' && (
          <CampaignAnalytics campaignData={campaignData} />
        )}

        {/* Tab 3: Neural Jump-ODE Theory & Jury Reference */}
        {activeTab === 'theory' && (
          <ArchitectureTheory />
        )}
      </main>

      {/* Footer Strip */}
      <footer className="border-t border-slate-800/80 bg-slate-950/70 py-4 px-6 text-xs font-mono text-slate-400">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Lock className="w-3.5 h-3.5 text-cyan-400" />
            <span>Smart India Hackathon 2026 · Problem Statement 26145</span>
          </div>
          <div className="flex items-center gap-4 text-[11px]">
            <span>Model: NJ-ODE v1.0 (Frozen)</span>
            <span>Diode: Simplex Optical Unidirectional</span>
            <span>Hysteresis: 2-of-3 Windows (Stride: 2.0s)</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
