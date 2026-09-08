import React, { useState } from 'react';
import {
  Cable,
  Usb,
  CheckCircle2,
  AlertCircle,
  Smartphone,
  Laptop,
  Radio,
  WifiOff,
  Copy,
  Check,
  RefreshCw,
  ExternalLink,
  ShieldCheck,
  Zap
} from 'lucide-react';

export default function UsbCableModal({ isOpen, onClose, usbStatus, onRefresh }) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const isConnected = usbStatus?.status === 'connected';
  const phoneUrl = usbStatus?.phone_access_url || 'http://localhost:8000/scan';

  const handleCopyUrl = () => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(phoneUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4 font-mono text-xs">
      <div className="w-full max-w-2xl rounded-2xl border border-zinc-800 bg-[#0d1017] p-5 sm:p-6 shadow-2xl space-y-5 text-zinc-100 max-h-[92vh] overflow-y-auto">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-zinc-800 pb-3.5">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-emerald-950/60 border border-emerald-700/50 text-emerald-400">
              <Cable className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm sm:text-base font-bold text-white flex items-center gap-2">
                PHYSICAL USB WIRE LINK SETUP
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  NO WI-FI REQUIRED
                </span>
              </h3>
              <p className="text-[11px] text-zinc-400">
                100% Physical simplex optical transmission via direct copper wire
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-zinc-400 hover:text-white rounded-lg hover:bg-zinc-800 cursor-pointer"
          >
            ✕
          </button>
        </div>

        {/* Cable Hardware Topology Flowchart */}
        <div className="p-4 rounded-xl bg-[#121520] border border-zinc-800 space-y-3">
          <div className="text-[11px] font-semibold text-zinc-300 uppercase tracking-wider flex items-center justify-between">
            <span>Hardware Data Flow Pipeline</span>
            <span className="text-emerald-400 font-normal">Physical Simplex Link</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 text-center text-[10px]">
            {/* Step 1 */}
            <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 flex flex-col items-center justify-center space-y-1">
              <Laptop className="w-4 h-4 text-violet-400" />
              <span className="font-bold text-zinc-200">System 3 / 2</span>
              <span className="text-zinc-400">In-Zone Generator</span>
              <span className="text-violet-300 text-[9px]">(Flashes QR on Screen)</span>
            </div>

            {/* Step 2 */}
            <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 flex flex-col items-center justify-center space-y-1">
              <Radio className="w-4 h-4 text-amber-400" />
              <span className="font-bold text-zinc-200">Optical Photons</span>
              <span className="text-zinc-400">Camera Ingress</span>
              <span className="text-amber-300 text-[9px]">(Simplex Air-Gap)</span>
            </div>

            {/* Step 3 */}
            <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 flex flex-col items-center justify-center space-y-1">
              <Smartphone className="w-4 h-4 text-sky-400" />
              <span className="font-bold text-zinc-200">Mobile Phone</span>
              <span className="text-zinc-400">Optical Transceiver</span>
              <span className="text-sky-300 text-[9px]">(Wi-Fi Turned OFF)</span>
            </div>

            {/* Step 4 */}
            <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-600/50 flex flex-col items-center justify-center space-y-1">
              <Usb className="w-4 h-4 text-emerald-400" />
              <span className="font-bold text-emerald-200">Physical USB Wire</span>
              <span className="text-zinc-300">System 1 (SOC Laptop)</span>
              <span className="text-emerald-300 text-[9px]">(Type-A/C or Type-C/C)</span>
            </div>
          </div>
        </div>

        {/* Supported Physical Cables Banner */}
        <div className="p-3.5 rounded-xl bg-gradient-to-r from-emerald-950/30 to-violet-950/30 border border-zinc-800 flex items-center justify-between text-[11px]">
          <div>
            <div className="text-zinc-200 font-bold">Supported Physical Cable Standards:</div>
            <div className="text-zinc-400 mt-0.5">
              • <strong>USB Type-A to Type-C</strong> (Standard high-speed copper link)
              <br />
              • <strong>USB Type-C to Type-C</strong> (Modern reversible Thunderbolt / USB-PD link)
            </div>
          </div>
          <div className="p-2 rounded-lg bg-zinc-900 text-emerald-400 border border-zinc-700">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        {/* Live Cable Status HUD */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-zinc-300 font-bold">Active Wire Link Status:</span>
            <button
              onClick={onRefresh}
              className="text-[11px] text-zinc-400 hover:text-zinc-200 flex items-center gap-1 cursor-pointer"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Refresh Status</span>
            </button>
          </div>

          <div className={`p-3 rounded-xl border flex items-center justify-between ${
            isConnected
              ? 'bg-emerald-950/30 border-emerald-600/50 text-emerald-300'
              : 'bg-amber-950/30 border-amber-600/40 text-amber-300'
          }`}>
            <div className="flex items-center gap-2.5">
              {isConnected ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              ) : (
                <AlertCircle className="w-5 h-5 text-amber-400 animate-pulse" />
              )}
              <div>
                <div className="font-bold">
                  {isConnected ? 'PHYSICAL WIRE LINK ACTIVE' : 'WAITING FOR USB CABLE CONNECTION'}
                </div>
                <div className="text-[10px] opacity-80 mt-0.5">
                  Transport Protocol: {usbStatus?.transport || 'Scanning for RNDIS / ADB'}
                </div>
              </div>
            </div>
            <span className="text-xs font-bold uppercase tracking-wider">
              {isConnected ? 'LINK OK' : 'PENDING'}
            </span>
          </div>
        </div>

        {/* Step-by-Step Instructions */}
        <div className="space-y-2.5">
          <span className="text-zinc-300 font-bold">Quick 4-Step Setup Guide:</span>
          
          <div className="space-y-2 text-[11px] text-zinc-400">
            <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 flex items-start gap-2.5">
              <span className="font-bold text-violet-400">1.</span>
              <div>
                <strong className="text-zinc-200">Connect Wire Cable:</strong> Plug USB Type-A to Type-C OR Type-C to Type-C cable between mobile phone and System 1 laptop.
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 flex items-start gap-2.5">
              <span className="font-bold text-emerald-400">2.</span>
              <div>
                <strong className="text-zinc-200">Disable Radio (No Wi-Fi):</strong> Turn OFF Wi-Fi and Mobile Data on the mobile phone. This ensures strictly 0.00% RF leakage.
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 flex items-start gap-2.5">
              <span className="font-bold text-amber-400">3.</span>
              <div>
                <strong className="text-zinc-200">Enable Wire Transport:</strong> On phone Settings &gt; Network &gt; Turn ON <strong className="text-amber-300">USB Tethering</strong> (OR enable Developer Options &gt; USB Debugging for automatic ADB port forwarding).
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 flex items-start gap-2.5">
              <span className="font-bold text-sky-400">4.</span>
              <div className="flex-1">
                <strong className="text-zinc-200">Open Browser on Phone:</strong> In Chrome or Safari on the phone, navigate to the local link:
                <div className="mt-1.5 flex items-center gap-2">
                  <input
                    type="text"
                    readOnly
                    value={phoneUrl}
                    className="flex-1 px-2.5 py-1 rounded bg-black border border-zinc-700 text-emerald-400 font-mono text-xs select-all"
                  />
                  <button
                    onClick={handleCopyUrl}
                    className="px-2.5 py-1 rounded bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs flex items-center gap-1 cursor-pointer transition-colors"
                  >
                    {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-zinc-800 pt-3">
          <div className="text-[10px] text-zinc-500 flex items-center gap-1.5">
            <WifiOff className="w-3.5 h-3.5 text-zinc-400" />
            <span>Zero Wi-Fi Transport Policy • Optical Diode Simplex</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-semibold text-xs cursor-pointer transition-colors"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
