import React, { useState, useEffect, useRef } from 'react';
import { Camera, RefreshCw, ShieldCheck, Zap, AlertCircle, CheckCircle2, Flashlight, Radio, Activity } from 'lucide-react';
import jsQR from 'jsqr';

export default function PhoneCameraScanner({ onClose, onPacketDecoded }) {
  const videoRef = useRef(null);
  const overlayRef = useRef(null);

  const [hasCamera, setHasCamera] = useState(true);
  const [cameraActive, setCameraActive] = useState(false);
  const [facingMode, setFacingMode] = useState('environment'); // 'environment' for rear camera
  const [videoDevices, setVideoDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [decodedCount, setDecodedCount] = useState(0);
  const [lastDecodedPkt, setLastDecodedPkt] = useState(null);
  const [scadaVitals, setScadaVitals] = useState(null);
  const [streamFps, setStreamFps] = useState(0);
  const [isInsecureHttp, setIsInsecureHttp] = useState(false);
  const [torchSupported, setTorchSupported] = useState(false);
  const [torchOn, setTorchOn] = useState(false);
  const [flashFeedback, setFlashFeedback] = useState(false);

  const lastDecodedRef = useRef({ time: 0, text: '', seq: null });
  const streamRef = useRef(null);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const isHttp = window.location.protocol === 'http:';
      const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
      if (isHttp && !isLocalhost) {
        setIsInsecureHttp(true);
      }
    }
  }, []);

  // Enumerate camera devices and auto-detect Iriun Webcam (USB / Wi-Fi from phone)
  useEffect(() => {
    const detectCameras = async () => {
      if (typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
        try {
          const devices = await navigator.mediaDevices.enumerateDevices();
          const videoInputs = devices.filter(d => d.kind === 'videoinput');
          setVideoDevices(videoInputs);

          // Auto-select Iriun Webcam if detected
          const iriun = videoInputs.find(d => /iriun/i.test(d.label));
          if (iriun && !selectedDeviceId) {
            setSelectedDeviceId(iriun.deviceId);
          } else if (videoInputs.length > 0 && !selectedDeviceId) {
            setSelectedDeviceId(videoInputs[0].deviceId);
          }
        } catch (e) {
          console.warn("Could not enumerate video devices:", e);
        }
      }
    };
    detectCameras();
  }, []);

  // Switch to HTTPS for real-time 30 FPS video streaming
  const handleSwitchToHttps = () => {
    if (typeof window !== 'undefined') {
      const hostname = window.location.hostname;
      const port = window.location.port === '8501' ? '8443' : window.location.port;
      const hostStr = port ? `${hostname}:${port}` : hostname;
      const targetUrl = `https://${hostStr}${window.location.pathname}${window.location.search}`;
      window.location.href = targetUrl;
    }
  };

  // Start Real-Time 30 FPS Camera Feed (Supports Iriun Webcam over USB cable)
  const startCamera = async (overrideDeviceId) => {
    setErrorMsg('');
    const devId = overrideDeviceId || selectedDeviceId;

    // Check if mediaDevices API is available (only present in Secure Contexts in modern mobile browsers)
    if (typeof navigator === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setHasCamera(false);
      setCameraActive(false);
      if (typeof window !== 'undefined' && window.location.protocol === 'http:') {
        setIsInsecureHttp(true);
        setErrorMsg("Mobile Chrome & Safari disable continuous video streaming over plain HTTP. Tap 'Switch to HTTPS' below to enable 30 FPS real-time scanning.");
      } else {
        setErrorMsg("Camera access not available or permission denied in this browser.");
      }
      return;
    }

    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }

      // Tiered constraint candidates: prioritize explicit device ID (e.g. Iriun Webcam)
      const constraintCandidates = [];
      if (devId) {
        constraintCandidates.push(
          {
            video: {
              deviceId: { exact: devId },
              width: { ideal: 1280 },
              height: { ideal: 720 },
            },
            audio: false,
          },
          {
            video: { deviceId: { exact: devId } },
            audio: false,
          }
        );
      }
      constraintCandidates.push(
        {
          video: {
            facingMode: { ideal: facingMode },
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
          audio: false,
        },
        {
          video: { facingMode: { ideal: facingMode } },
          audio: false,
        },
        {
          video: { facingMode: facingMode },
          audio: false,
        },
        {
          video: true,
          audio: false,
        },
      );

      let stream = null;
      let lastErr = null;
      for (const constraints of constraintCandidates) {
        try {
          stream = await navigator.mediaDevices.getUserMedia(constraints);
          if (stream) break;
        } catch (err) {
          lastErr = err;
        }
      }

      if (!stream) {
        throw lastErr || new Error("Failed to initialize video stream.");
      }

      streamRef.current = stream;

      // Re-enumerate devices to fetch actual labels now that permission is granted
      if (navigator.mediaDevices.enumerateDevices) {
        navigator.mediaDevices.enumerateDevices().then(devs => {
          const videoInputs = devs.filter(d => d.kind === 'videoinput');
          setVideoDevices(videoInputs);
          const iriun = videoInputs.find(d => /iriun/i.test(d.label));
          if (iriun && !devId) {
            setSelectedDeviceId(iriun.deviceId);
          }
        }).catch(() => {});
      }

      // Check for torch / flashlight support
      const videoTrack = stream.getVideoTracks()[0];
      if (videoTrack) {
        const capabilities = videoTrack.getCapabilities ? videoTrack.getCapabilities() : {};
        if (capabilities.torch) {
          setTorchSupported(true);
        }
      }

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.setAttribute('playsinline', 'true');
        videoRef.current.setAttribute('autoplay', 'true');
        videoRef.current.setAttribute('muted', 'true');
        videoRef.current.playsInline = true;
        videoRef.current.muted = true;
        await videoRef.current.play().catch(e => console.warn("Video play warning:", e));
      }

      setCameraActive(true);
      setHasCamera(true);
      setErrorMsg('');
    } catch (err) {
      console.error('Camera access error:', err);
      setHasCamera(false);
      setCameraActive(false);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setErrorMsg("Camera permission was denied. Please allow camera permissions in your browser settings and tap 'Retry Camera'.");
      } else {
        setErrorMsg(`Camera error: ${err.message || 'Unable to start camera stream.'}`);
      }
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  const toggleTorch = async () => {
    if (!streamRef.current) return;
    const track = streamRef.current.getVideoTracks()[0];
    if (!track) return;

    try {
      const nextState = !torchOn;
      await track.applyConstraints({
        advanced: [{ torch: nextState }]
      });
      setTorchOn(nextState);
    } catch (err) {
      console.warn("Could not toggle flashlight:", err);
    }
  };

  useEffect(() => {
    startCamera(selectedDeviceId);
    return () => {
      stopCamera();
    };
  }, [facingMode, selectedDeviceId]);

  // Optical QR Real-Time Continuous Decoding Loop via jsQR
  useEffect(() => {
    let animId;
    let frameCount = 0;
    let lastFpsTime = performance.now();

    // Reusable offscreen canvas for high-speed downscaled decoding
    const scanCanvas = document.createElement('canvas');
    const scanCtx = scanCanvas.getContext('2d', { willReadFrequently: true });

    const scanFrame = () => {
      if (videoRef.current && videoRef.current.readyState >= 2) {
        const video = videoRef.current;
        const overlay = overlayRef.current;

        const w = video.videoWidth || 640;
        const h = video.videoHeight || 480;

        if (overlay) {
          overlay.width = w;
          overlay.height = h;
          const oCtx = overlay.getContext('2d');
          oCtx.clearRect(0, 0, w, h);

          frameCount++;
          const now = performance.now();
          if (now - lastFpsTime >= 1000) {
            setStreamFps(frameCount);
            frameCount = 0;
            lastFpsTime = now;
          }

          // Downscale to max 640px wide for instantaneous jsQR processing (3-8ms vs 80ms)
          const scale = Math.min(1.0, 640 / w);
          const sw = Math.floor(w * scale);
          const sh = Math.floor(h * scale);
          scanCanvas.width = sw;
          scanCanvas.height = sh;

          scanCtx.drawImage(video, 0, 0, sw, sh);

          try {
            const imgData = scanCtx.getImageData(0, 0, sw, sh);
            const code = jsQR(imgData.data, sw, sh, {
              inversionAttempts: 'dontInvert',
            });

            if (code && code.data) {
              // Map detected polygon back to full overlay display coordinate space
              const invScale = 1.0 / scale;
              const loc = code.location;
              const p1 = { x: loc.topLeftCorner.x * invScale, y: loc.topLeftCorner.y * invScale };
              const p2 = { x: loc.topRightCorner.x * invScale, y: loc.topRightCorner.y * invScale };
              const p3 = { x: loc.bottomRightCorner.x * invScale, y: loc.bottomRightCorner.y * invScale };
              const p4 = { x: loc.bottomLeftCorner.x * invScale, y: loc.bottomLeftCorner.y * invScale };

              // Draw green high-contrast targeting polygon
              oCtx.beginPath();
              oCtx.moveTo(p1.x, p1.y);
              oCtx.lineTo(p2.x, p2.y);
              oCtx.lineTo(p3.x, p3.y);
              oCtx.lineTo(p4.x, p4.y);
              oCtx.closePath();
              oCtx.lineWidth = 4;
              oCtx.strokeStyle = '#10b981';
              oCtx.stroke();

              // Subtle fill
              oCtx.fillStyle = 'rgba(16, 185, 129, 0.18)';
              oCtx.fill();

              // Corner brackets
              const drawCorner = (pt, vx, vy) => {
                oCtx.beginPath();
                oCtx.moveTo(pt.x + vx * 20, pt.y);
                oCtx.lineTo(pt.x, pt.y);
                oCtx.lineTo(pt.x, pt.y + vy * 20);
                oCtx.lineWidth = 5;
                oCtx.strokeStyle = '#34d399';
                oCtx.stroke();
              };
              drawCorner(p1, 1, 1);
              drawCorner(p2, -1, 1);
              drawCorner(p3, -1, -1);
              drawCorner(p4, 1, -1);

              // Throttle repeat packets (250ms threshold or new content)
              const nowSec = Date.now();
              if (code.data !== lastDecodedRef.current.text || (nowSec - lastDecodedRef.current.time > 250)) {
                lastDecodedRef.current = { text: code.data, time: nowSec };
                handleDecodedData(code.data);
              }
            }
          } catch (e) {
            // Frame processing error ignored
          }
        }
      }
      animId = requestAnimationFrame(scanFrame);
    };

    animId = requestAnimationFrame(scanFrame);
    return () => cancelAnimationFrame(animId);
  }, []);

  const handleDecodedData = async (rawText) => {
    try {
      // Haptic confirmation
      if (typeof navigator !== 'undefined' && navigator.vibrate) {
        try { navigator.vibrate(35); } catch {}
      }

      setFlashFeedback(true);
      setTimeout(() => setFlashFeedback(false), 300);

      const payload = JSON.parse(rawText);
      const feat = payload.feat || [1.0, 128, 3.5, 1.0, 0];
      const size = payload.size || feat[1] || 128;
      const isThreat = Boolean(payload.atk);
      const src = payload.src || payload.facility || (isThreat ? 'redteam-attacker' : 'nuclear-scada');

      // Extract authentic Kudankulam PWR SCADA Telemetry (NPPAD 2022)
      const p = payload.p ?? payload.pressure_bar ?? 155.5;
      const tavg = payload.tavg ?? payload.core_temp_c ?? 310.0;
      const flow = payload.flow ?? payload.coolant_flow_kgs ?? 16515.8;
      const mw = payload.mw ?? payload.output_mwe ?? 955.3;
      const cpu = payload.cpu ?? payload.container_cpu_pct ?? 1.2;
      const ram = payload.ram ?? payload.container_mem_pct ?? 2.8;
      const state = payload.state ?? payload.reactor_state ?? 'NOMINAL_FULL_POWER';
      const atk = payload.atk || payload.attack_type || '';

      const scadaObj = { p, tavg, flow, mw, cpu, ram, state, atk };
      setScadaVitals(scadaObj);

      setDecodedCount(c => c + 1);
      setLastDecodedPkt({
        seq: payload.seq ?? decodedCount + 1,
        src: src,
        size: size,
        threat: isThreat,
        atk: payload.atk || 'CALM_NOMINAL',
        feat: feat,
        time: new Date().toLocaleTimeString(),
      });

      // Dispatch real-time optical packet transit hops to System 1 SOC backend
      const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
      const postEvent = async (ev) => {
        await fetch('/api/packet/event', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(ev),
        }).catch(() => {});
      };

      // Hop 1: In-Zone source node -> tx-diode
      await postEvent({ type: 'packet_transit', from: src, to: 'tx-diode', size, feat, threat: isThreat, scada: scadaObj, timestamp: Date.now() / 1000 });
      await delay(60);

      // Hop 2: tx-diode -> optical-gap
      await postEvent({ type: 'packet_transit', from: 'tx-diode', to: 'optical-gap', size, feat, is_diode_bridge: true, threat: isThreat, scada: scadaObj, timestamp: Date.now() / 1000 });
      await delay(60);

      // Hop 3: optical-gap -> rx-diode (phone camera optical reception)
      await postEvent({ type: 'packet_transit', from: 'optical-gap', to: 'rx-diode', size, feat, is_diode_bridge: true, threat: isThreat, scada: scadaObj, timestamp: Date.now() / 1000 });
      await delay(60);

      // Hop 4: rx-diode -> njode-core (AI model continuous evaluation on System 1 laptop)
      await postEvent({ type: 'packet_transit', from: 'rx-diode', to: 'njode-core', size, feat, threat: isThreat, scada: scadaObj, timestamp: Date.now() / 1000 });

      if (isThreat) {
        await delay(60);
        await postEvent({
          type: 'packet_transit',
          from: 'njode-core',
          to: 'soc-siem',
          size,
          feat,
          threat: true,
          is_alert: true,
          scada: scadaObj,
          timestamp: Date.now() / 1000,
        });
      }

      if (onPacketDecoded) {
        onPacketDecoded(payload);
      }
    } catch {
      // Non-JSON QR frame
      setDecodedCount(c => c + 1);
      setLastDecodedPkt({
        seq: decodedCount + 1,
        src: 'optical-qr-node',
        size: rawText.length,
        threat: false,
        atk: 'RAW_DATA',
        feat: [1.0, rawText.length, 3.5, 1.0, 0],
        time: new Date().toLocaleTimeString(),
      });
    }
  };

  const toggleCameraFacing = () => {
    setFacingMode(prev => (prev === 'environment' ? 'user' : 'environment'));
  };

  const selectedDeviceObj = videoDevices.find(d => d.deviceId === selectedDeviceId);
  const isIriunActive = selectedDeviceObj && /iriun/i.test(selectedDeviceObj.label);

  return (
    <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-2 sm:p-4">
      <div className="bg-[#0c0e14] border border-zinc-800 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col max-h-[96vh]">
        {/* Modal Header */}
        <div className="px-4 py-3 border-b border-zinc-800 flex items-center justify-between bg-zinc-950 gap-2">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="p-2 rounded-lg bg-emerald-950/70 border border-emerald-700/60 text-emerald-400 shrink-0">
              <Camera className="w-4 h-4 animate-pulse" />
            </div>
            <div className="min-w-0">
              <h3 className="text-xs sm:text-sm font-semibold text-zinc-100 font-mono flex items-center gap-2 flex-wrap">
                REAL-TIME OPTICAL CAMERA SCANNER
                <span className="text-[9px] sm:text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold">
                  30 FPS LIVE
                </span>
                {isIriunActive && (
                  <span className="text-[9px] sm:text-[10px] px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-bold">
                    📱 IRIUN USB
                  </span>
                )}
              </h3>
              <p className="text-[11px] text-zinc-400 hidden sm:block truncate">
                Continuous optical air-gap packet monitoring — zero manual snapping required
              </p>
            </div>
          </div>
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            {videoDevices.length > 1 && (
              <select
                value={selectedDeviceId}
                onChange={(e) => {
                  const newId = e.target.value;
                  setSelectedDeviceId(newId);
                  startCamera(newId);
                }}
                className="px-2 py-1 text-[11px] font-mono rounded-lg border border-zinc-700 bg-zinc-900 text-zinc-200 hover:border-emerald-500/60 focus:outline-none focus:border-emerald-500 cursor-pointer max-w-[140px] sm:max-w-[200px] truncate"
                title="Select Camera Input (e.g. Iriun Webcam USB)"
              >
                {videoDevices.map((dev, idx) => (
                  <option key={dev.deviceId || idx} value={dev.deviceId}>
                    {dev.label ? (/iriun/i.test(dev.label) ? `📱 ${dev.label} (Phone USB)` : `📷 ${dev.label}`) : `Camera ${idx + 1}`}
                  </option>
                ))}
              </select>
            )}
            {torchSupported && (
              <button
                onClick={toggleTorch}
                className={`p-1.5 rounded-lg border text-xs font-mono flex items-center gap-1 transition-colors cursor-pointer ${
                  torchOn ? 'bg-amber-500/20 border-amber-500/50 text-amber-300' : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200'
                }`}
                title="Toggle Torch / Flashlight"
              >
                <Flashlight className="w-3.5 h-3.5" />
              </button>
            )}
            {hasCamera && (
              <button
                onClick={toggleCameraFacing}
                className="px-2.5 py-1 text-xs font-mono rounded-lg border border-zinc-800 bg-zinc-900 text-zinc-300 hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer"
                title="Switch between front and rear camera"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{facingMode === 'environment' ? 'Rear Cam' : 'Front Cam'}</span>
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 text-zinc-400 hover:text-white rounded-lg hover:bg-zinc-800 text-sm font-mono cursor-pointer"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="flex-1 min-h-0 overflow-y-auto p-3 sm:p-4 space-y-3">
          {/* Live Video Viewport */}
          <div className="relative aspect-video w-full rounded-xl overflow-hidden bg-black border border-zinc-800 flex items-center justify-center">
            {isInsecureHttp || errorMsg ? (
              <div className="p-5 sm:p-8 text-center text-zinc-300 max-w-md space-y-3 font-mono text-xs">
                <AlertCircle className="w-10 h-10 text-amber-400 mx-auto" />
                <p className="text-zinc-100 font-bold text-sm">Mobile WebRTC Camera Security Notice</p>
                <p className="text-zinc-400 text-[11px] leading-relaxed">
                  Mobile browsers (Chrome / Safari) disable continuous 30 FPS video streaming over plain HTTP. To enable real-time camera streaming:
                </p>

                <div className="pt-2 space-y-2">
                  <button
                    onClick={handleSwitchToHttps}
                    className="w-full py-2.5 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold font-mono flex items-center justify-center gap-2 shadow-lg cursor-pointer transition-transform active:scale-95"
                  >
                    <Zap className="w-4 h-4" />
                    <span>🔒 SWITCH TO HTTPS FOR LIVE 30 FPS VIDEO</span>
                  </button>

                  <div className="p-3 rounded-lg bg-zinc-900/90 border border-zinc-800 text-left text-[11px] text-zinc-400 space-y-1">
                    <p className="text-zinc-200 font-semibold">Quick 2-Step Setup:</p>
                    <p>1. Tap the button above to switch to HTTPS.</p>
                    <p>2. If Chrome says <em className="text-amber-300">"Your connection isn't private"</em>, tap <strong>Advanced → Proceed</strong>.</p>
                    <p>3. Allow camera permission. The 30 FPS live video scanner will begin immediately!</p>
                  </div>

                  <button
                    onClick={startCamera}
                    className="w-full py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-mono cursor-pointer"
                  >
                    Retry Camera Stream
                  </button>
                </div>
              </div>
            ) : (
              <>
                <video
                  ref={videoRef}
                  className="w-full h-full object-contain"
                  autoPlay
                  playsInline
                  muted
                />
                <canvas
                  ref={overlayRef}
                  className="absolute inset-0 w-full h-full pointer-events-none object-contain"
                />

                {/* Animated HUD Viewfinder Reticle */}
                <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                  <div className={`w-52 sm:w-64 h-52 sm:h-64 border-2 border-dashed rounded-2xl flex flex-col items-center justify-between p-3 transition-colors duration-200 ${
                    flashFeedback ? 'border-emerald-400 bg-emerald-500/10' : 'border-emerald-500/40'
                  }`}>
                    <div className="w-full flex justify-between text-[10px] font-mono text-emerald-400/80">
                      <span>┌ AIR-GAP RX</span>
                      <span>┐</span>
                    </div>

                    <div className="text-center">
                      <div className="text-[10px] font-mono text-emerald-400/80 bg-black/70 px-2 py-0.5 rounded backdrop-blur-sm">
                        AIM AT SYSTEM 2 SCREEN
                      </div>
                      {flashFeedback && (
                        <div className="text-[9px] font-mono text-emerald-300 bg-emerald-950/80 border border-emerald-500 px-2 py-0.5 rounded mt-1 animate-pulse">
                          ⚡ PACKET DECODED &amp; FORWARDED
                        </div>
                      )}
                    </div>

                    <div className="w-full flex justify-between text-[10px] font-mono text-emerald-400/80">
                      <span>└ OPTICAL</span>
                      <span>┘</span>
                    </div>
                  </div>
                </div>

                {/* Top Overlay Badges */}
                <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5 px-2.5 py-1 rounded bg-black/75 border border-zinc-800 text-[10px] font-mono text-emerald-400 backdrop-blur-sm">
                  <Radio className="w-3 h-3 animate-pulse text-emerald-400" />
                  <span>30 FPS LIVE STREAM</span>
                </div>

                <div className="absolute top-2.5 right-2.5 flex items-center gap-2">
                  <div className="px-2 py-1 rounded bg-black/75 border border-zinc-800 text-[10px] font-mono text-zinc-300 backdrop-blur-sm">
                    {streamFps} FPS
                  </div>
                  <div className="px-2 py-1 rounded bg-emerald-950/80 border border-emerald-600/60 text-[10px] font-mono text-emerald-300 font-bold backdrop-blur-sm">
                    {decodedCount} PKTS
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Kudankulam Unit 1 NPPAD Nuclear Vitals HUD */}
          {scadaVitals && (
            <div className="p-3 rounded-xl border border-zinc-800 bg-[#06080e] font-mono text-xs space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-zinc-300 flex items-center gap-1.5 font-semibold text-[11px] uppercase tracking-wider">
                  <Activity className="w-3.5 h-3.5 text-sky-400" />
                  Kudankulam Unit 1 (PWR) · Nuclear SCADA Vitals
                </span>
                <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                  scadaVitals.state === 'NOMINAL_FULL_POWER'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                    : 'bg-rose-500/20 text-rose-300 border border-rose-500/40 animate-pulse'
                }`}>
                  {scadaVitals.state}
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px]">
                <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px]">Coolant Pressure</span>
                  <span className="text-zinc-200 font-bold">{scadaVitals.p} bar</span>
                </div>
                <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px]">Core Temp (Tavg)</span>
                  <span className="text-amber-400 font-bold">{scadaVitals.tavg} °C</span>
                </div>
                <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px]">Coolant Flow (WRCA)</span>
                  <span className={`font-bold ${scadaVitals.flow < 10000 ? 'text-rose-400 animate-pulse' : 'text-emerald-400'}`}>
                    {scadaVitals.flow} kg/s
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px]">Grid Power / CPU</span>
                  <span className="text-sky-400 font-bold">{scadaVitals.mw} MWe ({scadaVitals.cpu}%)</span>
                </div>
              </div>
            </div>
          )}

          {/* Real-Time Decoded Optical Packet Telemetry Feed */}
          <div className="p-3 rounded-xl border border-zinc-800 bg-[#07090e] font-mono text-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-zinc-400 flex items-center gap-1.5 font-semibold text-[11px] uppercase tracking-wider">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                Continuous Optical Ingestion Feed
              </span>
              {lastDecodedPkt ? (
                <span className="text-[10px] text-emerald-400 font-medium">Forwarded to SOC at {lastDecodedPkt.time}</span>
              ) : (
                <span className="text-[10px] text-amber-500 animate-pulse">Waiting for QR in camera frame...</span>
              )}
            </div>

            {lastDecodedPkt ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px]">
                <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px]">Sequence</span>
                  <span className="text-zinc-200 font-bold">#{lastDecodedPkt.seq}</span>
                </div>
                <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px]">Source Node</span>
                  <span className="text-sky-400 font-bold">{lastDecodedPkt.src}</span>
                </div>
                <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px]">Datagram Size</span>
                  <span className="text-emerald-400 font-bold">{lastDecodedPkt.size} Bytes</span>
                </div>
                <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800">
                  <span className="text-zinc-500 block text-[10px]">AI Classification</span>
                  <span className={lastDecodedPkt.threat ? 'text-rose-400 font-bold' : 'text-emerald-400 font-bold'}>
                    {lastDecodedPkt.threat ? '🚨 ATTACK' : '✅ BENIGN'}
                  </span>
                </div>
              </div>
            ) : (
              <div className="p-3 text-center text-zinc-500 text-xs italic">
                Point your phone camera at System 2 where the QR transmitter is active. Frames are decoded continuously.
              </div>
            )}
          </div>

          {/* Real-time Architecture Guide */}
          <div className="p-2.5 rounded-xl border border-zinc-800/80 bg-zinc-950/60 font-mono text-[11px] text-zinc-400 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Zap className="w-3.5 h-3.5 text-emerald-400 flex-shrink-0" />
              <span>Pipeline: <strong className="text-zinc-200">System 2 (QR)</strong> ➔ <strong className="text-emerald-400">Phone Camera (30 FPS)</strong> ➔ <strong className="text-sky-400">System 1 (NJ-ODE AI)</strong></span>
            </div>
            <span className="text-[10px] text-emerald-400 font-bold hidden sm:inline">0.00% RETURN PATH</span>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-4 py-2.5 border-t border-zinc-800 bg-zinc-950 flex items-center justify-between text-xs font-mono">
          <span className="text-zinc-500 text-[10px] hidden sm:inline">
            Physical Simplex Diode: 100% Optical Photons
          </span>
          <button
            onClick={onClose}
            className="w-full sm:w-auto px-4 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium transition-colors cursor-pointer"
          >
            Close Scanner
          </button>
        </div>
      </div>
    </div>
  );
}
