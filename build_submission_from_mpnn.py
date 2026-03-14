#!/usr/bin/env python3
"""
Parse ProteinMPNN output, rank by score, build competition CSV.
ProteinMPNN score = negative log-probability; LOWER = better fit to structure.
"""
import csv, re, sys
from pathlib import Path

MPNN_FA  = Path("/home/on/ProteinMPNN/outputs/rbx1_binders/seqs/interface_complex.fa")
OUT_CSV  = Path("/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/rbx1_mpnn_candidates.csv")
TARGET   = 100

seqs = []
current_meta = {}

for line in MPNN_FA.read_text().splitlines():
    if line.startswith(">"):
        # Parse score from header
        m = re.search(r"score=([\d.]+)", line)
        score = float(m.group(1)) if m else 999.0
        temp_m = re.search(r"T=([\d.]+)", line)
        temp = float(temp_m.group(1)) if temp_m else 0.0
        samp_m = re.search(r"sample=(\d+)", line)
        samp = int(samp_m.group(1)) if samp_m else 0
        current_meta = {"score": score, "temp": temp, "sample": samp}
    else:
        seq = line.strip()
        if seq and current_meta.get("sample", 0) > 0:  # skip native reference (sample=0)
            seqs.append({**current_meta, "sequence": seq, "length": len(seq)})

print(f"Total candidates parsed: {len(seqs)}")

# Deduplicate
seen = set()
unique = []
for s in seqs:
    if s["sequence"] not in seen:
        seen.add(s["sequence"])
        unique.append(s)
print(f"Unique sequences: {len(unique)}")

# Filter: length 40-120 AA (competition requirement)
filtered = [s for s in unique if 40 <= s["length"] <= 120]
print(f"Within length range (40-120 AA): {len(filtered)}")

# Sort by ProteinMPNN score ascending (lower = better)
filtered.sort(key=lambda x: x["score"])

# Show score distribution
scores = [s["score"] for s in filtered]
print(f"\nScore range: {min(scores):.4f} - {max(scores):.4f}")
print(f"Top 10 scores: {[round(s,4) for s in scores[:10]]}")

# Take top TARGET
selected = filtered[:TARGET]
print(f"\nSelected top {len(selected)} for submission")

# Write competition CSV
with open(OUT_CSV, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Name", "Sequence"])
    for i, s in enumerate(selected, 1):
        name = f"RBX1_MPNN_{i:03d}"
        writer.writerow([name, s["sequence"]])

print(f"Wrote: {OUT_CSV}")
print("\nTop 5 sequences:")
for i, s in enumerate(selected[:5], 1):
    print(f"  {i}. score={s['score']:.4f} T={s['temp']} L={s['length']} {s['sequence'][:40]}...")
