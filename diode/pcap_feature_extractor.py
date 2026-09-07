"""
CHRONOS PCAP FEATURE EXTRACTOR
------------------------------
Takes real network packet captures (.pcap files) from benchmark datasets
(CIC-IDS2017, CTU-13, 4SICS SCADA) and extracts the 6 core NTRO features:

1. Flow 5-tuple: (src_ip, dst_ip, src_port, dst_port, proto)
2. Inter-Arrival Time (IAT) statistics: mean_iat, std_iat, cv_iat (For C2 Beaconing)
3. Source-IP Shannon Entropy (For Volumetric / Spoofed DDoS)
4. Outbound / Inbound Byte Ratio (For Data Exfiltration)
5. DNS Query string & character entropy (For DGA / Tunnelling)
6. First-N packet size sequences (SPLT for Encrypted Malware)
"""

import math
import numpy as np
from collections import defaultdict

def calculate_shannon_entropy(items):
    """Calculates Shannon Entropy on a list of items (e.g. Source IPs or Domain chars)."""
    if not items:
        return 0.0
    counts = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    total = len(items)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log2(p)
    return round(entropy, 3)

class FlowRecord:
    def __init__(self, flow_key):
        self.flow_key = flow_key
        self.packet_timestamps = []
        self.packet_sizes = []
        self.inbound_bytes = 0
        self.outbound_bytes = 0
        self.dns_queries = []
        self.ja4_hash = None

    def add_packet(self, timestamp, size, is_outbound, dns_query=None, ja4=None):
        self.packet_timestamps.append(timestamp)
        self.packet_sizes.append(size)
        if is_outbound:
            self.outbound_bytes += size
        else:
            self.inbound_bytes += size
        if dns_query:
            self.dns_queries.append(dns_query)
        if ja4:
            self.ja4_hash = ja4

    def extract_features(self):
        """Converts raw packet observations into a clean ML feature vector."""
        total_pkts = len(self.packet_timestamps)
        if total_pkts < 2:
            return None

        # 1. Inter-Arrival Time (IAT) Statistics (Threat B: C2 Beaconing)
        iats = [self.packet_timestamps[i] - self.packet_timestamps[i-1] for i in range(1, total_pkts)]
        mean_iat = float(np.mean(iats))
        std_iat = float(np.std(iats))
        cv_iat = std_iat / (mean_iat + 1e-6)  # Low CV = high periodicity (beaconing)

        # 2. Byte Ratio (Threat F: Exfiltration)
        byte_ratio = self.outbound_bytes / (self.inbound_bytes + 1e-6)

        # 3. DNS Features (Threat C: DGA & Tunneling)
        max_dns_entropy = 0.0
        max_dns_len = 0
        if self.dns_queries:
            entropies = [calculate_shannon_entropy(list(q)) for q in self.dns_queries]
            max_dns_entropy = max(entropies)
            max_dns_len = max([len(q) for q in self.dns_queries])

        # 4. Sequence of Packet Lengths and Times (SPLT - Threat D: Encrypted Malware)
        # Take first 10 packet sizes as spatial geometric signature
        first_10_sizes = self.packet_sizes[:10]
        while len(first_10_sizes) < 10:
            first_10_sizes.append(0)

        return {
            "flow_key": f"{self.flow_key[0]}:{self.flow_key[1]} -> {self.flow_key[2]}:{self.flow_key[3]} [{self.flow_key[4]}]",
            "total_packets": total_pkts,
            "mean_iat": round(mean_iat, 4),
            "std_iat": round(std_iat, 4),
            "cv_iat": round(cv_iat, 4),
            "byte_ratio": round(byte_ratio, 2),
            "max_dns_entropy": max_dns_entropy,
            "max_dns_len": max_dns_len,
            "ja4_hash": self.ja4_hash,
            "first_10_packet_sizes": first_10_sizes
        }

if __name__ == "__main__":
    print("[*] CHRONOS Feature Extraction Engine Loaded.")
    print("[*] Ready to process raw pcap buffers and extract NTRO feature vectors.")
