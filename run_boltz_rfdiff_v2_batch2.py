#!/usr/bin/env python3
"""
Boltz-2 complex screening — RFdiffusion v2 batch 2.

18 candidates from 16 unique backbones.
Change from original proposal: bb25 removed (already validated); replaced
with rbx1_binder_32_T01_s1 (bb32, last genuinely new backbone, min=65).

Pass criteria:
  pair_iptm_AB >= 0.50
  iptm         >= 0.60
  delta_plddt  >= -20.0

Outputs:
  boltz_rfdiff_v2_inputs/   (FASTAs; shared with batch 1 — new files appended)
  boltz_rfdiff_v2_outputs/  (Boltz predictions)
  rbx1_boltz_rfdiff_v2_batch2_scores.csv
"""

import argparse, csv, json, os, shutil, subprocess, sys
from pathlib import Path

RBX1_SEQ = (
    "KKRFEVKKWNAVALWAWDIVVDNCAICRNHIMDLCIECQANQASATSEECTVAWGVCNHAFHFHCISRWLK"
    "TRQVCPLDNREWEFQKY"
)

# ── Batch 2 candidates (18, 16 unique backbones) ─────────────────────────────
# (sequence_id, backbone_id, mean_plddt, min_plddt, rationale)
BATCH2 = [
    ("rbx1_binder_55_T01_s3", "rbx1_binder_55", 91.32, 72.0,
     "3rd from bb55 — both b1 reps passed (0.752, 0.737); proven backbone"),
    ("rbx1_binder_32_T01_s1", "rbx1_binder_32", 79.55, 65.0,
     "Last new backbone; best available (min=65, exactly at floor); bb58/39/21 worse"),
    ("rbx1_binder_28_T01_s2", "rbx1_binder_28", 89.14, 81.0,
     "Second chance bb28; s5 dropped (pairAB=0.423); s2 min=81 vs s5 min=73"),
    ("rbx1_binder_1_T02_s5",  "rbx1_binder_1",  88.60, 79.0,
     "Follow-up bb1; s3 passed at 0.796 — test adjacent sequence"),
    ("rbx1_binder_61_T01_s3", "rbx1_binder_61", 86.79, 76.0,
     "Follow-up bb61; s4 passed at 0.817 — second rep from strong backbone"),
    ("rbx1_binder_82_T01_s3", "rbx1_binder_82", 86.85, 73.0,
     "New backbone bb82; top of 4 available sequences"),
    ("rbx1_binder_27_T01_s5", "rbx1_binder_27", 86.70, 76.0,
     "New backbone bb27; s5 cleaner min (76 vs s3's 72)"),
    ("rbx1_binder_62_T01_s5", "rbx1_binder_62", 85.80, 77.0,
     "New backbone bb62; s5 cleanest (min=77 vs s4's 60)"),
    ("rbx1_binder_57_T01_s5", "rbx1_binder_57", 85.55, 60.0,
     "New backbone bb57; sole representative in pool"),
    ("rbx1_binder_82_T01_s1", "rbx1_binder_82", 83.94, 67.0,
     "2nd from bb82; sequence diversity within new backbone"),
    ("rbx1_binder_70_T01_s5", "rbx1_binder_70", 82.93, 80.0,
     "New backbone bb70; best min in remaining pool (80)"),
    ("rbx1_binder_27_T01_s3", "rbx1_binder_27", 83.86, 72.0,
     "2nd from bb27; paired with s5 for backbone coverage"),
    ("rbx1_binder_5_T01_s4",  "rbx1_binder_5",  83.95, 72.0,
     "New backbone bb5; s4 cleanest (min=72 vs s5's 55)"),
    ("rbx1_binder_45_T01_s3", "rbx1_binder_45", 81.52, 65.0,
     "2nd from bb45; s1 passed at 0.752 — extend proven backbone"),
    ("rbx1_binder_38_T01_s5", "rbx1_binder_38", 80.50, 62.0,
     "New backbone bb38; sole representative"),
    ("rbx1_binder_47_T01_s5", "rbx1_binder_47", 79.44, 60.0,
     "New backbone bb47; s5 marginally better than s2"),
    ("rbx1_binder_74_T01_s1", "rbx1_binder_74", 77.82, 65.0,
     "New backbone bb74; s1 cleanest (min=65 vs s3's 62)"),
    ("rbx1_binder_86_T01_s1", "rbx1_binder_86", 75.33, 63.0,
     "New backbone bb86; sole representative"),
]

CANDIDATE_IDS = [c[0] for c in BATCH2]

PASS_PAIR  = 0.50
PASS_IPTM  = 0.60
PASS_DELTA = -20.0

ESMFOLD_V2_CSV = Path(
    "/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/"
    "GEM-Adaptyv-RBX-1-2026/rbx1_rfdiff_esmfold_v2_scores.csv"
)


def parse_args():
    repo_root = Path(__file__).resolve().parent
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default=str(repo_root))
    p.add_argument("--recycling-steps",   type=int, default=3)
    p.add_argument("--diffusion-samples", type=int, default=1)
    p.add_argument("--sampling-steps",    type=int, default=200)
    p.add_argument("--override", action="store_true", default=True)
    return p.parse_args()


def find_boltz():
    for p in ["/home/on/miniforge3/envs/protein-design/bin/boltz", shutil.which("boltz")]:
        if p and Path(p).is_file() and os.access(p, os.X_OK):
            return p
    sys.exit("ERROR: boltz binary not found.")


def load_sequences(csv_path, wanted_ids):
    found = {}
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            if row["sequence_id"] in wanted_ids:
                found[row["sequence_id"]] = row
    missing = set(wanted_ids) - set(found)
    if missing:
        sys.exit("ERROR: IDs not in %s:\n  %s" % (csv_path.name, sorted(missing)))
    return found


def safe_load_confidence(path):
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError) as e:
        print("  WARNING: %s: %s" % (path, e))
        return None


def extract_pair_iptm(conf):
    pci = conf.get("pair_chains_iptm", {})
    try:
        return round(pci["0"]["1"], 4)
    except (KeyError, TypeError):
        return None


def find_confidence_json(out_root, run_name, seq_id):
    expected = out_root / run_name / "predictions" / seq_id / ("confidence_%s_model_0.json" % seq_id)
    if expected.exists():
        return expected
    matches = list(out_root.rglob("confidence_%s_model_0.json" % seq_id))
    if matches:
        if len(matches) > 1:
            print("  WARNING: multiple hits for %s, using first" % seq_id)
        return matches[0]
    return None


def main():
    args     = parse_args()
    out_root = Path(args.out_dir)
    input_dir  = out_root / "boltz_rfdiff_v2_inputs"
    output_dir = out_root / "boltz_rfdiff_v2_outputs"
    score_csv  = out_root / "rbx1_boltz_rfdiff_v2_batch2_scores.csv"

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    boltz_bin = find_boltz()

    # ── Manifest ─────────────────────────────────────────────────────────────
    print("=" * 70)
    print("BATCH 2 — RFdiffusion v2 Boltz complex screen")
    print("  18 candidates  |  16 unique backbones  |  11 new to screening")
    print("  Pass: pair_iptm_AB >= %.2f  |  iPTM >= %.2f  |  delta >= %.1f" % (
        PASS_PAIR, PASS_IPTM, PASS_DELTA))
    print("=" * 70)
    print()
    print("%-3s  %-34s  %-18s  %6s  %6s  %4s" % (
        "#", "sequence_id", "backbone_id", "mean", "min", "len"))
    print("-" * 75)
    for i, (sid, bb, mean_p, min_p, _) in enumerate(BATCH2, 1):
        tag = " [new bb]" if bb not in {
            "rbx1_binder_55","rbx1_binder_28","rbx1_binder_1",
            "rbx1_binder_61","rbx1_binder_45"} else " [follow-up]"
        print("%-3d  %-34s  %-18s  %6.1f  %6.1f" % (i, sid, bb, mean_p, min_p))
    print()

    # ── Load sequences ────────────────────────────────────────────────────────
    print("=" * 70)
    print("STEP 1 — Loading sequences")
    print("=" * 70)
    seqs = load_sequences(ESMFOLD_V2_CSV, CANDIDATE_IDS)
    print("  Loaded %d sequences." % len(seqs))

    # ── Write FASTAs ──────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("STEP 2 — Writing input FASTAs")
    print("=" * 70)
    for sid in CANDIDATE_IDS:
        binder_seq = seqs[sid]["binder_chain_sequence"]
        fasta = input_dir / ("%s.fasta" % sid)
        fasta.write_text(">A|protein\n%s\n>B|protein\n%s\n" % (RBX1_SEQ, binder_seq))
        print("  %s  (%d aa)" % (fasta.name, len(binder_seq)))
    print("\n  %d FASTAs -> %s" % (len(CANDIDATE_IDS), input_dir))

    # ── Run Boltz ─────────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("STEP 3 — Running Boltz-2")
    print("=" * 70)
    cmd = [
        boltz_bin, "predict", str(input_dir),
        "--out_dir",           str(output_dir),
        "--accelerator",       "gpu",
        "--model",             "boltz2",
        "--recycling_steps",   str(args.recycling_steps),
        "--sampling_steps",    str(args.sampling_steps),
        "--diffusion_samples", str(args.diffusion_samples),
        "--output_format",     "pdb",
        "--use_msa_server",
        "--no_kernels",
    ]
    if args.override:
        cmd.append("--override")
    print("CMD:", " ".join(cmd))
    print()
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print("WARNING: Boltz exited %d — attempting partial parse" % result.returncode)

    # ── Parse confidence ──────────────────────────────────────────────────────
    print()
    print("=" * 70)
    print("STEP 4 — Parsing confidence scores")
    print("=" * 70)
    run_name = "boltz_results_%s" % input_dir.name
    rows = []

    for sid in CANDIDATE_IDS:
        row = seqs[sid]
        binder_seq = row["binder_chain_sequence"]
        mono_plddt = float(row.get("mean_plddt", 0) or 0)  # already 0-100

        conf_path = find_confidence_json(output_dir, run_name, sid)
        if conf_path is None:
            print("  MISSING: %s" % sid)
            rows.append({
                "sequence_id": sid, "backbone_id": row.get("backbone_id",""),
                "temperature": row.get("temperature",""), "binder_length": len(binder_seq),
                "monomer_plddt": round(mono_plddt,1),
                "iptm": None, "protein_iptm": None, "pair_iptm_AB": None,
                "ptm": None, "complex_plddt": None, "plddt_delta": None,
                "status": "missing", "binder_chain_sequence": binder_seq,
            })
            continue

        conf = safe_load_confidence(conf_path)
        if conf is None:
            rows.append({
                "sequence_id": sid, "backbone_id": row.get("backbone_id",""),
                "temperature": row.get("temperature",""), "binder_length": len(binder_seq),
                "monomer_plddt": round(mono_plddt,1),
                "iptm": None, "protein_iptm": None, "pair_iptm_AB": None,
                "ptm": None, "complex_plddt": None, "plddt_delta": None,
                "status": "parse_error", "binder_chain_sequence": binder_seq,
            })
            continue

        iptm         = round(conf.get("iptm",         0) or 0, 4)
        protein_iptm = round(conf.get("protein_iptm", 0) or 0, 4)
        ptm          = round(conf.get("ptm",          0) or 0, 4)
        complex_plddt = round((conf.get("complex_plddt", 0) or 0) * 100, 2)
        pair_AB      = extract_pair_iptm(conf)
        plddt_delta  = round(complex_plddt - mono_plddt, 1) if mono_plddt else None

        print("  %s" % sid)
        print("    pair_iptm_AB=%.4f  iptm=%.3f  protein_iptm=%.3f" % (
            pair_AB or 0, iptm, protein_iptm))
        print("    ptm=%.3f  complex_pLDDT=%.1f  monomer_pLDDT=%.1f  delta=%+.1f" % (
            ptm, complex_plddt, mono_plddt, plddt_delta or 0))

        rows.append({
            "sequence_id": sid, "backbone_id": row.get("backbone_id",""),
            "temperature": row.get("temperature",""), "binder_length": len(binder_seq),
            "monomer_plddt": round(mono_plddt,1),
            "iptm": iptm, "protein_iptm": protein_iptm, "pair_iptm_AB": pair_AB,
            "ptm": ptm, "complex_plddt": complex_plddt, "plddt_delta": plddt_delta,
            "status": "ok", "binder_chain_sequence": binder_seq,
        })

    # ── Write CSV ─────────────────────────────────────────────────────────────
    fields = ["sequence_id","backbone_id","temperature","binder_length",
              "monomer_plddt","iptm","protein_iptm","pair_iptm_AB",
              "ptm","complex_plddt","plddt_delta","status","binder_chain_sequence"]
    with open(score_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print("\n  Score CSV -> %s" % score_csv)

    # ── Results table ─────────────────────────────────────────────────────────
    ok = [r for r in rows if r["status"] == "ok" and r["pair_iptm_AB"] is not None]
    if not ok:
        print("\nNo successful predictions.")
        return

    ranked = sorted(ok, key=lambda r: (-(r["pair_iptm_AB"] or 0), -(r["iptm"] or 0)))

    print()
    print("=" * 70)
    print("RESULTS — ranked by pair_iptm_AB")
    print("=" * 70)
    print("%-34s %4s  %7s  %6s  %7s  %7s  %6s  %s" % (
        "sequence_id","len","pairAB","iPTM","cPLDDT","mPLDDT","delta","verdict"))
    print("-" * 90)

    passed, dropped = [], []
    for r in ranked:
        pab   = float(r["pair_iptm_AB"] or 0)
        iptm  = float(r["iptm"] or 0)
        delta = float(r["plddt_delta"]) if r["plddt_delta"] is not None else -999
        ok_p  = pab >= PASS_PAIR and iptm >= PASS_IPTM and delta >= PASS_DELTA
        verdict = "PASS" if ok_p else "DROP"
        if ok_p:
            passed.append(r)
        else:
            dropped.append(r)
        print("%-34s %4s  %7.3f  %6.3f  %7.1f  %7.1f  %6.1f  %s" % (
            r["sequence_id"], r["binder_length"], pab, iptm,
            float(r["complex_plddt"] or 0), float(r["monomer_plddt"] or 0),
            delta, verdict))

    print()
    print("Tier distribution (pair_iptm_AB):")
    for t, label in [(0.8,"excellent"),(0.6,"good"),(0.5,"pass"),(0.4,"marginal")]:
        n = sum(1 for r in ok if float(r["pair_iptm_AB"] or 0) >= t)
        print("  >= %.1f (%s): %d/%d" % (t, label, n, len(ok)))

    print()
    print("Gate: pairAB >= %.2f  |  iPTM >= %.2f  |  delta >= %.1f" % (
        PASS_PAIR, PASS_IPTM, PASS_DELTA))
    print("%d PASS  /  %d DROP  /  %d missing  (from %d candidates)" % (
        len(passed), len(dropped), len(rows)-len(ok), len(rows)))

    if dropped:
        print()
        print("DROP reasons:")
        for r in dropped:
            pab   = float(r["pair_iptm_AB"] or 0)
            iptm  = float(r["iptm"] or 0)
            delta = float(r["plddt_delta"]) if r["plddt_delta"] is not None else -999
            reasons = []
            if pab   < PASS_PAIR:  reasons.append("pairAB=%.3f<%.2f" % (pab,  PASS_PAIR))
            if iptm  < PASS_IPTM:  reasons.append("iPTM=%.3f<%.2f"   % (iptm, PASS_IPTM))
            if delta < PASS_DELTA: reasons.append("delta=%.1f<%.1f"  % (delta,PASS_DELTA))
            print("  DROP  %-34s  (%s)" % (r["sequence_id"], ", ".join(reasons)))

    if passed:
        print()
        print("Candidates for review (do NOT update validated set yet):")
        for r in passed:
            print("  %-34s  pairAB=%.3f  iPTM=%.3f  cPLDDT=%.1f  len=%s" % (
                r["sequence_id"], float(r["pair_iptm_AB"]),
                float(r["iptm"]), float(r["complex_plddt"] or 0),
                r["binder_length"]))


if __name__ == "__main__":
    main()
