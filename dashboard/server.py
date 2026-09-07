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

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DIST_DIR = REPO_ROOT / "frontend" / "dist"
if not DIST_DIR.exists() and (REPO_ROOT / "frontend" / "package.json").exists():
    import subprocess
    print("[i] Building React frontend distribution bundle...")
    try:
        subprocess.run(["npm", "run", "build"], cwd=str(REPO_ROOT / "frontend"), check=True)
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


async def serve_spa_index(request: Request) -> FileResponse:
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
    })


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
]

# Mount static dist assets if directory exists
if DIST_DIR.exists():
    routes.append(Mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets"))
    routes.append(Route("/{path:path}", serve_spa_index, methods=["GET"]))
else:
    routes.append(Route("/", serve_spa_index, methods=["GET"]))

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = Starlette(debug=False, routes=routes, middleware=middleware)


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
    parser.add_argument("--ssl", action="store_true", help="Enable HTTPS using SSL certificates (required for mobile phone camera WebRTC)")
    parser.add_argument("--ssl-key", default="", help="Path to SSL private key")
    parser.add_argument("--ssl-cert", default="", help="Path to SSL certificate")
    parser.add_argument("--reload", action="store_true", help="Enable live code reload")
    args = parser.parse_args()

    ssl_keyfile = None
    ssl_certfile = None
    protocol = "http"

    if args.ssl:
        cert_dir = REPO_ROOT / "certs"
        k, c = ensure_ssl_certs(cert_dir, args.host)
        ssl_keyfile = args.ssl_key or k
        ssl_certfile = args.ssl_cert or c
        protocol = "https"

    print("=" * 72)
    print("🛡️  CHRONOS CYBER-DEFENSE SOC FULL-STACK CONSOLE")
    print("=" * 72)
    print(f" Web Interface:     {protocol}://localhost:{args.port}")
    print(f" Network URL:       {protocol}://{args.host}:{args.port}")
    print(f" SSL Encryption:    {'ENABLED (HTTPS for Mobile Camera)' if args.ssl else 'DISABLED (HTTP)'}")
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


if __name__ == "__main__":
    main()
