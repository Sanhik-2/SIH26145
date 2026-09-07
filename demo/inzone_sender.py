"""
demo/inzone_sender.py — Simulates the protected / air-gapped side of the network.

Generates simplex network traffic behind a data diode:
  1. Calm baseline traffic (SCADA telemetry + occasional web sync)
  2. Injected attack at --attack-at <sec> (default: 20s)
  3. Returns to calm baseline for post-attack recovery

Transmits packets over a simplex UDP socket (unidirectional, no return channel).
Run:
  python demo/inzone_sender.py --attack-at 20 --attack exfil_burst
"""
import argparse
from pathlib import Path
import socket
import struct
import sys
import time
from typing import List

# Ensure repository root is on sys.path regardless of execution directory
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from features.extractor import Packet
from simulation.attacks.c2_beacon import c2_beacon_stream
from simulation.attacks.dga_tunnel import dga_tunnel_stream
from simulation.attacks.exfil_burst import exfil_burst_stream
from simulation.benign.telemetry import telemetry_stream
from simulation.benign.web_sync import web_sync_stream


ATTACK_FACTORIES = {
    "c2_beacon": lambda dur, seed, t0: c2_beacon_stream(duration_s=dur, seed=seed, t0=t0, period=2.5, jitter=0.2),
    "exfil_burst": lambda dur, seed, t0: exfil_burst_stream(duration_s=dur, seed=seed, t0=t0, gap_mean=0.015, pkt_size=1400),
    "dga_tunnel": lambda dur, seed, t0: dga_tunnel_stream(duration_s=dur, seed=seed, t0=t0),
}


def build_scenario_packets(
    total_duration: float,
    attack_at: float,
    attack_name: str,
    attack_duration: float,
    seed: int = 42,
) -> List[Packet]:
    """Generate and chronological-sort all scenario packets."""
    # 1. Telemetry runs throughout total_duration
    pkts = list(telemetry_stream(duration_s=total_duration, seed=seed, t0=0.0))

    # 2. Web sync runs throughout total_duration
    pkts.extend(web_sync_stream(duration_s=total_duration, seed=seed + 1, t0=0.0))

    # 3. Attack injected during [attack_at, attack_at + attack_duration]
    factory = ATTACK_FACTORIES[attack_name]
    atk_pkts = factory(attack_duration, seed + 2, attack_at)
    pkts.extend(atk_pkts)

    # Sort strictly by arrival time
    pkts.sort(key=lambda p: p.t)
    return pkts


def encode_packet(p: Packet) -> bytes:
    """Encode packet into binary frame: [8B float t][4B uint size][payload]."""
    header = struct.pack(">dI", p.t, p.size)
    return header + p.payload


def main():
    parser = argparse.ArgumentParser(description="CHRONOS Air-Gap In-Zone Simplex Traffic Sender")
    parser.add_argument("--host", default="127.0.0.1", help="Receiver host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9999, help="Receiver UDP port (default: 9999)")
    parser.add_argument("--attack-at", type=float, default=20.0, help="Seconds from start when attack is injected (default: 20)")
    parser.add_argument("--attack", choices=list(ATTACK_FACTORIES.keys()), default="exfil_burst", help="Attack class to inject")
    parser.add_argument("--attack-duration", type=float, default=15.0, help="Duration of attack injection in seconds (default: 15)")
    parser.add_argument("--total-duration", type=float, default=60.0, help="Total scenario duration in seconds (default: 60)")
    parser.add_argument("--speed", type=float, default=1.0, help="Speed multiplier (1.0 = real-time, 2.0 = 2x speed)")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    args = parser.parse_args()

    attack_end = args.attack_at + args.attack_duration

    print("=" * 72)
    print("🔒 CHRONOS AIR-GAP TRAFFIC SENDER (IN-ZONE TRANSMITTER)")
    print("=" * 72)
    print(f"Target Diode Receiver:  udp://{args.host}:{args.port}")
    print(f"Total Duration:         {args.total_duration:.1f} s (Speed: {args.speed:.1f}x)")
    print(f"Scenario Timeline:")
    print(f"  [ 0.0s - {args.attack_at:4.1f}s]   CALM BENIGN (Telemetry + Web Sync)")
    print(f"  [{args.attack_at:4.1f}s - {attack_end:4.1f}s]   🚨 INJECTING ATTACK: {args.attack.upper()}")
    print(f"  [{attack_end:4.1f}s - {args.total_duration:4.1f}s]   POST-ATTACK RECOVERY (Calm Benign)")
    print("=" * 72)

    pkts = build_scenario_packets(
        total_duration=args.total_duration,
        attack_at=args.attack_at,
        attack_name=args.attack,
        attack_duration=args.attack_duration,
        seed=args.seed,
    )
    print(f"Prepared {len(pkts)} packets for transmission.")
    print("Transmitting one-way datagrams across simplex diode...\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    start_wall_time = time.time()
    sent_count = 0
    last_print = -1.0

    for p in pkts:
        target_sim_time = p.t
        elapsed_wall = (time.time() - start_wall_time) * args.speed

        sleep_s = (target_sim_time - elapsed_wall) / args.speed
        if sleep_s > 0:
            time.sleep(sleep_s)

        data = encode_packet(p)
        try:
            sock.sendto(data, (args.host, args.port))
            sent_count += 1
        except Exception as e:
            print(f"[!] Send error: {e}")

        # Live status print every ~1 simulated second
        if int(target_sim_time) != int(last_print):
            last_print = target_sim_time
            if target_sim_time < args.attack_at:
                phase_badge = "✅ [PASSIVE CALM]"
            elif target_sim_time < attack_end:
                phase_badge = f"🚨 [ATTACK: {args.attack.upper()}]"
            else:
                phase_badge = "🔄 [RECOVERY CALM]"

            sys.stdout.write(f"\r{phase_badge} T+{target_sim_time:4.1f}s | Packets sent: {sent_count:4d} ")
            sys.stdout.flush()

    # End of stream sentinel packet (size 0)
    sock.sendto(encode_packet(Packet(t=args.total_duration + 0.1, size=0, payload=b"EOS")), (args.host, args.port))
    sock.close()

    print(f"\n\n[✓] Transmission complete. Total {sent_count} packets sent across simplex diode.")


if __name__ == "__main__":
    main()
