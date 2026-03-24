"""
1. Append 12 PASS candidates from Boltz batch 1 to rbx1_rfdiff_validated.csv
2. Write 2 borderline reserve cases to rbx1_rfdiff_reserve.csv
3. Print validated set summary
4. Propose Boltz batch 2 from remaining unscreened ESMFold-v2 candidates
"""

import csv
from pathlib import Path

ROOT = Path("/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026")

VALIDATED_CSV   = ROOT / "rbx1_rfdiff_validated.csv"
RESERVE_CSV     = ROOT / "rbx1_rfdiff_reserve.csv"
BATCH1_CSV      = ROOT / "rbx1_boltz_rfdiff_v2_batch1_scores.csv"
ESMFOLD_V2_CSV  = ROOT / "rbx1_rfdiff_esmfold_v2_scores.csv"

# ── Confirmed PASS from batch 1 ───────────────────────────────────────────────
BATCH1_PASS = [
    "rbx1_binder_16_T01_s5",
    "rbx1_binder_11_T02_s2",
    "rbx1_binder_61_T01_s4",
    "rbx1_binder_64_T01_s4",
    "rbx1_binder_1_T02_s3",
    "rbx1_binder_45_T01_s1",
    "rbx1_binder_55_T01_s2",
    "rbx1_binder_15_T02_s3",
    "rbx1_binder_55_T01_s4",
    "rbx1_binder_63_T01_s1",
    "rbx1_binder_44_T01_s3",
    "rbx1_binder_77_T01_s3",
]

# ── Reserve (borderline — not PASS, not discarded) ────────────────────────────
BATCH1_RESERVE = {
    "rbx1_binder_87_T01_s3": "Δ=-24.4 < -20.0 (interface good: pairAB=0.744, iPTM=0.744)",
    "rbx1_binder_63_T01_s2": "pairAB=0.498 < 0.50 (one decimal off gate; iPTM=0.607 ok)",
}

# ── Batch 2 proposal ──────────────────────────────────────────────────────────
# 18 candidates from 16 unique backbones; all from remaining unscreened pool
BATCH2_PROPOSAL = [
    ("rbx1_binder_55_T01_s3", "rbx1_binder_55", 91.32, 72.0,
     "3rd from bb55 — both batch-1 reps passed (0.752, 0.737); backbone earns extra coverage"),
    ("rbx1_binder_25_T01_s5", "rbx1_binder_25", 90.09, 55.0,
     "New backbone; mean=90.1 — borderline min=55 (exactly at gate); worth one shot"),
    ("rbx1_binder_28_T01_s2", "rbx1_binder_28", 89.14, 81.0,
     "Second chance for bb28; s5 dropped (pairAB=0.423); s2 has min=81 vs s5's min=73 — notably cleaner"),
    ("rbx1_binder_1_T02_s5",  "rbx1_binder_1",  88.60, 79.0,
     "Follow-up on bb1: s3 passed at pairAB=0.796 — test adjacent sequence for consistency"),
    ("rbx1_binder_61_T01_s3", "rbx1_binder_61", 86.79, 76.0,
     "Follow-up on bb61: s4 passed at pairAB=0.817 — second representative from strong backbone"),
    ("rbx1_binder_82_T01_s3", "rbx1_binder_82", 86.85, 73.0,
     "New backbone bb82; top sequence by mean pLDDT from 4 available"),
    ("rbx1_binder_27_T01_s5", "rbx1_binder_27", 86.70, 76.0,
     "New backbone bb27; s5 has better min than s3 (76 vs 72)"),
    ("rbx1_binder_62_T01_s5", "rbx1_binder_62", 85.80, 77.0,
     "New backbone bb62; s5 is cleanest (min=77, vs s4's min=60)"),
    ("rbx1_binder_57_T01_s5", "rbx1_binder_57", 85.55, 60.0,
     "New backbone bb57; only one sequence available from this backbone"),
    ("rbx1_binder_82_T01_s1", "rbx1_binder_82", 83.94, 67.0,
     "2nd from bb82; adds sequence diversity within backbone"),
    ("rbx1_binder_70_T01_s5", "rbx1_binder_70", 82.93, 80.0,
     "New backbone bb70; excellent min=80 — tightest pLDDT distribution in remaining pool"),
    ("rbx1_binder_27_T01_s3", "rbx1_binder_27", 83.86, 72.0,
     "2nd from bb27; paired with s5 for backbone-level coverage"),
    ("rbx1_binder_5_T01_s4",  "rbx1_binder_5",  83.95, 72.0,
     "New backbone bb5; s4 is best representative (min=72 vs s5's 55)"),
    ("rbx1_binder_45_T01_s3", "rbx1_binder_45", 81.52, 65.0,
     "2nd from bb45: s1 passed at pairAB=0.752 — extend coverage within passing backbone"),
    ("rbx1_binder_38_T01_s5", "rbx1_binder_38", 80.50, 62.0,
     "New backbone bb38; sole representative in remaining pool"),
    ("rbx1_binder_47_T01_s5", "rbx1_binder_47", 79.44, 60.0,
     "New backbone bb47; s5 marginally better than s2 by mean pLDDT"),
    ("rbx1_binder_74_T01_s1", "rbx1_binder_74", 77.82, 65.0,
     "New backbone bb74; s1 is cleanest representative (min=65 vs s3's 62)"),
    ("rbx1_binder_86_T01_s1", "rbx1_binder_86", 75.33, 63.0,
     "New backbone bb86; sole representative in remaining pool"),
]


# ── Load data ─────────────────────────────────────────────────────────────────
def load_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))

batch1_rows = {r["sequence_id"]: r for r in load_csv(BATCH1_CSV)}
esmfold_rows = {r["sequence_id"]: r for r in load_csv(ESMFOLD_V2_CSV)}
existing_validated = load_csv(VALIDATED_CSV)
existing_ids = {r["sequence_id"] for r in existing_validated}


# ── STEP 1: Append 12 PASS to validated CSV ───────────────────────────────────
print("=" * 65)
print("STEP 1 — Appending 12 PASS candidates to rbx1_rfdiff_validated.csv")
print("=" * 65)

validated_fields = [
    "sequence_id", "backbone_id", "temperature", "binder_length",
    "monomer_plddt", "monomer_plddt_min", "complex_plddt", "plddt_delta",
    "pair_iptm_AB", "iptm", "ptm", "boltz_gate", "validation_stage",
    "binder_chain_sequence",
]

new_rows = []
for sid in BATCH1_PASS:
    if sid in existing_ids:
        print("  SKIP (already present): %s" % sid)
        continue
    b = batch1_rows[sid]
    e = esmfold_rows.get(sid, {})
    new_rows.append({
        "sequence_id":     sid,
        "backbone_id":     b.get("backbone_id", ""),
        "temperature":     b.get("temperature", ""),
        "binder_length":   b.get("binder_length", ""),
        "monomer_plddt":   b.get("monomer_plddt", ""),
        "monomer_plddt_min": e.get("min_plddt", ""),
        "complex_plddt":   b.get("complex_plddt", ""),
        "plddt_delta":     b.get("plddt_delta", ""),
        "pair_iptm_AB":    b.get("pair_iptm_AB", ""),
        "iptm":            b.get("iptm", ""),
        "ptm":             b.get("ptm", ""),
        "boltz_gate":      "PASS",
        "validation_stage": "boltz_complex_v2_batch1",
        "binder_chain_sequence": b.get("binder_chain_sequence", ""),
    })
    print("  ADD: %-34s  pairAB=%s  cPLDDT=%s" % (
        sid, b.get("pair_iptm_AB","?"), b.get("complex_plddt","?")))

all_validated = existing_validated + new_rows
with open(VALIDATED_CSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=validated_fields)
    w.writeheader()
    w.writerows(all_validated)
print("\n  Written %d total rows → %s" % (len(all_validated), VALIDATED_CSV))


# ── STEP 2: Write reserve CSV ─────────────────────────────────────────────────
print()
print("=" * 65)
print("STEP 2 — Writing reserve CSV")
print("=" * 65)

reserve_fields = [
    "sequence_id", "backbone_id", "temperature", "binder_length",
    "monomer_plddt", "monomer_plddt_min", "complex_plddt", "plddt_delta",
    "pair_iptm_AB", "iptm", "ptm", "failure_reason", "binder_chain_sequence",
]

# Load existing reserve if present
existing_reserve = []
existing_reserve_ids = set()
if RESERVE_CSV.exists():
    existing_reserve = load_csv(RESERVE_CSV)
    existing_reserve_ids = {r["sequence_id"] for r in existing_reserve}

reserve_rows = list(existing_reserve)
for sid, reason in BATCH1_RESERVE.items():
    if sid in existing_reserve_ids:
        print("  SKIP (already in reserve): %s" % sid)
        continue
    b = batch1_rows[sid]
    e = esmfold_rows.get(sid, {})
    reserve_rows.append({
        "sequence_id":     sid,
        "backbone_id":     b.get("backbone_id", ""),
        "temperature":     b.get("temperature", ""),
        "binder_length":   b.get("binder_length", ""),
        "monomer_plddt":   b.get("monomer_plddt", ""),
        "monomer_plddt_min": e.get("min_plddt", ""),
        "complex_plddt":   b.get("complex_plddt", ""),
        "plddt_delta":     b.get("plddt_delta", ""),
        "pair_iptm_AB":    b.get("pair_iptm_AB", ""),
        "iptm":            b.get("iptm", ""),
        "ptm":             b.get("ptm", ""),
        "failure_reason":  reason,
        "binder_chain_sequence": b.get("binder_chain_sequence", ""),
    })
    print("  RESERVE: %-34s  %s" % (sid, reason))

with open(RESERVE_CSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=reserve_fields)
    w.writeheader()
    w.writerows(reserve_rows)
print("\n  Written %d reserve rows → %s" % (len(reserve_rows), RESERVE_CSV))


# ── STEP 3: Validated set summary ─────────────────────────────────────────────
print()
print("=" * 65)
print("STEP 3 — Validated set summary")
print("=" * 65)
print("Total validated: %d" % len(all_validated))
print()

# By source batch
batches = {}
for r in all_validated:
    s = r.get("validation_stage", "unknown")
    batches[s] = batches.get(s, 0) + 1
print("By validation stage:")
for s, n in sorted(batches.items()):
    print("  %-32s %d" % (s, n))

# By backbone
print()
bb_counts = {}
for r in all_validated:
    bb = r.get("backbone_id", "?")
    bb_counts[bb] = bb_counts.get(bb, 0) + 1

print("By backbone:")
for bb, n in sorted(bb_counts.items()):
    print("  %-22s %d" % (bb, n))

print()
print("Unique backbones: %d" % len(bb_counts))

# pairAB distribution
vals = []
for r in all_validated:
    try:
        vals.append(float(r["pair_iptm_AB"]))
    except (ValueError, KeyError):
        pass
if vals:
    print()
    print("pair_iptm_AB distribution:")
    for t, label in [(0.8, "excellent"), (0.7, "strong"), (0.6, "good"), (0.5, "pass")]:
        print("  >= %.1f (%s): %d/%d" % (t, label, sum(1 for v in vals if v >= t), len(vals)))
    print("  mean=%.3f  min=%.3f  max=%.3f" % (
        sum(vals)/len(vals), min(vals), max(vals)))


# ── STEP 4: Batch 2 proposal ──────────────────────────────────────────────────
print()
print("=" * 65)
print("STEP 4 — Proposed Boltz batch 2 (18 candidates, 16 backbones)")
print("=" * 65)
print("Exclusions applied:")
print("  - bb23 (both sequences failed interface: pairAB < 0.25)")
print("  - All batch 1 IDs (18 already screened)")
print("  - ESMFold failures (mean < 70 or min < 55)")
print()

# Verify all batch 2 IDs exist in ESMFold v2 CSV
missing_b2 = [c[0] for c in BATCH2_PROPOSAL if c[0] not in esmfold_rows]
if missing_b2:
    print("WARNING: these batch 2 IDs not found in ESMFold v2 CSV:")
    for m in missing_b2:
        print("  " + m)
else:
    print("All 18 batch 2 IDs verified in ESMFold v2 CSV.")

print()
print("%3s  %-34s  %-18s  %6s  %6s  %4s  rationale" % (
    "#", "sequence_id", "backbone_id", "mean", "min", "len"))
print("-" * 130)
unique_bbs = set()
for i, (sid, bb, mean_p, min_p, rationale) in enumerate(BATCH2_PROPOSAL, 1):
    unique_bbs.add(bb)
    e = esmfold_rows.get(sid, {})
    blen = e.get("binder_length", "?")
    print("%3d  %-34s  %-18s  %6.1f  %6.1f  %4s  %s" % (
        i, sid, bb, mean_p, min_p, blen, rationale[:65]))

print()
print("Unique backbones in batch 2: %d" % len(unique_bbs))
print("Backbones new to screening:  %d" % len(unique_bbs - set(bb_counts.keys())))
print()
print("To run: python run_boltz_rfdiff_v2_batch2.py")
print("(script not yet written — confirm batch selection first)")
