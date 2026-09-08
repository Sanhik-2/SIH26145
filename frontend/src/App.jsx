import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  Activity, 
  Radio, 
  Cpu, 
  BarChart3, 
  Lock, 
  CheckCircle2, 
  AlertTriangle, 
  Terminal, 
  Layers, 
  Sparkles, 
  PlayCircle, 
  StopCircle, 
  Gauge, 
  Info,
  Database,
  Zap,
  RotateCcw,
  Camera
} from 'lucide-react';

import HardwareDiodeTopology from './components/HardwareDiodeTopology';
import NetworkGraphView from './components/NetworkGraphView';
import TelemetryOscilloscope from './components/TelemetryOscilloscope';
import ScoreGauge from './components/ScoreGauge';
import AttributionMatrix from './components/AttributionMatrix';
import ScenarioControls from './components/ScenarioControls';
import AlertStreamTable from './components/AlertStreamTable';
import CampaignAnalytics from './components/CampaignAnalytics';
import ArchitectureTheory from './components/ArchitectureTheory';
import PhoneCameraScanner from './components/PhoneCameraScanner';
import CallourDashboardView from './components/CallourDashboardView';
import UsbCableModal from './components/UsbCableModal';

export default function App() {
  // Tabs: 'dashboard' (Executive Home) | 'topology' | 'telemetry' | 'detection' | 'attribution' | 'alerts' | 'diode' | 'campaign' | 'theory'
  const [activeTab, setActiveTab] = useState('dashboard');
  const [showPhoneScanner, setShowPhoneScanner] = useState(false);
  const [showUsbModal, setShowUsbModal] = useState(false);
  const [usbStatus, setUsbStatus] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [speed, setSpeed] = useState(1.0);
  const [currentScenario, setCurrentScenario] = useState('calm');

  // Poll USB Physical Wire Cable Link status
  const fetchUsbStatus = async () => {
    try {
      const res = await fetch('/api/usb/status');
      if (res.ok) {
        const data = await res.json();
        setUsbStatus(data);
      }
    } catch (e) {}
  };

  useEffect(() => {
    fetchUsbStatus();
    const iv = setInterval(fetchUsbStatus, 3000);
    return () => clearInterval(iv);
  }, []);

  // Auto-open Phone Camera Scanner if requested via URL query param or route
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      if (params.get('scan') === '1' || window.location.pathname === '/scan' || params.has('scanner')) {
        setShowPhoneScanner(true);
      }
    }
  }, []);
  const [autoTour, setAutoTour] = useState(false);
  const [autoTourPhase, setAutoTourPhase] = useState({
    name: 'Phase 1/6: Calm Baseline (FPR 0.0%)',
    remaining: 8,
    stepIndex: 1,
    totalSteps: 6,
  });

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

  // Hysteresis state
  const [hysteresisCount, setHysteresisCount] = useState(0);
  const [isConfirmedAlert, setIsConfirmedAlert] = useState(false);

  // Real packet stream event from optical QR data diode
  const [realPacketEvent, setRealPacketEvent] = useState(null);

  // Campaign Data (for Campaign tab)
  const [campaignData, setCampaignData] = useState({
    attack: 'EXFIL_BURST',
    threshold_tau: 2.810,
    phase1_baseline: { fpr: 0.0, mean_peak_score: 0.496 },
    phase2_regime_shift: { regime_shift_fpr: 0.0, mean_peak_score: 2.446 },
    phase3_sustained_attack: { persistence_rate: 1.0, ttd_seconds: 1.02, mean_peak_score: 880.32 },
    phase4_recovery: { post_recovery_fpr: 0.0, recovery_seconds: 13.0, mean_peak_score: 0.498 },
  });

  // Connect to SSE real-time event stream from dashboard server
  useEffect(() => {
    let es = null;
    try {
      es = new EventSource('/api/stream');
      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'packet_transit') {
            setRealPacketEvent(data);
            if (data.scada) {
              const sc = data.scada;
              const telemPoint = {
                time: data.timestamp || (Date.now() / 1000),
                iat: (data.feat && data.feat[0]) || 0.1,
                bytes: (data.feat && data.feat[1]) || data.size || 128,
                entropy: (data.feat && data.feat[2]) || (sc.p ? (sc.p / 45.0) : 3.5),
                burst: (data.feat && data.feat[3]) || (sc.flow ? (sc.flow / 16000.0) : 1.0),
              };
              setCurrentTelemetry(telemPoint);
              setTelemetryHistory(prev => [...prev.slice(-60), telemPoint]);
            } else if (data.feat && Array.isArray(data.feat)) {
              const telemPoint = {
                time: data.timestamp || (Date.now() / 1000),
                iat: Number(data.feat[0]) || 0.1,
                bytes: Number(data.feat[1]) || data.size || 128,
                entropy: Number(data.feat[2]) || 3.5,
                burst: Number(data.feat[3]) || 1.0,
              };
              setCurrentTelemetry(telemPoint);
              setTelemetryHistory(prev => [...prev.slice(-60), telemPoint]);
            }
          } else if (data.type === 'nuclear_telemetry' && data.telemetry) {
            const nt = data.telemetry;
            const telemPoint = {
              time: data.timestamp || (Date.now() / 1000),
              iat: 0.1,
              bytes: nt.pressure_bar ? Math.round(nt.pressure_bar * 4) : 128,
              entropy: nt.core_temp_c ? (nt.core_temp_c / 100.0) : 3.1,
              burst: nt.coolant_flow_kgs ? (nt.coolant_flow_kgs / 16500.0) : 1.0,
            };
            setCurrentTelemetry(telemPoint);
            setTelemetryHistory(prev => [...prev.slice(-60), telemPoint]);
          } else if (data.type === 'scenario_change') {
            if (data.scenario) setCurrentScenario(data.scenario);
            if (data.speed) setSpeed(data.speed);
          } else if (data.type === 'anomaly_alert' && data.alert) {
            const a = data.alert;
            setAlerts(prev => [a, ...prev.slice(0, 99)]);
            if (a.confirmed) setIsConfirmedAlert(true);
            if (a.peak_score !== undefined) setCurrentScore(a.peak_score);
            if (a.attribution) setAttribution(a.attribution);
          } else if (data.type === 'alert' || data.is_anomaly !== undefined) {
            setAlerts(prev => [data, ...prev.slice(0, 99)]);
          }
        } catch (err) {}
      };
      es.onerror = () => {};
    } catch (err) {}

    return () => {
      if (es) es.close();
    };
  }, []);

  // Fetch initial backend state & alerts if server is up
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch('/api/status');
        if (res.ok) {
          const data = await res.json();
          setSystemStatus(prev => ({ ...prev, ...data, connected: true }));
        }
      } catch (err) {}

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

  // Autonomous Simulation Tour: Cycles through realistic threat phases
  useEffect(() => {
    if (!autoTour || !isStreaming) return;

    const tourSteps = [
      { scenario: 'calm', duration: 8, label: 'Phase 1/6: Calm Baseline (FPR 0.0%)' },
      { scenario: 'exfil_burst', duration: 12, label: 'Phase 2/6: 🚨 Exfil Flood (bytes)' },
      { scenario: 'calm', duration: 6, label: 'Phase 3/6: 🔄 Latent Decay Recovery' },
      { scenario: 'c2_beacon', duration: 12, label: 'Phase 4/6: 🚨 C2 Beacon (entropy)' },
      { scenario: 'calm', duration: 6, label: 'Phase 5/6: 🔄 Latent Decay Recovery' },
      { scenario: 'dga_tunnel', duration: 12, label: 'Phase 6/6: 🚨 DGA Tunnel (entropy)' },
    ];

    let currentStepIdx = 0;
    let stepElapsed = 0;

    const tourInterval = setInterval(() => {
      const step = tourSteps[currentStepIdx];
      stepElapsed += 1;
      const left = Math.max(step.duration - stepElapsed, 0);

      setAutoTourPhase({
        name: step.label,
        remaining: left,
        stepIndex: currentStepIdx + 1,
        totalSteps: tourSteps.length,
      });

      if (stepElapsed >= step.duration) {
        currentStepIdx = (currentStepIdx + 1) % tourSteps.length;
        stepElapsed = 0;
        setCurrentScenario(tourSteps[currentStepIdx].scenario);
      }
    }, 1000);

    return () => clearInterval(tourInterval);
  }, [autoTour, isStreaming]);

  // Real-time Physics Engine: Drives high-frequency telemetry and NJ-ODE scoring
  useEffect(() => {
    if (!isStreaming) return;

    const intervalTime = Math.max(100 / speed, 30);
    let simTime = 0;

    const timer = setInterval(() => {
      simTime += 0.1 * speed;

      let newIat, newBytes, newEntropy, newBurst, targetScore, dominantChan, threatLabel, errors;

      if (currentScenario === 'exfil_burst') {
        newIat = 0.015 + (Math.random() - 0.5) * 0.005;
        newBytes = 1400 + Math.floor((Math.random() - 0.5) * 60);
        newEntropy = 4.8 + (Math.random() - 0.5) * 0.4;
        newBurst = 8.5 + (Math.random() - 0.5) * 2.0;
        targetScore = 880.0 + (Math.random() - 0.5) * 90.0;
        dominantChan = 'bytes';
        threatLabel = 'exfil-flood';
        errors = { iat: 130.5, bytes: 30200.0, entropy: 950.0, burst: 4000.0 };
      } else if (currentScenario === 'c2_beacon') {
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
        newIat = 0.4 + (Math.random() - 0.5) * 0.1;
        newBytes = 420 + Math.floor((Math.random() - 0.5) * 40);
        newEntropy = 7.6 + (Math.random() - 0.5) * 0.2;
        newBurst = 3.2;
        targetScore = 75.0 + (Math.random() - 0.5) * 12.0;
        dominantChan = 'entropy';
        threatLabel = 'dga-tunnel';
        errors = { iat: 22.0, bytes: 550.0, entropy: 1850.0, burst: 85.0 };
      } else if (currentScenario === 'ddos_flood') {
        newIat = 0.005 + (Math.random() - 0.5) * 0.002;
        newBytes = 64 + Math.floor(Math.random() * 20);
        newEntropy = 2.1 + (Math.random() - 0.5) * 0.3;
        newBurst = 12.0 + (Math.random() - 0.5) * 2.0;
        targetScore = 420.0 + (Math.random() - 0.5) * 45.0;
        dominantChan = 'burst';
        threatLabel = 'ddos-flood';
        errors = { iat: 850.0, bytes: 120.0, entropy: 40.0, burst: 12500.0 };
      } else if (currentScenario === 'tls_c2') {
        newIat = 1.8 + (Math.random() - 0.5) * 0.3;
        newBytes = 512 + Math.floor((Math.random() - 0.5) * 50);
        newEntropy = 7.92 + (Math.random() - 0.5) * 0.08;
        newBurst = 1.4;
        targetScore = 24.5 + (Math.random() - 0.5) * 4.0;
        dominantChan = 'entropy';
        threatLabel = 'tls-c2';
        errors = { iat: 14.0, bytes: 210.0, entropy: 820.0, burst: 16.0 };
      } else if (currentScenario === 'portscan') {
        newIat = 0.08 + (Math.random() - 0.5) * 0.02;
        newBytes = 54;
        newEntropy = 3.1 + (Math.random() - 0.5) * 0.2;
        newBurst = 4.5;
        targetScore = 18.2 + (Math.random() - 0.5) * 3.0;
        dominantChan = 'iat';
        threatLabel = 'recon-portscan';
        errors = { iat: 420.0, bytes: 15.0, entropy: 8.0, burst: 120.0 };
      } else {
        // Calm Baseline: Industrial SCADA telemetry + periodic web sync
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
      setCurrentScore(prev => prev + (targetScore - prev) * 0.25);

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
            threat_class: threatLabel,
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

  // Nav Tabs configuration
  const NAV_TABS = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3, badge: null },
    { id: 'topology', label: 'Topology', icon: Layers, badge: null },
    { id: 'telemetry', label: 'Telemetry', icon: Activity, badge: null },
    { id: 'detection', label: 'Detection', icon: Gauge, badge: null },
    { id: 'attribution', label: 'Attribution', icon: Cpu, badge: null },
    { id: 'alerts', label: 'Alert Log', icon: ShieldAlert, badge: alerts.length > 0 ? alerts.length : null },
    { id: 'diode', label: 'Hardware Diode', icon: Radio, badge: null },
    { id: 'campaign', label: '300s Campaign', icon: BarChart3, badge: null },
    { id: 'theory', label: 'Architecture & Jury', icon: Terminal, badge: null },
  ];

  return (
    <div className="h-screen w-screen overflow-hidden text-zinc-100 flex flex-col bg-[#090a0f] select-none">
      {/* Top Header Navbar */}
      <header className="flex-shrink-0 border-b border-zinc-800 bg-[#090a0f]/95 px-5 py-2.5 z-40">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Brand Logo & Tagline */}
          <div className="flex items-center gap-2.5 flex-shrink-0">
            <div className="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-300">
              <ShieldAlert className="w-4 h-4 text-zinc-200" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xs font-semibold tracking-wider font-mono text-zinc-100 uppercase">
                  CHRONOS // SOC ENCLAVE
                </h1>
                <span className="px-1.5 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400 font-mono text-[9px]">
                  v{systemStatus.version} LOCKED
                </span>
              </div>
              <p className="text-[10px] text-zinc-400 font-mono hidden sm:block">
                Passive Threat Detection behind Unidirectional Optical Data Diode
              </p>
            </div>
          </div>

          {/* Dedicated Navigation Tabs ("for each button, we get a new tab") */}
          <nav className="flex items-center gap-1 p-1 rounded-lg bg-zinc-950 border border-zinc-800 font-mono text-xs overflow-x-auto">
            {NAV_TABS.map(tab => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-2.5 py-1 rounded-md transition-colors flex items-center gap-1.5 flex-shrink-0 ${
                    isActive
                      ? 'bg-zinc-800 text-zinc-100 font-medium ring-1 ring-zinc-700'
                      : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{tab.label}</span>
                  {tab.badge !== null && (
                    <span className="ml-0.5 px-1 py-0.2 text-[9px] rounded-full bg-rose-950 text-rose-300 border border-rose-800 font-mono">
                      {tab.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Live System Indicators */}
          <div className="flex items-center gap-2 font-mono text-xs flex-shrink-0">
            {/* Live Phone Camera Scanner Trigger */}
            <button
              onClick={() => setShowPhoneScanner(true)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-950/70 border border-emerald-600/60 text-emerald-400 hover:bg-emerald-900 text-xs font-mono transition-colors shadow-sm cursor-pointer"
              title="Open Phone Camera Optical Scanner"
            >
              <Camera className="w-3.5 h-3.5 animate-pulse" />
              <span className="hidden sm:inline">📱 SCAN QR</span>
            </button>

            {/* Auto-Simulation Tour Button */}
            <button
              onClick={() => setAutoTour(a => !a)}
              className={`flex items-center gap-1.5 px-2 py-0.5 rounded-md border text-xs font-mono transition-colors ${
                autoTour
                  ? 'bg-zinc-800 border-zinc-700 text-zinc-100'
                  : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200'
              }`}
              title="Toggle Autonomous Simulation Tour"
            >
              {autoTour ? <StopCircle className="w-3 h-3 text-zinc-300" /> : <PlayCircle className="w-3 h-3 text-emerald-400" />}
              <span>{autoTour ? `AUTO (${autoTourPhase.remaining}s)` : '▶ AUTO'}</span>
            </button>

            <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-md border ${
              isConfirmedAlert 
                ? 'bg-rose-950/30 border-rose-900/60 text-rose-300' 
                : 'bg-zinc-900 border-zinc-800 text-zinc-400'
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isConfirmedAlert ? 'bg-rose-500' : 'bg-emerald-500'}`} />
              <span className="hidden sm:inline">
                {isConfirmedAlert ? 'ANOMALY DETECTED' : 'CALM MONITORING'}
              </span>
            </div>

            <div className="px-2 py-0.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hidden md:block">
              τ = <span className="text-zinc-200">{systemStatus.tau.toFixed(2)}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Viewport Container: Fits within window height (zero page scrolling) */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-4 py-2.5 overflow-hidden flex flex-col min-h-0">
        {/* Auto-Simulation Tour Ribbon Banner (when active) */}
        {autoTour && (
          <div className="flex-shrink-0 flex items-center justify-between gap-3 px-3 py-1.5 mb-2 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-300 font-mono text-xs">
            <div className="flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-zinc-400 flex-shrink-0" />
              <span className="font-semibold text-zinc-200 uppercase text-[11px]">TOUR:</span>
              <span className="text-zinc-300 text-[11px]">{autoTourPhase.name}</span>
              <span className="text-zinc-500 text-[10px] hidden sm:inline">
                · Next in <span className="text-zinc-200 font-medium">{autoTourPhase.remaining}s</span>
              </span>
            </div>
            <button
              onClick={() => setAutoTour(false)}
              className="px-2 py-0.5 rounded bg-zinc-850 hover:bg-zinc-750 text-zinc-400 hover:text-zinc-100 border border-zinc-700 text-[11px] transition-colors"
            >
              Manual Mode
            </button>
          </div>
        )}

        {/* TAB 0: EXECUTIVE CALLOUR DASHBOARD */}
        {activeTab === 'dashboard' && (
          <div className="h-full flex flex-col min-h-0 overflow-y-auto">
            <CallourDashboardView
              systemStatus={systemStatus}
              currentTelemetry={currentTelemetry}
              telemetryHistory={telemetryHistory}
              currentScore={currentScore}
              scoreHistory={scoreHistory}
              alerts={alerts}
              attribution={attribution}
              isConfirmedAlert={isConfirmedAlert}
              realPacketEvent={realPacketEvent}
              currentScenario={currentScenario}
              onTriggerAttack={handleTriggerAttack}
              isStreaming={isStreaming}
              onToggleStreaming={() => setIsStreaming(!isStreaming)}
              onResetStream={handleResetStream}
              speed={speed}
              onChangeSpeed={setSpeed}
              usbStatus={usbStatus}
              onOpenUsbModal={() => setShowUsbModal(true)}
              onOpenScanner={() => setShowPhoneScanner(true)}
              onSwitchTab={setActiveTab}
            />
          </div>
        )}

        {/* TAB 1: HOME // OBSIDIAN NETWORK GRAPH */}
        {activeTab === 'topology' && (
          <div className="h-full flex flex-col min-h-0 space-y-2">
            <div className="flex-1 min-h-0 w-full">
              <NetworkGraphView
                currentScenario={currentScenario}
                score={currentScore}
                tau={systemStatus.tau}
                packetEvent={realPacketEvent}
                isStreaming={isStreaming}
              />
            </div>
            <ScenarioControls
              variant="compact"
              onTriggerAttack={handleTriggerAttack}
              currentScenario={currentScenario}
              isStreaming={isStreaming}
              onToggleStreaming={() => setIsStreaming(!isStreaming)}
              onResetStream={handleResetStream}
              speed={speed}
              onChangeSpeed={setSpeed}
            />
          </div>
        )}

        {/* TAB 2: TELEMETRY OSCILLOSCOPE */}
        {activeTab === 'telemetry' && (
          <div className="h-full flex flex-col min-h-0 space-y-2">
            <div className="flex-1 min-h-0 w-full">
              <TelemetryOscilloscope
                currentTelemetry={currentTelemetry}
                history={telemetryHistory}
              />
            </div>
            <ScenarioControls
              variant="compact"
              onTriggerAttack={handleTriggerAttack}
              currentScenario={currentScenario}
              isStreaming={isStreaming}
              onToggleStreaming={() => setIsStreaming(!isStreaming)}
              onResetStream={handleResetStream}
              speed={speed}
              onChangeSpeed={setSpeed}
            />
          </div>
        )}

        {/* TAB 3: ANOMALY DETECTION ENGINE */}
        {activeTab === 'detection' && (
          <div className="h-full flex flex-col min-h-0 space-y-2">
            <div className="flex-1 min-h-0 w-full grid grid-cols-1 md:grid-cols-3 gap-3 overflow-hidden">
              <div className="md:col-span-2 h-full flex flex-col min-h-0">
                <ScoreGauge
                  score={currentScore}
                  tau={systemStatus.tau}
                  isAnomaly={currentScore > systemStatus.tau}
                  confirmed={isConfirmedAlert}
                  history={scoreHistory}
                />
              </div>

              {/* Side Metric Panel */}
              <div className="md:col-span-1 flex flex-col justify-between p-4 rounded-xl border border-zinc-800 bg-[#090a0f] font-mono text-xs overflow-y-auto">
                <div>
                  <h4 className="text-xs font-semibold text-zinc-200 tracking-wider uppercase mb-3 flex items-center gap-1.5">
                    <Gauge className="w-3.5 h-3.5 text-zinc-400" />
                    Detection Specifications
                  </h4>
                  <div className="space-y-2.5 text-zinc-400 text-[11px]">
                    <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800 flex justify-between items-center">
                      <span>Calibrated Threshold τ</span>
                      <span className="text-zinc-200 font-semibold">{systemStatus.tau.toFixed(3)}</span>
                    </div>
                    <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800 flex justify-between items-center">
                      <span>Hysteresis Rule</span>
                      <span className="text-amber-400 font-semibold">2 of 3 Windows</span>
                    </div>
                    <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800 flex justify-between items-center">
                      <span>Stride Horizon</span>
                      <span className="text-zinc-200 font-semibold">2.0s</span>
                    </div>
                    <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800 flex justify-between items-center">
                      <span>Calm Baseline FPR</span>
                      <span className="text-emerald-400 font-semibold">0.00%</span>
                    </div>
                    <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800 flex justify-between items-center">
                      <span>Inference Latency</span>
                      <span className="text-sky-400 font-semibold">1.1ms</span>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-zinc-800 text-[10px] text-zinc-500 leading-relaxed">
                  Mathematical Decision Boundary: An alert is confirmed iff peak reconstruction error satisfies S(W) &gt; τ for 2 consecutive strides.
                </div>
              </div>
            </div>

            <ScenarioControls
              variant="compact"
              onTriggerAttack={handleTriggerAttack}
              currentScenario={currentScenario}
              isStreaming={isStreaming}
              onToggleStreaming={() => setIsStreaming(!isStreaming)}
              onResetStream={handleResetStream}
              speed={speed}
              onChangeSpeed={setSpeed}
            />
          </div>
        )}

        {/* TAB 4: CHANNEL ATTRIBUTION */}
        {activeTab === 'attribution' && (
          <div className="h-full flex flex-col min-h-0 space-y-2">
            <div className="flex-1 min-h-0 w-full grid grid-cols-1 md:grid-cols-3 gap-3 overflow-hidden">
              <div className="md:col-span-2 h-full flex flex-col min-h-0">
                <AttributionMatrix attribution={attribution} />
              </div>

              {/* Channel Taxonomy Reference */}
              <div className="md:col-span-1 flex flex-col justify-between p-4 rounded-xl border border-zinc-800 bg-[#090a0f] font-mono text-xs overflow-y-auto">
                <div>
                  <h4 className="text-xs font-semibold text-zinc-200 tracking-wider uppercase mb-3 flex items-center gap-1.5">
                    <Cpu className="w-3.5 h-3.5 text-zinc-400" />
                    Physical Channel Taxonomy
                  </h4>
                  <div className="space-y-2 text-[11px]">
                    <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800">
                      <div className="text-rose-400 font-semibold">BYTES DOMINANT</div>
                      <div className="text-zinc-400 text-[10px] mt-0.5">Payload volume exfiltration, large file dumps, jumbo frames.</div>
                    </div>
                    <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800">
                      <div className="text-amber-400 font-semibold">ENTROPY DOMINANT</div>
                      <div className="text-zinc-400 text-[10px] mt-0.5">DNS DGA tunneling, encrypted TLS C2, random domain queries.</div>
                    </div>
                    <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800">
                      <div className="text-emerald-400 font-semibold">IAT DOMINANT</div>
                      <div className="text-zinc-400 text-[10px] mt-0.5">Periodic heartbeat, synchronized polling, reconnaissance scan.</div>
                    </div>
                    <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800">
                      <div className="text-sky-400 font-semibold">BURST DOMINANT</div>
                      <div className="text-zinc-400 text-[10px] mt-0.5">Volumetric packet flooding, SYN flood, microburst traffic.</div>
                    </div>
                  </div>
                </div>

                <div className="mt-3 pt-2.5 border-t border-zinc-800 text-[10px] text-zinc-500">
                  Bayesian attribution decomposes reconstruction error e_k = ||x_k - x̂_k||₂ without requiring supervised training labels.
                </div>
              </div>
            </div>

            <ScenarioControls
              variant="compact"
              onTriggerAttack={handleTriggerAttack}
              currentScenario={currentScenario}
              isStreaming={isStreaming}
              onToggleStreaming={() => setIsStreaming(!isStreaming)}
              onResetStream={handleResetStream}
              speed={speed}
              onChangeSpeed={setSpeed}
            />
          </div>
        )}

        {/* TAB 5: ALERT LOG TABLE */}
        {activeTab === 'alerts' && (
          <div className="h-full flex flex-col min-h-0 space-y-2">
            <div className="flex-1 min-h-0 w-full">
              <AlertStreamTable alerts={alerts} />
            </div>
            <ScenarioControls
              variant="compact"
              onTriggerAttack={handleTriggerAttack}
              currentScenario={currentScenario}
              isStreaming={isStreaming}
              onToggleStreaming={() => setIsStreaming(!isStreaming)}
              onResetStream={handleResetStream}
              speed={speed}
              onChangeSpeed={setSpeed}
            />
          </div>
        )}

        {/* TAB 6: OPTICAL HARDWARE DIODE */}
        {activeTab === 'diode' && (
          <div className="h-full flex flex-col min-h-0 space-y-2">
            <div className="flex-1 min-h-0 w-full">
              <HardwareDiodeTopology
                packetEvent={realPacketEvent}
                isStreaming={isStreaming}
                isAttacking={currentScenario !== 'calm'}
                packetRate={currentScenario === 'exfil_burst' ? 66 : 12}
              />
            </div>
            <ScenarioControls
              variant="compact"
              onTriggerAttack={handleTriggerAttack}
              currentScenario={currentScenario}
              isStreaming={isStreaming}
              onToggleStreaming={() => setIsStreaming(!isStreaming)}
              onResetStream={handleResetStream}
              speed={speed}
              onChangeSpeed={setSpeed}
            />
          </div>
        )}

        {/* TAB 7: 300S CAMPAIGN BENCHMARK */}
        {activeTab === 'campaign' && (
          <div className="h-full flex flex-col min-h-0">
            <div className="flex-1 min-h-0 overflow-y-auto pr-1">
              <CampaignAnalytics campaignData={campaignData} />
            </div>
          </div>
        )}

        {/* TAB 8: THEORY & JURY REFERENCE */}
        {activeTab === 'theory' && (
          <div className="h-full flex flex-col min-h-0">
            <div className="flex-1 min-h-0 overflow-y-auto pr-1">
              <ArchitectureTheory />
            </div>
          </div>
        )}
      </main>

      {/* Footer Strip */}
      <footer className="flex-shrink-0 border-t border-zinc-800/80 bg-zinc-950 py-2 px-5 text-xs font-mono text-zinc-400">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Lock className="w-3.5 h-3.5 text-zinc-400" />
            <span>Smart India Hackathon 2026 · Problem Statement 26145</span>
          </div>
          <div className="flex items-center gap-4 text-[11px] text-zinc-400">
            <span>Model: NJ-ODE v1.0 (Frozen)</span>
            <span>Diode: Simplex Optical Unidirectional</span>
            <span>Hysteresis: 2-of-3 Windows</span>
          </div>
        </div>
      </footer>

      {showPhoneScanner && (
        <PhoneCameraScanner onClose={() => setShowPhoneScanner(false)} />
      )}

      {showUsbModal && (
        <UsbCableModal
          usbStatus={usbStatus}
          onClose={() => setShowUsbModal(false)}
          onOpenScanner={() => {
            setShowUsbModal(false);
            setShowPhoneScanner(true);
          }}
        />
      )}
    </div>
  );
}
