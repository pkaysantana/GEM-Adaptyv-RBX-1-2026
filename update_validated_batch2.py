"""
Append 8 PASS from batch 2 to rbx1_rfdiff_validated.csv.
Append 3 borderline drops to rbx1_rfdiff_reserve.csv.
Print summary.
"""
import csv
from pathlib import Path

ROOT = Path("/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026")
VALIDATED_CSV  = ROOT / "rbx1_rfdiff_validated.csv"
RESERVE_CSV    = ROOT / "rbx1_rfdiff_reserve.csv"
BATCH2_CSV     = ROOT / "rbx1_boltz_rfdiff_v2_batch2_scores.csv"
ESMFOLD_V2_CSV = ROOT / "rbx1_rfdiff_esmfold_v2_scores.csv"

BATCH2_PASS = [
    "rbx1_binder_45_T01_s3",
    "rbx1_binder_38_T01_s5",
    "rbx1_binder_57_T01_s5",
    "rbx1_binder_47_T01_s5",
    "rbx1_binder_62_T01_s5",
    "rbx1_binder_1_T02_s5",
    "rbx1_binder_82_T01_s3",
    "rbx1_binder_61_T01_s3",
]

BATCH2_RESERVE = {
    "rbx1_binder_27_T01_s5": "delta=-22.2 < -20.0 (pairAB=0.832 excellent; fails Δ gate only)",
    "rbx1_binder_86_T01_s1": "iPTM=0.567 < 0.60 (pairAB=0.503; two decimals off on iPTM)",
    "rbx1_binder_27_T01_s3": "iPTM=0.502 < 0.60 (pairAB=0.502; iPTM just under gate)",
}

def load_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))

batch2  = {r["sequence_id"]: r for r in load_csv(BATCH2_CSV)}
esm     = {r["sequence_id"]: r for r in load_csv(ESMFOLD_V2_CSV)}
current = load_csv(VALIDATED_CSV)
current_ids = {r["sequence_id"] for r in current}

VALIDATED_FIELDS = [
    "sequence_id","backbone_id","temperature","binder_length",
    "monomer_plddt","monomer_plddt_min","complex_plddt","plddt_delta",
    "pair_iptm_AB","iptm","ptm","boltz_gate","validation_stage",
    "binder_chain_sequence",
]
RESERVE_FIELDS = [
    "sequence_id","backbone_id","temperature","binder_length",
    "monomer_plddt","monomer_plddt_min","complex_plddt","plddt_delta",
    "pair_iptm_AB","iptm","ptm","failure_reason","binder_chain_sequence",
]

# ── 1. Append PASS to validated ───────────────────────────────────────────────
new_validated = []
for sid in BATCH2_PASS:
    if sid in current_ids:
        print("SKIP (already present): %s" % sid)
        continue
    b = batch2[sid]
    e = esm.get(sid, {})
    new_validated.append({
        "sequence_id":       sid,
        "backbone_id":       b.get("backbone_id",""),
        "temperature":       b.get("temperature",""),
        "binder_length":     b.get("binder_length",""),
        "monomer_plddt":     b.get("monomer_plddt",""),
        "monomer_plddt_min": e.get("min_plddt",""),
        "complex_plddt":     b.get("complex_plddt",""),
        "plddt_delta":       b.get("plddt_delta",""),
        "pair_iptm_AB":      b.get("pair_iptm_AB",""),
        "iptm":              b.get("iptm",""),
        "ptm":               b.get("ptm",""),
        "boltz_gate":        "PASS",
        "validation_stage":  "boltz_complex_v2_batch2",
        "binder_chain_sequence": b.get("binder_chain_sequence",""),
    })

all_validated = current + new_validated
with open(VALIDATED_CSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=VALIDATED_FIELDS)
    w.writeheader()
    w.writerows(all_validated)

# ── 2. Append reserve ─────────────────────────────────────────────────────────
existing_reserve = load_csv(RESERVE_CSV) if RESERVE_CSV.exists() else []
existing_reserve_ids = {r["sequence_id"] for r in existing_reserve}

new_reserve = []
for sid, reason in BATCH2_RESERVE.items():
    if sid in existing_reserve_ids:
        continue
    b = batch2[sid]
    e = esm.get(sid, {})
    new_reserve.append({
        "sequence_id":       sid,
        "backbone_id":       b.get("backbone_id",""),
        "temperature":       b.get("temperature",""),
        "binder_length":     b.get("binder_length",""),
        "monomer_plddt":     b.get("monomer_plddt",""),
        "monomer_plddt_min": e.get("min_plddt",""),
        "complex_plddt":     b.get("complex_plddt",""),
        "plddt_delta":       b.get("plddt_delta",""),
        "pair_iptm_AB":      b.get("pair_iptm_AB",""),
        "iptm":              b.get("iptm",""),
        "ptm":               b.get("ptm",""),
        "failure_reason":    reason,
        "binder_chain_sequence": b.get("binder_chain_sequence",""),
    })

all_reserve = existing_reserve + new_reserve
with open(RESERVE_CSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=RESERVE_FIELDS)
    w.writeheader()
    w.writerows(all_reserve)

# ── 3. Summary ────────────────────────────────────────────────────────────────
print("=" * 65)
print("VALIDATED SET SUMMARY")
print("=" * 65)
print("Total validated: %d  (+%d from batch 2)" % (len(all_validated), len(new_validated)))
print("Reserve:         %d  (+%d from batch 2)" % (len(all_reserve), len(new_reserve)))

# By backbone
print()
print("By backbone:")
bb_rows = {}
for r in all_validated:
    bb = r["backbone_id"]
    bb_rows.setdefault(bb, []).append(r)

# Sort by count desc, then name
for bb, rows in sorted(bb_rows.items(), key=lambda x: (-len(x[1]), x[0])):
    seqs = ", ".join(r["sequence_id"].replace(bb+"_","") for r in rows)
    print("  %-22s %d   (%s)" % (bb, len(rows), seqs))

print()
print("Unique backbones validated: %d" % len(bb_rows))

# By stage
stages = {}
for r in all_validated:
    s = r.get("validation_stage","?")
    stages[s] = stages.get(s, 0) + 1
print()
print("By validation stage:")
for s, n in sorted(stages.items()):
    print("  %-36s %d" % (s, n))

# Top 10 by pair_iptm_AB
print()
print("=" * 65)
print("TOP 10 by pair_iptm_AB")
print("=" * 65)
scored = [(r, float(r["pair_iptm_AB"])) for r in all_validated
          if r.get("pair_iptm_AB") not in ("","None",None)]
scored.sort(key=lambda x: -x[1])
print("%-3s  %-34s  %7s  %6s  %7s  %4s  %s" % (
    "#","sequence_id","pairAB","iPTM","cPLDDT","len","stage"))
print("-" * 85)
for i, (r, pab) in enumerate(scored[:10], 1):
    stage_short = r["validation_stage"].replace("boltz_complex","bc").replace("_v2_","_")
    print("%-3d  %-34s  %7.3f  %6.3f  %7.1f  %4s  %s" % (
        i, r["sequence_id"], pab,
        float(r["iptm"] or 0),
        float(r["complex_plddt"] or 0),
        r["binder_length"],
        stage_short))

# Overall pairAB stats
vals = [v for _, v in scored]
print()
print("pair_iptm_AB across all %d validated:" % len(vals))
print("  mean=%.3f  median=%.3f  min=%.3f  max=%.3f" % (
    sum(vals)/len(vals),
    sorted(vals)[len(vals)//2],
    min(vals), max(vals)))
for t, label in [(0.8,"excellent"),(0.7,"strong"),(0.6,"good")]:
    print("  >= %.1f (%s): %d/%d" % (t, label, sum(1 for v in vals if v >= t), len(vals)))

# ── 4. Exhausted / abandoned backbones ───────────────────────────────────────
print()
print("=" * 65)
print("BACKBONE STATUS")
print("=" * 65)

# All backbones ever screened (batch1 + batch2)
b1_screened = {
    "rbx1_binder_0","rbx1_binder_1","rbx1_binder_11","rbx1_binder_15",
    "rbx1_binder_16","rbx1_binder_23","rbx1_binder_28","rbx1_binder_44",
    "rbx1_binder_45","rbx1_binder_55","rbx1_binder_61","rbx1_binder_63",
    "rbx1_binder_64","rbx1_binder_77","rbx1_binder_87",
}
b2_screened = {
    "rbx1_binder_1","rbx1_binder_5","rbx1_binder_27","rbx1_binder_28",
    "rbx1_binder_32","rbx1_binder_38","rbx1_binder_45","rbx1_binder_47",
    "rbx1_binder_55","rbx1_binder_57","rbx1_binder_61","rbx1_binder_62",
    "rbx1_binder_70","rbx1_binder_74","rbx1_binder_82","rbx1_binder_86",
}
all_screened = b1_screened | b2_screened
validated_bbs = set(bb_rows.keys())

# Classify
abandoned = []   # screened, zero passes
exhausted = []   # validated but all sequences from that bb now screened with no remaining upside

# Backbones with zero validated despite being screened
for bb in sorted(all_screened):
    if bb not in validated_bbs:
        abandoned.append(bb)

print("Abandoned (screened, 0 validated):")
for bb in abandoned:
    print("  %s" % bb)

print()
print("Exhausted (validated but no further unscreened sequences worth testing):")
# bb55: s1,s2,s3,s4 all screened. s2,s4 passed; s3 collapsed (0.198). Done.
# bb23: both sequences dropped (0.221, 0.164). Done.
# bb28: s2 and s5 both dropped. Done.
# bb63: s1 passed; s2 in reserve (0.498). No more sequences. Done.
exhausted_notes = {
    "rbx1_binder_55": "s2+s4 pass; s3 collapsed (0.198); s1 unscreened but bb signal clear",
    "rbx1_binder_23": "both sequences failed (0.221, 0.164) — no interface signal",
    "rbx1_binder_28": "s5+s2 both dropped (0.423, 0.360) — backbone abandoned",
    "rbx1_binder_0":  "dropped (0.325) — no further sequences",
    "rbx1_binder_87": "reserve only (delta=-24.4); s5 failed ESMFold — done",
    "rbx1_binder_32": "dropped (0.465) — last new backbone, no further sequences",
    "rbx1_binder_74": "dropped (0.301) — abandoned",
    "rbx1_binder_5":  "dropped (0.386) — abandoned",
}
for bb, note in exhausted_notes.items():
    print("  %-22s  %s" % (bb, note))

print()
print("Reserve (borderline — not validated, not abandoned):")
for r in all_reserve:
    print("  %-34s  pairAB=%s  reason: %s" % (
        r["sequence_id"], r["pair_iptm_AB"],
        r["failure_reason"][:60]))
