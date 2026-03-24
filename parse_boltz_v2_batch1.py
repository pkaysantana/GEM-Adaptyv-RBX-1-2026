import csv
from pathlib import Path

csv_path = Path("/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/rbx1_boltz_rfdiff_v2_batch1_scores.csv")
if not csv_path.exists():
    print("ERROR: score CSV not found:", csv_path)
    raise SystemExit(1)

rows = []
with open(csv_path) as f:
    for row in csv.DictReader(f):
        rows.append(row)

ok = [r for r in rows if r["status"] == "ok" and r["pair_iptm_AB"] not in ("", "None", None)]
ranked = sorted(ok, key=lambda r: -float(r["pair_iptm_AB"]))

PASS_PAIR  = 0.50
PASS_IPTM  = 0.60
PASS_DELTA = -20.0

passed, dropped = [], []
for r in ranked:
    pab   = float(r["pair_iptm_AB"])
    iptm  = float(r["iptm"])
    delta = float(r["plddt_delta"]) if r["plddt_delta"] not in ("", "None", None) else -999
    if pab >= PASS_PAIR and iptm >= PASS_IPTM and delta >= PASS_DELTA:
        passed.append(r)
    else:
        dropped.append(r)

print("=== Batch 1 results (rbx1_boltz_rfdiff_v2_batch1_scores.csv) ===")
print("Total scored: %d  |  PASS: %d  |  DROP: %d" % (len(ok), len(passed), len(dropped)))
print()
print("%-34s %7s  %6s  %7s  %7s  %6s  verdict" % (
    "sequence_id", "pairAB", "iPTM", "cPLDDT", "mPLDDT", "delta"))
print("-" * 90)
for r in ranked:
    pab   = float(r["pair_iptm_AB"])
    iptm  = float(r["iptm"])
    cpld  = float(r["complex_plddt"])
    mpld  = float(r["monomer_plddt"])
    delta = float(r["plddt_delta"]) if r["plddt_delta"] not in ("", "None", None) else -999
    verdict = "PASS" if (pab >= PASS_PAIR and iptm >= PASS_IPTM and delta >= PASS_DELTA) else "DROP"
    print("%-34s %7.3f  %6.3f  %7.1f  %7.1f  %6.1f  %s" % (
        r["sequence_id"], pab, iptm, cpld, mpld, delta, verdict))

print()
print("--- PASS list ---")
for r in passed:
    pab  = float(r["pair_iptm_AB"])
    iptm = float(r["iptm"])
    cpld = float(r["complex_plddt"])
    blen = r["binder_length"]
    print("  %-34s  pairAB=%.3f  iPTM=%.3f  cPLDDT=%.1f  len=%s" % (
        r["sequence_id"], pab, iptm, cpld, blen))

print()
print("--- DROP list ---")
for r in dropped:
    pab   = float(r["pair_iptm_AB"])
    iptm  = float(r["iptm"])
    delta = float(r["plddt_delta"]) if r["plddt_delta"] not in ("", "None", None) else -999
    reasons = []
    if pab   < PASS_PAIR:  reasons.append("pairAB=%.3f<%.2f" % (pab,  PASS_PAIR))
    if iptm  < PASS_IPTM:  reasons.append("iPTM=%.3f<%.2f"   % (iptm, PASS_IPTM))
    if delta < PASS_DELTA: reasons.append("delta=%.1f<%.1f"  % (delta, PASS_DELTA))
    print("  %-34s  (%s)" % (r["sequence_id"], ", ".join(reasons)))
