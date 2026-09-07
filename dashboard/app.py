"""CHRONOS SOC dashboard — renders alert stream & evaluation results.

Data sources (fully decoupled from the model):
  alerts.jsonl           — LiveFeeder alert events (live tail)
  results/campaign.json  — continuous campaign results
  results/eval.json      — static per-attack results
Run:  streamlit run dashboard/app.py
"""
import json
import time
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="CHRONOS SOC", page_icon="🛡️", layout="wide")

REPO_ROOT = Path(__file__).resolve().parent.parent
ALERTS = REPO_ROOT / "alerts.jsonl"


def norm(a: dict) -> dict:
    """Normalize AlertEvent (new) or legacy LiveFeeder lines (old) to one shape."""
    attr = a.get("attribution") or {}
    attr = attr if isinstance(attr, dict) else {}
    t1 = a.get("window_t1", a.get("window_end"))
    ts_str = a.get("ts")
    if not ts_str and t1 is not None:
        ts_str = f"T+{t1:.1f}s"
    return {
        "time": ts_str or (time.strftime("%H:%M:%S", time.localtime(t1)) if t1 else "?"),
        "score": float(a.get("peak_score", a.get("score", 0.0))),
        "tau": float(a.get("threshold", a.get("tau", 2.810))),
        "flagged": bool(a.get("is_anomaly", a.get("flagged", False))),
        "confirmed": bool(a.get("confirmed", a.get("flagged", False))),
        "channel": attr.get("top_channel") or attr.get("channel")
                   or attr.get("dominant_channel") or a.get("top_channel") or "—",
        "threat": attr.get("threat_type") or attr.get("threat")
                  or attr.get("category") or "—",
        "n_obs": a.get("n_obs", "—"),
    }


def load_alerts(n=400) -> list[dict]:
    if not ALERTS.exists():
        return []
    try:
        lines = ALERTS.read_text().splitlines()[-n:]
    except Exception:
        return []
    out = []
    for ln in lines:
        try:
            out.append(norm(json.loads(ln)))
        except (json.JSONDecodeError, ValueError):
            continue                     # half-written line during tail — skip
    return out


# ---------------- sidebar ----------------
st.sidebar.title("🛡️ CHRONOS SOC")
st.sidebar.caption("Passive threat detection · unidirectional traffic · v1.0")
refresh = st.sidebar.slider("Refresh interval (s)", 1, 10, 2)
live = st.sidebar.checkbox("🔴 LIVE", value=True)
tab1, tab2, tab3 = st.tabs(["🛰️ Live Monitor", "📈 Campaign", "📊 Static Eval"])

# ---------------- live tab ----------------
with tab1:
    alerts = load_alerts()
    if not alerts:
        st.info("No alerts yet — start `python demo/scan_receiver.py` and `python demo/inzone_sender.py`.")
    else:
        df = pd.DataFrame(alerts)
        last = alerts[-1]
        flagged_recent = [a for a in alerts[-15:] if a["flagged"]]
        confirmed_now = bool(flagged_recent and all(a["confirmed"] for a in flagged_recent[-2:]))

        c1, c2, c3, c4 = st.columns(4)
        if confirmed_now:
            threat_name = last['threat'] if last['threat'] != '—' else last['channel']
            c1.error(f"🚨 ATTACK — {threat_name}")
        elif flagged_recent:
            c1.warning("⚠️ SUSPECTED (pre-confirmation)")
        else:
            c1.success("✅ PASSIVE — calm")

        c2.metric("Anomaly score (last)", f"{last['score']:.2f}",
                  delta=f"τ = {last['tau']:.2f}")
        c3.metric("Flagged (last 15 win.)", len(flagged_recent))
        c4.metric("Confirmed alerts (session)",
                  sum(1 for a in alerts if a["flagged"] and a["confirmed"]))

        st.subheader("Score vs Threshold")
        chart = df[["score"]].copy()
        chart["τ"] = last["tau"]
        st.line_chart(chart, height=240)

        st.subheader("Live Alert Stream")
        show = df.tail(50).iloc[::-1].copy()                     # newest first
        show["flag"] = show.apply(
            lambda r: "🚨" if r["flagged"] and r["confirmed"]
            else ("⚠️" if r["flagged"] else "·"), axis=1)
        st.dataframe(
            show[["flag", "time", "score", "tau", "flagged", "confirmed",
                  "channel", "threat", "n_obs"]],
            use_container_width=True, height=380)

# ---------------- campaign tab ----------------
with tab2:
    cj = REPO_ROOT / "results/campaign.json"
    if cj.exists():
        data = json.loads(cj.read_text())
        attack_type = data.get("attack", "unknown").upper()
        tau_val = data.get("threshold_tau", 2.810)
        st.caption(f"Campaign Attack: **{attack_type}** · Checkpoint τ = **{tau_val:.3f}**")

        # Visual layout: metrics row
        p1 = data.get("phase1_baseline", {})
        p2 = data.get("phase2_regime_shift", {})
        p3 = data.get("phase3_sustained_attack", {})
        p4 = data.get("phase4_recovery", {})

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("P1 Calm FPR", f"{p1.get('fpr', 0)*100:.1f}%", f"Mean S: {p1.get('mean_peak_score', 0):.2f}")
        m2.metric("P2 Regime-Shift FPR", f"{p2.get('regime_shift_fpr', 0)*100:.1f}%", f"Mean S: {p2.get('mean_peak_score', 0):.2f}")
        m3.metric("P3 Persistence", f"{p3.get('persistence_rate', 0)*100:.1f}%", f"TTD: {p3.get('ttd_seconds', 0)}s")
        m4.metric("P4 Post-Recovery FPR", f"{p4.get('post_recovery_fpr', 0)*100:.1f}%", f"Recovery: {p4.get('recovery_seconds', 0)}s")

        img = REPO_ROOT / "results/campaign.png"
        if img.exists():
            st.image(str(img), caption="Window peak score across continuous campaign phases (300 s timeline)")

        with st.expander("Detailed Campaign JSON Breakdown", expanded=False):
            st.json(data)
    else:
        st.info("Run `python evaluate_campaign.py --multiregime --attack <name>` first.")

# ---------------- static eval tab ----------------
with tab3:
    ej = REPO_ROOT / "results/eval.json"
    if ej.exists():
        data = json.loads(ej.read_text())
        campaigns = data.get("campaigns", {})
        if campaigns:
            df_eval = pd.DataFrame(campaigns).T
            st.subheader("Attack Detection & Attribution Performance")
            st.dataframe(df_eval, use_container_width=True)
        st.metric("Benign False Positive Rate (FPR)", f"{data.get('benign_fpr', 0)*100:.1f}%", delta=f"τ = {data.get('threshold_tau', 2.810):.3f}")
        with st.expander("Raw Evaluation JSON", expanded=False):
            st.json(data)
    else:
        st.info("Run `python evaluate.py` first.")

if live:
    time.sleep(refresh)
    st.rerun()
