import React, { useState, useEffect, useRef } from 'react';
import { Camera, CameraOff, RefreshCw, ShieldCheck, Zap, AlertCircle, CheckCircle2, Upload, ExternalLink } from 'lucide-react';
import jsQR from 'jsqr';

export default function PhoneCameraScanner({ onClose, onPacketDecoded }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const overlayRef = useRef(null);
  const fileInputRef = useRef(null);

  const [hasCamera, setHasCamera] = useState(true);
  const [cameraActive, setCameraActive] = useState(false);
  const [facingMode, setFacingMode] = useState('environment'); // 'environment' for rear camera
  const [errorMsg, setErrorMsg] = useState('');
  const [decodedCount, setDecodedCount] = useState(0);
  const [lastDecodedPkt, setLastDecodedPkt] = useState(null);
  const [streamFps, setStreamFps] = useState(0);
  const [isInsecureHttp, setIsInsecureHttp] = useState(false);

  const lastDecodedRef = useRef({ time: 0, text: '' });
  const streamRef = useRef(null);

  useEffect(() => {
    if (typeof window !== 'undefined' && !window.isSecureContext && window.location.protocol !== 'https:') {
      setIsInsecureHttp(true);
    }
  }, []);

  // Start Camera Feed
  const startCamera = async () => {
    setErrorMsg('');

    // Check if mediaDevices API is available (only present in Secure Contexts in modern mobile browsers)
    if (typeof navigator === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setHasCamera(false);
      setCameraActive(false);
      if (typeof window !== 'undefined' && !window.isSecureContext) {
        setIsInsecureHttp(true);
        setErrorMsg("Insecure HTTP Context: Mobile Chrome/Safari restrict live video streaming to HTTPS. Use the 'Snap Photo' button below (works 100% on HTTP), or restart the server with --ssl.");
      } else {
        setErrorMsg("Camera API not accessible or permissions denied in this browser.");
      }
      return;
    }

    try {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }

      const constraints = {
        video: {
          facingMode: { ideal: facingMode },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      };

      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.setAttribute('playsinline', 'true');
        await videoRef.current.play();
      }
      setCameraActive(true);
      setHasCamera(true);
    } catch (err) {
      console.error('Camera access error:', err);
      setHasCamera(false);
      setErrorMsg(`Camera error: ${err.message || 'Unable to access camera.'}`);
      setCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  useEffect(() => {
    startCamera();
    return () => {
      stopCamera();
    };
  }, [facingMode]);

  // Optical QR Decoding Loop via jsQR
  useEffect(() => {
    let animId;
    let frameCount = 0;
    let lastFpsTime = performance.now();

    const scanFrame = () => {
      if (videoRef.current && videoRef.current.readyState === videoRef.current.HAVE_ENOUGH_DATA) {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        const overlay = overlayRef.current;

        if (canvas && overlay) {
          const w = video.videoWidth;
          const h = video.videoHeight;

          canvas.width = w;
          canvas.height = h;
          overlay.width = w;
          overlay.height = h;

          const ctx = canvas.getContext('2d', { willReadFrequently: true });
          const oCtx = overlay.getContext('2d');

          ctx.drawImage(video, 0, 0, w, h);
          oCtx.clearRect(0, 0, w, h);

          frameCount++;
          const now = performance.now();
          if (now - lastFpsTime >= 1000) {
            setStreamFps(frameCount);
            frameCount = 0;
            lastFpsTime = now;
          }

          try {
            const imgData = ctx.getImageData(0, 0, w, h);
            const code = jsQR(imgData.data, imgData.width, imgData.height, {
              inversionAttempts: 'dontInvert',
            });

            if (code && code.data) {
              // Draw bounding polygon
              const loc = code.location;
              oCtx.beginPath();
              oCtx.moveTo(loc.topLeftCorner.x, loc.topLeftCorner.y);
              oCtx.lineTo(loc.topRightCorner.x, loc.topRightCorner.y);
              oCtx.lineTo(loc.bottomRightCorner.x, loc.bottomRightCorner.y);
              oCtx.lineTo(loc.bottomLeftCorner.x, loc.bottomLeftCorner.y);
              oCtx.closePath();
              oCtx.lineWidth = 4;
              oCtx.strokeStyle = '#10b981';
              oCtx.stroke();

              // Throttle repeat packets
              const nowSec = Date.now();
              if (code.data !== lastDecodedRef.current.text || nowSec - lastDecodedRef.current.time > 400) {
                lastDecodedRef.current = { text: code.data, time: nowSec };
                handleDecodedData(code.data);
              }
            }
          } catch (e) {
            // Processing error ignored
          }
        }
      }
      animId = requestAnimationFrame(scanFrame);
    };

    animId = requestAnimationFrame(scanFrame);
    return () => cancelAnimationFrame(animId);
  }, []);

  // Handle Photo Capture (Works 100% on HTTP and mobile without WebRTC / getUserMedia restrictions!)
  const handlePhotoCaptured = (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const img = new Image();
      img.onload = () => {
        const c = document.createElement('canvas');
        c.width = img.width;
        c.height = img.height;
        const ctx = c.getContext('2d');
        ctx.drawImage(img, 0, 0);

        try {
          const imgData = ctx.getImageData(0, 0, c.width, c.height);
          const code = jsQR(imgData.data, imgData.width, imgData.height, {
            inversionAttempts: 'attemptBoth',
          });

          if (code && code.data) {
            handleDecodedData(code.data);
          } else {
            alert('No Optical QR Code found in the photo. Please align closer to the screen and ensure the QR code is clearly visible.');
          }
        } catch (err) {
          console.error('Image scan error:', err);
        }
      };
      img.src = event.target.result;
    };
    reader.readAsDataURL(file);
  };

  const handleDecodedData = async (rawText) => {
    try {
      const payload = JSON.parse(rawText);
      const feat = payload.feat || [1.0, 128, 3.5, 1.0, 0];
      const size = payload.size || feat[1] || 128;
      const isThreat = Boolean(payload.atk);
      const src = payload.src || (isThreat ? 'ews-alpha' : 'plc-01');

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

      // Dispatch sequential optical packet hops to Dashboard backend
      const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
      const postEvent = async (ev) => {
        await fetch('/api/packet/event', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(ev),
        }).catch(() => {});
      };

      // Hop 1: In-Zone source node -> tx-diode
      await postEvent({ type: 'packet_transit', from: src, to: 'tx-diode', size, feat, threat: isThreat, timestamp: Date.now() / 1000 });
      await delay(75);

      // Hop 2: tx-diode -> optical-gap
      await postEvent({ type: 'packet_transit', from: 'tx-diode', to: 'optical-gap', size, feat, is_diode_bridge: true, threat: isThreat, timestamp: Date.now() / 1000 });
      await delay(75);

      // Hop 3: optical-gap -> rx-diode (phone camera optical reception)
      await postEvent({ type: 'packet_transit', from: 'optical-gap', to: 'rx-diode', size, feat, is_diode_bridge: true, threat: isThreat, timestamp: Date.now() / 1000 });
      await delay(75);

      // Hop 4: rx-diode -> njode-core (AI model continuous evaluation on your laptop)
      await postEvent({ type: 'packet_transit', from: 'rx-diode', to: 'njode-core', size, feat, threat: isThreat, timestamp: Date.now() / 1000 });

      if (isThreat) {
        await delay(75);
        await postEvent({
          type: 'packet_transit',
          from: 'njode-core',
          to: 'soc-siem',
          size,
          feat,
          threat: true,
          is_alert: true,
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
        src: 'optical-qr',
        size: rawText.length,
        threat: false,
        atk: 'RAW_TEXT',
        time: new Date().toLocaleTimeString(),
      });
    }
  };

  const toggleCameraFacing = () => {
    setFacingMode(prev => (prev === 'environment' ? 'user' : 'environment'));
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
      {/* Hidden Native Camera File Input (Bypasses WebRTC getUserMedia restrictions on HTTP!) */}
      <input
        type="file"
        accept="image/*"
        capture="environment"
        ref={fileInputRef}
        onChange={handlePhotoCaptured}
        className="hidden"
      />

      <div className="bg-[#0c0e14] border border-zinc-800 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col max-h-[92vh]">
        {/* Modal Header */}
        <div className="px-5 py-3.5 border-b border-zinc-800 flex items-center justify-between bg-zinc-950/80">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-950/60 border border-emerald-800/60 text-emerald-400">
              <Camera className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-zinc-100 font-mono flex items-center gap-2">
                PHONE CAMERA OPTICAL QR SCANNER
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  REAL AIR GAP
                </span>
              </h3>
              <p className="text-xs text-zinc-400">
                Point smartphone rear camera at the screen QR code to decode packets across the optical air gap
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {hasCamera && (
              <button
                onClick={toggleCameraFacing}
                className="px-2.5 py-1 text-xs font-mono rounded-lg border border-zinc-800 bg-zinc-900 text-zinc-300 hover:text-white flex items-center gap-1.5 transition-colors cursor-pointer"
                title="Switch between front and back camera"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>{facingMode === 'environment' ? 'Rear Cam' : 'Front Cam'}</span>
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
        <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
          {/* Snap Photo Button - ALWAYS WORKS EVEN ON HTTP */}
          <div className="p-3.5 rounded-xl bg-gradient-to-r from-emerald-950/40 via-zinc-900/60 to-emerald-950/40 border border-emerald-800/50 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div>
              <div className="text-emerald-400 font-semibold text-xs font-mono flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" />
                Instant Phone Camera Capture (Works on HTTP &amp; HTTPS)
              </div>
              <p className="text-[11px] text-zinc-400 mt-0.5">
                Takes a direct high-res photo using your phone's native camera and decodes the QR packet instantly.
              </p>
            </div>
            <button
              onClick={() => fileInputRef.current && fileInputRef.current.click()}
              className="w-full sm:w-auto px-4 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-mono text-xs font-bold flex items-center justify-center gap-2 transition-transform active:scale-95 cursor-pointer shadow-md"
            >
              <Camera className="w-4 h-4" />
              <span>📸 SNAP PHOTO OF SCREEN QR</span>
            </button>
          </div>

          {/* Video / Camera Viewport */}
          <div className="relative aspect-video w-full rounded-xl overflow-hidden bg-black border border-zinc-800 flex items-center justify-center">
            {errorMsg ? (
              <div className="p-6 text-center text-zinc-400 max-w-lg space-y-3 font-mono text-xs">
                <AlertCircle className="w-8 h-8 text-amber-400 mx-auto" />
                <p className="text-zinc-200 font-semibold text-sm">Mobile Browser Camera Restriction</p>
                <p className="text-zinc-400 text-[11px] leading-relaxed">
                  Modern mobile browsers (Chrome &amp; Safari) only expose continuous WebRTC video streams over <strong className="text-emerald-400">HTTPS</strong>.
                </p>
                
                <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-2">
                  <button
                    onClick={() => fileInputRef.current && fileInputRef.current.click()}
                    className="w-full sm:w-auto px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <Camera className="w-4 h-4" />
                    <span>Use Native Phone Camera Instead</span>
                  </button>
                  <button
                    onClick={startCamera}
                    className="w-full sm:w-auto px-3 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs cursor-pointer"
                  >
                    Retry Stream
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
                <canvas ref={canvasRef} className="hidden" />
                <canvas
                  ref={overlayRef}
                  className="absolute inset-0 w-full h-full pointer-events-none object-contain"
                />

                {/* Reticle / Viewfinder guide */}
                <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
                  <div className="w-56 h-56 border-2 border-dashed border-emerald-500/50 rounded-2xl flex items-center justify-center">
                    <span className="text-[10px] font-mono text-emerald-400/70 bg-black/60 px-2 py-0.5 rounded">
                      ALIGN QR HERE
                    </span>
                  </div>
                </div>

                {/* Live FPS tag */}
                <div className="absolute top-3 right-3 px-2 py-1 rounded bg-black/60 border border-zinc-800 text-[10px] font-mono text-emerald-400">
                  {streamFps} FPS
                </div>
              </>
            )}
          </div>

          {/* Last Decoded Optical Packet Live Inspector */}
          <div className="p-3.5 rounded-xl border border-zinc-800 bg-[#07090e] font-mono text-xs space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-zinc-400 flex items-center gap-1.5 font-semibold text-[11px] uppercase tracking-wider">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                Latest Decoded Optical Packet
              </span>
              {lastDecodedPkt ? (
                <span className="text-[10px] text-zinc-500">Decoded at {lastDecodedPkt.time}</span>
              ) : (
                <span className="text-[10px] text-amber-500">Waiting for QR in camera frame...</span>
              )}
            </div>

            {lastDecodedPkt ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px]">
                <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800/80">
                  <span className="text-zinc-500 block text-[10px]">Seq ID</span>
                  <span className="text-zinc-200 font-bold">#{lastDecodedPkt.seq}</span>
                </div>
                <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800/80">
                  <span className="text-zinc-500 block text-[10px]">Source Node</span>
                  <span className="text-sky-400 font-bold">{lastDecodedPkt.src}</span>
                </div>
                <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800/80">
                  <span className="text-zinc-500 block text-[10px]">Packet Size</span>
                  <span className="text-emerald-400 font-bold">{lastDecodedPkt.size} Bytes</span>
                </div>
                <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800/80">
                  <span className="text-zinc-500 block text-[10px]">Status</span>
                  <span className={lastDecodedPkt.threat ? 'text-rose-400 font-bold' : 'text-emerald-400 font-bold'}>
                    {lastDecodedPkt.threat ? '🚨 ATTACK' : '✅ BENIGN'}
                  </span>
                </div>
              </div>
            ) : (
              <div className="p-4 text-center text-zinc-500 text-xs italic">
                Hold phone camera up to the screen where the QR Diode is running, or tap "Snap Photo".
              </div>
            )}
          </div>

          {/* Alternative 2: Enable HTTPS for 30fps streaming or use IP Webcam */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono text-xs">
            <div className="p-3 rounded-xl border border-zinc-800/80 bg-zinc-950/60 space-y-1.5">
              <div className="text-zinc-300 font-semibold text-xs flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-emerald-400" />
                Enable 30 FPS Live Video (HTTPS)
              </div>
              <p className="text-[10px] text-zinc-400">
                Restart server with SSL on laptop:
              </p>
              <div className="p-1.5 rounded bg-black border border-zinc-800 text-emerald-400 text-[10px] select-all">
                python run.py soc --ssl
              </div>
              <p className="text-[10px] text-zinc-500">
                Then open <code className="text-sky-400">https://&lt;laptop-ip&gt;:8501</code> and accept self-signed cert.
              </p>
            </div>

            <div className="p-3 rounded-xl border border-zinc-800/80 bg-zinc-950/60 space-y-1.5">
              <div className="text-zinc-300 font-semibold text-xs flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-sky-400" />
                Python IP Webcam Streaming
              </div>
              <p className="text-[10px] text-zinc-400">
                Using IP Webcam app on phone:
              </p>
              <div className="p-1.5 rounded bg-black border border-zinc-800 text-sky-400 text-[10px] select-all">
                python run.py scan --phone 10.1.45.X
              </div>
              <p className="text-[10px] text-zinc-500">
                Bypasses phone browser entirely by reading camera stream in Python OpenCV!
              </p>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 border-t border-zinc-800 bg-zinc-950 flex items-center justify-between text-xs font-mono">
          <span className="text-zinc-400 text-[11px]">
            Physical Simplex Air Gap: Photons Only · Zero Reverse Copper Bit Path
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium transition-colors cursor-pointer"
          >
            Close Scanner
          </button>
        </div>
      </div>
    </div>
  );
}
