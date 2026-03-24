"""
Extract pLDDT scores from ESMFold v2 PDB outputs.
Joins with rbx1_rfdiff_mpnn_v2_filtered.csv metadata.
Writes rbx1_rfdiff_esmfold_v2_scores.csv.
Does NOT rerun folding or overwrite PDBs.
"""

import os
import re
import csv
from pathlib import Path

PDB_DIR = Path("/home/on/esmfold_rfdiff_v2_passing")
MPNN_CSV = Path("/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/rbx1_rfdiff_mpnn_v2_filtered.csv")
OUT_CSV  = Path("/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/rbx1_rfdiff_esmfold_v2_scores.csv")

MEAN_PLDDT_THRESH = 70.0
MIN_PLDDT_THRESH  = 55.0


# ── 1. Load MPNN metadata ────────────────────────────────────────────────────
meta = {}
with open(MPNN_CSV) as f:
    reader = csv.DictReader(f)
    for row in reader:
        meta[row["sequence_id"]] = row


# ── 2. Parse PDB files ───────────────────────────────────────────────────────
def parse_pdb_plddt(pdb_path: Path):
    """Return (mean, min, max) pLDDT from CA atoms (B-factor col, 0-1 scale → ×100)."""
    ca_plddt = []
    with open(pdb_path) as f:
        for line in f:
            if line.startswith("ATOM") and line[12:16].strip() == "CA":
                try:
                    bfac = float(line[60:66].strip())
                    ca_plddt.append(bfac * 100.0)   # ESMFold stores 0-1
                except ValueError:
                    pass
    if not ca_plddt:
        return None, None, None
    return (
        round(sum(ca_plddt) / len(ca_plddt), 2),
        round(min(ca_plddt), 2),
        round(max(ca_plddt), 2),
    )


records = []
pdb_files = sorted(PDB_DIR.glob("*.pdb"))
print(f"Found {len(pdb_files)} PDB files in {PDB_DIR}")

for pdb in pdb_files:
    seq_id = pdb.stem          # e.g. rbx1_binder_0_T02_s5
    mean_p, min_p, max_p = parse_pdb_plddt(pdb)
    if mean_p is None:
        print(f"  WARNING: no CA atoms found in {pdb.name}")
        continue

    m = meta.get(seq_id, {})
    records.append({
        "sequence_id":       seq_id,
        "backbone_id":       m.get("backbone_id", ""),
        "temperature":       m.get("temperature", ""),
        "binder_length":     m.get("binder_length", ""),
        "mpnn_score":        m.get("mpnn_score", ""),
        "mean_plddt":        mean_p,
        "min_plddt":         min_p,
        "max_plddt":         max_p,
        "binder_chain_sequence": m.get("binder_chain_sequence", ""),
        "pdb_path":          str(pdb),
    })

# ── 3. Write full scores CSV ─────────────────────────────────────────────────
fieldnames = [
    "sequence_id", "backbone_id", "temperature", "binder_length",
    "mpnn_score", "mean_plddt", "min_plddt", "max_plddt",
    "binder_chain_sequence", "pdb_path",
]
with open(OUT_CSV, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(records)
print(f"\nWrote {len(records)} rows → {OUT_CSV}")


# ── 4. Apply filters ─────────────────────────────────────────────────────────
passing = [r for r in records
           if r["mean_plddt"] >= MEAN_PLDDT_THRESH
           and r["min_plddt"] >= MIN_PLDDT_THRESH]

print(f"\n{'='*60}")
print(f"FILTER: mean_pLDDT ≥ {MEAN_PLDDT_THRESH}, min_pLDDT ≥ {MIN_PLDDT_THRESH}")
print(f"Total PDBs parsed : {len(records)}")
print(f"Passing filter    : {len(passing)}")
print(f"Failing filter    : {len(records) - len(passing)}")

# ── 5. Distribution by temperature ──────────────────────────────────────────
print(f"\n--- By temperature ---")
temp_counts = {}
for r in passing:
    t = r["temperature"]
    temp_counts[t] = temp_counts.get(t, 0) + 1
for t in sorted(temp_counts):
    print(f"  {t}: {temp_counts[t]}")

# ── 6. Distribution by backbone ─────────────────────────────────────────────
print(f"\n--- By backbone (passing count) ---")
bb_counts = {}
for r in passing:
    bb = r["backbone_id"]
    bb_counts[bb] = bb_counts.get(bb, 0) + 1
for bb in sorted(bb_counts, key=lambda x: int(re.search(r'\d+', x).group())):
    print(f"  {bb}: {bb_counts[bb]}")

# ── 7. Top 20 by mean pLDDT ──────────────────────────────────────────────────
print(f"\n--- Top 20 by mean pLDDT ---")
top20 = sorted(passing, key=lambda r: r["mean_plddt"], reverse=True)[:20]
print(f"{'sequence_id':<35} {'mean':>6} {'min':>6} {'max':>6}  {'temp':<5} {'len':>4}")
print("-" * 70)
for r in top20:
    print(f"{r['sequence_id']:<35} {r['mean_plddt']:>6.1f} {r['min_plddt']:>6.1f} "
          f"{r['max_plddt']:>6.1f}  {r['temperature']:<5} {r['binder_length']:>4}")

# ── 8. Failing sequences (for reference) ────────────────────────────────────
failing = [r for r in records if r not in passing]
if failing:
    print(f"\n--- Failing sequences ---")
    for r in sorted(failing, key=lambda r: r["mean_plddt"], reverse=True):
        print(f"  {r['sequence_id']:<35} mean={r['mean_plddt']:>5.1f}  min={r['min_plddt']:>5.1f}")
