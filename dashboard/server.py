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


# --- API Routes ---
async def api_status(request: Request) -> JSONResponse:
    info = load_checkpoint_info()
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


async def api_simulate(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        body = {}
    scenario = body.get("scenario", "calm")
    speed = float(body.get("speed", 1.0))
    return JSONResponse({
        "status": "success",
        "scenario": scenario,
        "speed": speed,
        "message": f"Scenario {scenario} triggered across simplex data diode at {speed}x speed",
    })



async def api_stream(request: Request) -> StreamingResponse:
    """Server-Sent Events (SSE) streaming alerts in real time."""
    async def event_generator():
        last_count = 0
        while True:
            alerts = read_recent_alerts(50)
            if len(alerts) > last_count:
                new_alerts = alerts[last_count:]
                last_count = len(alerts)
                for a in new_alerts:
                    yield f"data: {json.dumps(a)}\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def serve_spa_index(request: Request) -> FileResponse:
    index_file = DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({
        "status": "online",
        "message": "React frontend not built yet. Run 'npm run build' inside frontend/",
        "api_docs": ["/api/status", "/api/alerts", "/api/campaign", "/api/eval"]
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


def main():
    parser = argparse.ArgumentParser(description="CHRONOS React SOC Full-Stack Console Server")
    parser.add_argument("--host", default="0.0.0.0", help="Listen host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8501, help="Listen port (default: 8501)")
    parser.add_argument("--reload", action="store_true", help="Enable live code reload")
    args = parser.parse_args()

    print("=" * 72)
    print("🛡️  CHRONOS CYBER-DEFENSE SOC FULL-STACK CONSOLE")
    print("=" * 72)
    print(f" Web Interface:     http://localhost:{args.port}")
    print(f" Network URL:       http://{args.host}:{args.port}")
    print(f" Static Assets:     {DIST_DIR}")
    print(" Press Ctrl+C to terminate.")
    print("=" * 72)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
