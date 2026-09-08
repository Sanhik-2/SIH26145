"""
CHRONOS Full-Stack SOC Console Server
Integrates the React Cyber-Defense Dashboard with the AI Ingestion Engine.
Serves both REST / SSE API endpoints and the compiled React production SPA.

Run:
  python dashboard/server.py
  or:
  python run.py soc
"""
import argparse
import asyncio
import json
import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List, Dict, Any

import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, FileResponse, StreamingResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from diode.usb_bridge import get_usb_status
except ImportError:
    def get_usb_status(preferred_port: int = 8000) -> Dict[str, Any]:
        return {
            "status": "waiting_for_cable",
            "transport": "UNKNOWN",
            "is_physical_wire": False,
            "wifi_mode": False,
            "supported_cables": ["USB Type-A to Type-C", "USB Type-C to Type-C"],
            "steps": ["Connect USB cable from phone to laptop"]
        }

DIST_DIR = REPO_ROOT / "frontend" / "dist"
frontend_dir = REPO_ROOT / "frontend"
if (frontend_dir / "package.json").exists() and (not (DIST_DIR / "index.html").exists() or not (frontend_dir / "node_modules").exists()):
    import subprocess
    is_win = sys.platform == "win32"
    if not (frontend_dir / "node_modules").exists():
        print("[i] Installing frontend dependencies (npm install)...")
        try:
            subprocess.run(["npm", "install"], cwd=str(frontend_dir), check=True, shell=is_win)
        except Exception as e:
            print(f"[!] Warning: npm install failed: {e}")
    if not (DIST_DIR / "index.html").exists():
        print("[i] Building React frontend distribution bundle (npm run build)...")
        try:
            subprocess.run(["npm", "run", "build"], cwd=str(frontend_dir), check=True, shell=is_win)
        except Exception as e:
            print(f"[!] Warning: Frontend build failed: {e}")

ALERTS_PATHS = [
    REPO_ROOT / "results" / "demo_alerts.jsonl",
    REPO_ROOT / "alerts.jsonl",
]
CHECKPOINT_PATH = REPO_ROOT / "checkpoints" / "njode_telemetry.pt"
CAMPAIGN_PATH = REPO_ROOT / "results" / "campaign.json"
EVAL_PATH = REPO_ROOT / "results" / "eval.json"


BENCHMARK_PATH = REPO_ROOT / "results" / "benchmark.json"


_feeder = None
_model = None
try:
    import torch
    from features.extractor import Packet
    from features.windowing import LiveFeeder
    from models.njode import NJODE
    if CHECKPOINT_PATH.exists():
        _model = NJODE.load(str(CHECKPOINT_PATH), device="cpu")
    else:
        _model = NJODE(d_x=5, d_h=6, hidden=16, grid_step=0.01, horizon=0.5)
        _model.threshold.copy_(torch.tensor(2.464))
        _model.eval()
    _feeder = LiveFeeder(model=_model, window_s=10.0, stride_s=2.0, hysteresis_n=2, hysteresis_m=3, device="cpu")
    print(f"[✓] Dashboard server loaded NJ-ODE AI core (tau={_feeder.model.threshold.item():.4f})")
except Exception as e:
    print(f"[!] LiveFeeder init warning: {e}")


def load_checkpoint_info() -> Dict[str, Any]:
    info = {
        "version": "1.1",
        "tau": 2.810,
        "checkpoint": str(CHECKPOINT_PATH.relative_to(REPO_ROOT)) if CHECKPOINT_PATH.exists() else "none",
        "modelName": "NJ-ODE Continuous Simplex Guard (Protocol v1.1)",
        "features": ["iat", "bytes", "entropy", "burst", "direction"],
        "d_x": 5,
        "device": "cpu",
        "diodeStatus": "PHYSICAL_OPTICAL_AIRGAP",
        "ingestionLatencyMs": 1.1,
    }
    if CHECKPOINT_PATH.exists():
        try:
            import torch
            ckpt = torch.load(CHECKPOINT_PATH, map_location="cpu")
            if isinstance(ckpt, dict):
                cfg = ckpt.get("config", {})
                info["version"] = str(cfg.get("version", "1.1"))
                info["features"] = cfg.get("features", info["features"])
                info["d_x"] = cfg.get("d_x", 5)
                sd = ckpt.get("state_dict", {})
                if "threshold" in sd:
                    info["tau"] = round(float(sd["threshold"].item()), 4)
        except Exception:
            pass
    return info


def read_recent_alerts(limit: int = 150) -> List[Dict[str, Any]]:
    alerts = []
    for p in ALERTS_PATHS:
        if p.exists():
            try:
                lines = p.read_text().splitlines()[-limit:]
                for ln in lines:
                    ln = ln.strip()
                    if not ln:
                        continue
                    try:
                        alerts.append(json.loads(ln))
                    except Exception:
                        continue
            except Exception:
                pass
            if alerts:
                break
    return alerts[-limit:]


# Global in-memory broadcast manager for SSE clients
_sse_subscribers: List[asyncio.Queue] = []
_recent_packets: List[Dict[str, Any]] = []
_packet_stats: Dict[str, Any] = {
    "total_transited": 0,
    "last_transit_time": None,
    "active_flows": 0,
}

# Real-time Kudankulam Unit 1 / BARC PWR Nuclear Telemetry (NPPAD Nature Sci Data 2022)
_nuclear_telemetry: Dict[str, Any] = {
    "facility": "BARC / NPCIL Kudankulam Unit 1 (PWR)",
    "dataset": "Nature Scientific Data (NPPAD 96-Sensor Benchmark)",
    "reactor_state": "NOMINAL_FULL_POWER",
    "pressure_bar": 155.5,
    "core_temp_c": 310.0,
    "coolant_flow_kgs": 16515.8,
    "output_mwe": 955.3,
    "container_cpu_pct": 1.2,
    "container_mem_mb": 22.0,
    "container_mem_pct": 2.1,
    "last_attack": "None",
    "last_attack_time": "--:--:--",
    "last_updated": time.time(),
    "source": "optical_airgap",
}


async def broadcast_event(event_dict: Dict[str, Any]):
    """Broadcast an event dictionary to all active SSE streaming subscribers."""
    dead_queues = []
    for q in _sse_subscribers:
        try:
            q.put_nowait(event_dict)
        except Exception:
            dead_queues.append(q)
    for q in dead_queues:
        if q in _sse_subscribers:
            _sse_subscribers.remove(q)


# --- API Routes ---
async def api_status(request: Request) -> JSONResponse:
    info = load_checkpoint_info()
    info["packet_stats"] = _packet_stats
    info["nuclear_telemetry"] = _nuclear_telemetry
    return JSONResponse(info)


async def api_alerts(request: Request) -> JSONResponse:
    alerts = read_recent_alerts()
    return JSONResponse(alerts)


async def api_benchmark(request: Request) -> JSONResponse:
    if BENCHMARK_PATH.exists():
        try:
            data = json.loads(BENCHMARK_PATH.read_text())
            return JSONResponse(data)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    return JSONResponse({"error": "benchmark.json not generated yet"}, status_code=404)


async def api_campaign(request: Request) -> JSONResponse:
    if CAMPAIGN_PATH.exists():
        try:
            data = json.loads(CAMPAIGN_PATH.read_text())
            return JSONResponse(data)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    return JSONResponse({"error": "campaign.json not generated yet"}, status_code=404)


async def api_eval(request: Request) -> JSONResponse:
    if EVAL_PATH.exists():
        try:
            data = json.loads(EVAL_PATH.read_text())
            return JSONResponse(data)
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    return JSONResponse({"error": "eval.json not found"}, status_code=404)


async def api_packet_event(request: Request) -> JSONResponse:
    """Ingests real packet transit events from real_packet.py or network nodes."""
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse({"error": "Invalid JSON body"}, status_code=400)

    events = payload if isinstance(payload, list) else payload.get("events", [payload])
    now_ts = time.time()

    for ev in events:
        if not isinstance(ev, dict):
            continue
        if "type" not in ev:
            ev["type"] = "packet_transit"
        if "timestamp" not in ev:
            ev["timestamp"] = now_ts

        _recent_packets.append(ev)
        if len(_recent_packets) > 300:
            del _recent_packets[:100]

        _packet_stats["total_transited"] += 1
        _packet_stats["last_transit_time"] = now_ts
        await broadcast_event(ev)

        # Ingest SCADA physical telemetry if present in event or nested 'scada' dict
        scada_data = ev.get("scada") if isinstance(ev.get("scada"), dict) else {}
        p_val = ev.get("p", ev.get("pressure_bar", scada_data.get("p", scada_data.get("pressure_bar"))))
        if p_val is not None:
            try:
                _nuclear_telemetry["pressure_bar"] = round(float(p_val), 1)
                _nuclear_telemetry["core_temp_c"] = round(float(ev.get("tavg", ev.get("core_temp_c", scada_data.get("tavg", scada_data.get("core_temp_c", _nuclear_telemetry["core_temp_c"]))))), 1)
                _nuclear_telemetry["coolant_flow_kgs"] = round(float(ev.get("flow", ev.get("coolant_flow_kgs", scada_data.get("flow", scada_data.get("coolant_flow_kgs", _nuclear_telemetry["coolant_flow_kgs"]))))), 1)
                _nuclear_telemetry["output_mwe"] = round(float(ev.get("mw", ev.get("output_mwe", scada_data.get("mw", scada_data.get("output_mwe", _nuclear_telemetry["output_mwe"]))))), 1)
                _nuclear_telemetry["container_cpu_pct"] = round(float(ev.get("cpu", ev.get("container_cpu_pct", scada_data.get("cpu", scada_data.get("container_cpu_pct", _nuclear_telemetry["container_cpu_pct"]))))), 1)
                _nuclear_telemetry["container_mem_pct"] = round(float(ev.get("ram", ev.get("container_mem_pct", scada_data.get("ram", scada_data.get("container_mem_pct", _nuclear_telemetry["container_mem_pct"]))))), 1)
                state_val = ev.get("state", ev.get("reactor_state", scada_data.get("state", scada_data.get("reactor_state"))))
                if state_val:
                    _nuclear_telemetry["reactor_state"] = str(state_val)
                atk_val = ev.get("atk", ev.get("attack_type", scada_data.get("atk", scada_data.get("attack_type"))))
                if atk_val:
                    _nuclear_telemetry["last_attack"] = str(atk_val)
                    _nuclear_telemetry["last_attack_time"] = time.strftime("%H:%M:%S")
                _nuclear_telemetry["last_updated"] = now_ts
                await broadcast_event({
                    "type": "nuclear_telemetry",
                    "telemetry": dict(_nuclear_telemetry),
                    "timestamp": now_ts,
                })
            except Exception:
                pass

        # Evaluate continuous Neural Jump-ODE AI model on ingress optical packets
        feat = ev.get("feat")
        if feat and _feeder is not None and ev.get("to") == "njode-core":
            try:
                pkt = Packet(
                    t=now_ts,
                    size=int(ev.get("size", feat[1])),
                    payload=b"optical_airgap_pkt",
                    direction=int(feat[4])
                )
                alerts = _feeder.ingest_packet(pkt)
                for a in alerts:
                    rec = {
                        "ts": time.strftime("%H:%M:%S"),
                        "window_t0": round(a.window_t0, 2),
                        "window_t1": round(a.window_t1, 2),
                        "peak_score": round(a.peak_score, 4),
                        "threshold": round(a.threshold, 4),
                        "is_anomaly": a.is_anomaly,
                        "confirmed": a.confirmed,
                        "attribution": a.attribution,
                    }
                    with open(REPO_ROOT / "alerts.jsonl", "a") as f:
                        f.write(json.dumps(rec) + "\n")
                    # Broadcast alert event to connected dashboard clients
                    await broadcast_event({
                        "type": "anomaly_alert",
                        "alert": rec,
                        "timestamp": now_ts,
                    })
            except Exception:
                pass

    return JSONResponse({
        "status": "ok",
        "ingested": len(events),
        "total_transited": _packet_stats["total_transited"],
    })


async def api_packets_recent(request: Request) -> JSONResponse:
    """Returns recent packet transit events for connecting clients."""
    limit = int(request.query_params.get("limit", 60))
    return JSONResponse({
        "packets": _recent_packets[-limit:],
        "stats": _packet_stats,
    })


async def api_simulate(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        body = {}
    scenario = body.get("scenario", "calm")
    speed = float(body.get("speed", 1.0))

    # Broadcast scenario update to connected clients
    await broadcast_event({
        "type": "scenario_change",
        "scenario": scenario,
        "speed": speed,
        "timestamp": time.time(),
    })

    return JSONResponse({
        "status": "success",
        "scenario": scenario,
        "speed": speed,
        "message": f"Scenario {scenario} triggered across simplex data diode at {speed}x speed",
    })


async def api_stream(request: Request) -> StreamingResponse:
    """Server-Sent Events (SSE) streaming real packet events and alerts in real time."""
    client_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _sse_subscribers.append(client_queue)

    async def event_generator():
        last_count = 0
        try:
            # Yield initial connection confirmation
            init_msg = json.dumps({"type": "connection", "status": "online", "time": time.time()})
            yield f"data: {init_msg}\n\n"

            while True:
                # 1. Drain any queued broadcast events (real packets, scenario changes, alerts)
                drained = False
                while not client_queue.empty():
                    ev = client_queue.get_nowait()
                    yield f"data: {json.dumps(ev)}\n\n"
                    drained = True

                # 2. Check for newly written alerts from alerts.jsonl
                alerts = read_recent_alerts(50)
                if len(alerts) > last_count:
                    new_alerts = alerts[last_count:]
                    last_count = len(alerts)
                    for a in new_alerts:
                        if isinstance(a, dict) and "type" not in a:
                            a["type"] = "alert"
                        yield f"data: {json.dumps(a)}\n\n"
                        drained = True

                # Small sleep to prevent busy spinning
                await asyncio.sleep(0.05 if drained else 0.15)
        except asyncio.CancelledError:
            pass
        finally:
            if client_queue in _sse_subscribers:
                _sse_subscribers.remove(client_queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


async def serve_spa_index(request: Request):
    rel_path = request.path_params.get("path", "").lstrip("/")
    if rel_path:
        target_file = (DIST_DIR / rel_path).resolve()
        try:
            target_file.relative_to(DIST_DIR.resolve())
            if target_file.is_file():
                return FileResponse(target_file)
        except (ValueError, RuntimeError):
            pass
    index_file = DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({
        "status": "online",
        "message": "React frontend not built yet. Run 'npm run build' inside frontend/",
        "api_docs": ["/api/status", "/api/alerts", "/api/campaign", "/api/eval", "/api/diode/status", "/api/stream", "/api/packet/event", "/api/packets/recent"]
    })


async def api_diode_status(request: Request) -> JSONResponse:
    alerts = read_recent_alerts(20)
    last_alert = alerts[-1] if alerts else None
    return JSONResponse({
        "status": "SECURE_OPTICAL_AIRGAP",
        "transport": "OPTICAL_QR_DIODE",
        "simplex_assurance": "0.00% reverse bit transmission (Physical Diode)",
        "qr_ingest_port": 9999,
        "mirror_loopback_port": 9998,
        "latest_alert": last_alert,
        "recent_alerts_count": len(alerts),
        "packet_stats": _packet_stats,
        "nuclear_telemetry": _nuclear_telemetry,
    })


async def api_nuclear_status(request: Request) -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "telemetry": _nuclear_telemetry,
        "packet_stats": _packet_stats,
    })


async def api_scada_trip(request: Request) -> JSONResponse:
    now_str = time.strftime("%H:%M:%S")
    now_ts = time.time()
    _nuclear_telemetry["reactor_state"] = "LOSS_OF_FLOW"
    _nuclear_telemetry["coolant_flow_kgs"] = 2100.0
    _nuclear_telemetry["pressure_bar"] = 142.0
    _nuclear_telemetry["core_temp_c"] = 338.5
    _nuclear_telemetry["last_attack"] = "UNAUTHORIZED MODBUS FC05 PUMP TRIP"
    _nuclear_telemetry["last_attack_time"] = now_str
    _nuclear_telemetry["last_updated"] = now_ts

    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:8080/trip", method="POST")
        urllib.request.urlopen(req, timeout=0.5)
    except Exception:
        pass

    await broadcast_event({
        "type": "nuclear_telemetry",
        "telemetry": dict(_nuclear_telemetry),
        "timestamp": now_ts,
    })

    alert_rec = {
        "ts": now_str,
        "window_t0": round(now_ts - 2.0, 2),
        "window_t1": round(now_ts, 2),
        "peak_score": 2.85,
        "threshold": 2.464,
        "is_anomaly": True,
        "confirmed": True,
        "attribution": {
            "top_channel": "flow_transient",
            "threat_type": "modbus_pump_trip",
            "channel_errors": {"flow": 14415.8, "iat": 0.1, "bytes": 400.0, "entropy": 5.8, "burst": 3.0}
        }
    }
    try:
        with open(REPO_ROOT / "alerts.jsonl", "a") as f:
            f.write(json.dumps(alert_rec) + "\n")
    except Exception:
        pass

    await broadcast_event({
        "type": "anomaly_alert",
        "alert": alert_rec,
        "timestamp": now_ts,
    })

    return JSONResponse({"status": "PUMP_TRIPPED", "telemetry": _nuclear_telemetry})


async def api_scada_reset(request: Request) -> JSONResponse:
    now_str = time.strftime("%H:%M:%S")
    now_ts = time.time()
    _nuclear_telemetry["reactor_state"] = "NOMINAL_FULL_POWER"
    _nuclear_telemetry["coolant_flow_kgs"] = 16515.8
    _nuclear_telemetry["pressure_bar"] = 155.5
    _nuclear_telemetry["core_temp_c"] = 310.0
    _nuclear_telemetry["output_mwe"] = 955.3
    _nuclear_telemetry["last_attack"] = "Baseline Restored"
    _nuclear_telemetry["last_attack_time"] = now_str
    _nuclear_telemetry["last_updated"] = now_ts

    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:8080/reset", method="POST")
        urllib.request.urlopen(req, timeout=0.5)
    except Exception:
        pass

    await broadcast_event({
        "type": "nuclear_telemetry",
        "telemetry": dict(_nuclear_telemetry),
        "timestamp": now_ts,
    })

    return JSONResponse({"status": "RESET_OK", "telemetry": _nuclear_telemetry})


async def api_usb_status(request: Request) -> JSONResponse:
    port = int(request.query_params.get("port", 8000))
    return JSONResponse(get_usb_status(preferred_port=port))


async def poll_scada_background():
    """Periodically queries local SCADA HMI (port 8080) if available."""
    while True:
        try:
            import urllib.request
            req = urllib.request.Request("http://127.0.0.1:8080/stats", headers={"User-Agent": "Chronos-SOC"})
            with urllib.request.urlopen(req, timeout=0.6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "cpu_pct" in data:
                    _nuclear_telemetry["container_cpu_pct"] = data.get("cpu_pct", _nuclear_telemetry["container_cpu_pct"])
                    _nuclear_telemetry["container_mem_mb"] = data.get("memory_mb", _nuclear_telemetry["container_mem_mb"])
                    _nuclear_telemetry["container_mem_pct"] = data.get("memory_pct", _nuclear_telemetry["container_mem_pct"])
                    if data.get("last_attack") and data.get("last_attack") != "None":
                        _nuclear_telemetry["last_attack"] = data.get("last_attack")
                        _nuclear_telemetry["last_attack_time"] = data.get("last_attack_time", "--:--:--")

            req2 = urllib.request.Request("http://127.0.0.1:8080/", headers={"User-Agent": "Chronos-SOC"})
            with urllib.request.urlopen(req2, timeout=0.6) as resp:
                data2 = json.loads(resp.read().decode("utf-8"))
                if "pressure_bar" in data2:
                    _nuclear_telemetry["pressure_bar"] = data2.get("pressure_bar", _nuclear_telemetry["pressure_bar"])
                    _nuclear_telemetry["core_temp_c"] = data2.get("core_temp_c", _nuclear_telemetry["core_temp_c"])
                    _nuclear_telemetry["coolant_flow_kgs"] = data2.get("coolant_flow_kgs", _nuclear_telemetry["coolant_flow_kgs"])
                    _nuclear_telemetry["output_mwe"] = data2.get("output_mwe", _nuclear_telemetry["output_mwe"])
                    _nuclear_telemetry["reactor_state"] = data2.get("reactor_state", _nuclear_telemetry["reactor_state"])
                    _nuclear_telemetry["last_updated"] = time.time()
                    _nuclear_telemetry["source"] = "scada_hmi_local"
                    await broadcast_event({
                        "type": "nuclear_telemetry",
                        "telemetry": dict(_nuclear_telemetry),
                        "timestamp": time.time(),
                    })
        except Exception:
            pass
        await asyncio.sleep(2.0)


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(poll_scada_background())
    try:
        yield
    finally:
        task.cancel()


# Setup routes
routes = [
    Route("/api/status", api_status, methods=["GET"]),
    Route("/api/alerts", api_alerts, methods=["GET"]),
    Route("/api/benchmark", api_benchmark, methods=["GET"]),
    Route("/api/campaign", api_campaign, methods=["GET"]),
    Route("/api/eval", api_eval, methods=["GET"]),
    Route("/api/simulate", api_simulate, methods=["POST"]),
    Route("/api/stream", api_stream, methods=["GET"]),
    Route("/api/packet/event", api_packet_event, methods=["POST"]),
    Route("/api/packets/recent", api_packets_recent, methods=["GET"]),
    Route("/api/diode/status", api_diode_status, methods=["GET"]),
    Route("/api/usb/status", api_usb_status, methods=["GET"]),
    Route("/api/nuclear/status", api_nuclear_status, methods=["GET"]),
    Route("/api/scada/trip", api_scada_trip, methods=["GET", "POST"]),
    Route("/api/scada/reset", api_scada_reset, methods=["GET", "POST"]),
]

# Mount static dist assets and SPA fallback
(DIST_DIR / "assets").mkdir(parents=True, exist_ok=True)
routes.append(Mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets"))
routes.append(Route("/{path:path}", serve_spa_index, methods=["GET"]))

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = Starlette(debug=False, routes=routes, middleware=middleware, lifespan=lifespan)


def get_primary_lan_ip() -> str:
    """Finds the primary local LAN / Wi-Fi IP address for phone connectivity."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        # If VPN/Docker tunnel, check for Wi-Fi or local subnet
        if ip.startswith("172.16.") or ip.startswith("172.17."):
            import subprocess
            out = subprocess.check_output(["ip", "-4", "addr", "show"], text=True)
            for line in out.splitlines():
                if "inet " in line and ("wlp" in line or "wlan" in line or "eth" in line or "10." in line or "192.168." in line):
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        return parts[1].split("/")[0]
        return ip
    except Exception:
        return "127.0.0.1"


def check_or_clear_port(port: int):
    """Detects and frees port if held by a zombie background process."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("0.0.0.0", port))
        s.close()
        return
    except OSError:
        pass

    try:
        current_pid = os.getpid()
        if sys.platform == "win32":
            import subprocess
            out = subprocess.check_output(["netstat", "-ano"], text=True)
            for line in out.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    pid = int(parts[-1])
                    if pid != current_pid and pid > 0:
                        print(f"[i] Freeing occupied port {port} from prior process (PID: {pid})...")
                        subprocess.run(["taskkill", "/F", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            time.sleep(0.5)
        else:
            import subprocess
            out = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True).strip()
            if out:
                for pid in out.split():
                    if int(pid) != current_pid:
                        print(f"[i] Freeing occupied port {port} from prior process (PID: {pid})...")
                        subprocess.run(["kill", "-9", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                time.sleep(0.4)
    except Exception:
        pass


def ensure_ssl_certs(cert_dir: Path, host: str = "0.0.0.0"):
    cert_dir.mkdir(parents=True, exist_ok=True)
    key_path = cert_dir / "key.pem"
    cert_path = cert_dir / "cert.pem"
    if not key_path.exists() or not cert_path.exists():
        import subprocess
        cmd = [
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(key_path), "-out", str(cert_path),
            "-days", "365", "-nodes", "-subj", f"/CN={host}"
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except Exception:
            pass
    return str(key_path), str(cert_path)


def main():
    parser = argparse.ArgumentParser(description="CHRONOS React SOC Full-Stack Console Server")
    parser.add_argument("--host", default="0.0.0.0", help="Listen host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8501, help="Listen port (default: 8501)")
    parser.add_argument("--ssl-port", type=int, default=8443, help="HTTPS SSL companion port for mobile WebRTC (default: 8443)")
    parser.add_argument("--ssl", action="store_true", default=False, help="Force primary port to run HTTPS")
    parser.add_argument("--no-ssl", dest="enable_ssl", action="store_false", help="Disable HTTPS companion completely")
    parser.add_argument("--http", dest="enable_ssl", action="store_false", help="Disable HTTPS companion completely")
    parser.add_argument("--ssl-key", default="", help="Path to SSL private key")
    parser.add_argument("--ssl-cert", default="", help="Path to SSL certificate")
    parser.add_argument("--reload", action="store_true", help="Enable live code reload")
    args = parser.parse_args()

    check_or_clear_port(args.port)
    lan_ip = get_primary_lan_ip()

    if args.ssl:
        cert_dir = REPO_ROOT / "certs"
        k, c = ensure_ssl_certs(cert_dir, args.host)
        ssl_keyfile = args.ssl_key or k
        ssl_certfile = args.ssl_cert or c

        print("=" * 72)
        print("🛡️  CHRONOS CYBER-DEFENSE SOC FULL-STACK CONSOLE")
        print("=" * 72)
        print(f" Web Interface:     https://localhost:{args.port}")
        print(f" Local LAN URL:     https://{lan_ip}:{args.port}")
        print(f" 📱 PHONE 30 FPS:   https://{lan_ip}:{args.port}/?scan=1")
        print(f" SSL Encryption:    PRIMARY PORT ENCRYPTED (HTTPS)")
        print(f" Static Assets:     {DIST_DIR}")
        print(" Press Ctrl+C to terminate.")
        print("=" * 72)

        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            log_level="info"
        )
    else:
        enable_companion = getattr(args, "enable_ssl", True)
        ssl_keyfile = None
        ssl_certfile = None
        if enable_companion:
            try:
                cert_dir = REPO_ROOT / "certs"
                k, c = ensure_ssl_certs(cert_dir, args.host)
                ssl_keyfile = args.ssl_key or k
                ssl_certfile = args.ssl_cert or c
                check_or_clear_port(args.ssl_port)
            except Exception:
                enable_companion = False

        print("=" * 72)
        print("🛡️  CHRONOS CYBER-DEFENSE SOC FULL-STACK CONSOLE")
        print("=" * 72)
        print(f" Web Interface:     http://localhost:{args.port}")
        print(f" Local LAN URL:     http://{lan_ip}:{args.port}")
        if enable_companion:
            print(f" 📱 PHONE 30 FPS:   https://{lan_ip}:{args.ssl_port}/?scan=1")
            print(f" SSL Encryption:    COMPANION ACTIVE ON :{args.ssl_port} (Native Mobile WebRTC)")
        else:
            print(f" SSL Encryption:    DISABLED (HTTP Mode)")
        print(f" Static Assets:     {DIST_DIR}")
        print(" Press Ctrl+C to terminate.")
        print("=" * 72)

        if enable_companion:
            async def run_dual_servers():
                cfg_http = uvicorn.Config(app, host=args.host, port=args.port, log_level="info")
                cfg_https = uvicorn.Config(app, host=args.host, port=args.ssl_port, ssl_keyfile=ssl_keyfile, ssl_certfile=ssl_certfile, log_level="warning")
                srv_http = uvicorn.Server(cfg_http)
                srv_https = uvicorn.Server(cfg_https)
                await asyncio.gather(srv_http.serve(), srv_https.serve())

            try:
                asyncio.run(run_dual_servers())
            except (KeyboardInterrupt, SystemExit):
                pass
        else:
            uvicorn.run(
                app,
                host=args.host,
                port=args.port,
                log_level="info"
            )


if __name__ == "__main__":
    main()

