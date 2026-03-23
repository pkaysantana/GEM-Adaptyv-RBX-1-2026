#!/usr/bin/env python3
"""
First-pass ESMFold monomer screening using HuggingFace EsmForProteinFolding.
Reads rbx1_rfdiff_mpnn_v2_filtered.csv, folds each binder, extracts pLDDT.
"""
import csv
import os
import sys
import torch
from collections import Counter

FILT_CSV  = "/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/rbx1_rfdiff_mpnn_v2_filtered.csv"
OUT_DIR   = "/home/on/esmfold_rfdiff_v2_passing"
SCORE_CSV = "/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/rbx1_rfdiff_esmfold_v2_scores.csv"
HF_MODEL  = "facebook/esmfold_v1"

os.makedirs(OUT_DIR, exist_ok=True)

# -- load sequences -----------------------------------------------------------
sequences = []
with open(FILT_CSV) as fh:
    for row in csv.DictReader(fh):
        sequences.append({
            "sequence_id":           row["sequence_id"],
            "backbone_id":           row["backbone_id"],
            "temperature":           row["temperature"],
            "binder_chain_sequence": row["binder_chain_sequence"],
            "binder_length":         int(row["binder_length"]),
        })

print(f"Sequences to fold:  {len(sequences)}")
print(f"Output PDBs      -> {OUT_DIR}")
print(f"Score CSV        -> {SCORE_CSV}\n")

# -- load model ---------------------------------------------------------------
print(f"Loading EsmForProteinFolding from {HF_MODEL} ...")
from transformers import AutoTokenizer, EsmForProteinFolding

tokenizer = AutoTokenizer.from_pretrained(HF_MODEL)
model = EsmForProteinFolding.from_pretrained(HF_MODEL, low_cpu_mem_usage=True)

device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)
model = model.eval()
if device == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")
else:
    print("WARNING: running on CPU — will be slow")

# keep ESM trunk in float32 for numerical stability on nightly torch
model.esm = model.esm.float()
print("Model ready.\n")

# -- pLDDT extraction from output ---------------------------------------------
def get_plddt_per_residue(output, seq_len):
    """
    output.plddt shape: (batch, seq_len, 37) — pLDDT per residue per atom37.
    Use Calpha (atom37 index 1) as canonical per-residue pLDDT.
    Fall back to mean over all atoms if shape is unexpected.
    """
    plddt_tensor = output.plddt  # (1, L, 37) or (1, L)
    if plddt_tensor.dim() == 3:
        plddt_per_res = plddt_tensor[0, :seq_len, 1]  # Calpha column
    elif plddt_tensor.dim() == 2:
        plddt_per_res = plddt_tensor[0, :seq_len]
    else:
        raise ValueError(f"Unexpected plddt shape: {plddt_tensor.shape}")
    return plddt_per_res.float().cpu().tolist()

# -- PDB conversion helper ----------------------------------------------------
def try_save_pdb(output, seq_id, out_dir):
    """Attempt to save PDB using HF openfold utils; skip silently if unavailable."""
    try:
        from transformers.models.esm.openfold_utils.protein import to_pdb, Protein as OFProtein
        from transformers.models.esm.openfold_utils.feats import atom14_to_atom37

        final_atom_positions = atom14_to_atom37(output["positions"][-1], output)
        output_np = {k: v.to("cpu").numpy() for k, v in output.items()
                     if isinstance(v, torch.Tensor)}
        output_np["final_atom_positions"] = final_atom_positions.cpu().numpy()
        output_np["final_atom_mask"] = output["atom37_atom_exists"].cpu().numpy()

        pdbs = model.output_to_pdb(output)
        pdb_path = os.path.join(out_dir, f"{seq_id}.pdb")
        with open(pdb_path, "w") as fh:
            fh.write(pdbs[0])
        return pdb_path
    except Exception as e:
        # Use model's built-in helper if available
        try:
            pdbs = model.output_to_pdb(output)
            pdb_path = os.path.join(out_dir, f"{seq_id}.pdb")
            with open(pdb_path, "w") as fh:
                fh.write(pdbs[0])
            return pdb_path
        except Exception:
            return None

# -- run inference one sequence at a time to avoid OOM -----------------------
results = []
for i, entry in enumerate(sequences):
    seq_id = entry["sequence_id"]
    seq    = entry["binder_chain_sequence"]
    print(f"[{i+1:2d}/{len(sequences)}] {seq_id}  (len={len(seq)})")

    try:
        tokenized = tokenizer(
            [seq],
            return_tensors="pt",
            add_special_tokens=False,
        )
        tokenized = {k: v.to(device) for k, v in tokenized.items()}

        with torch.no_grad():
            output = model(**tokenized)

        plddt_vals = get_plddt_per_residue(output, len(seq))

        mean_p = round(sum(plddt_vals) / len(plddt_vals), 2)
        min_p  = round(min(plddt_vals), 2)
        max_p  = round(max(plddt_vals), 2)
        print(f"         pLDDT  mean={mean_p:.1f}  min={min_p:.1f}  max={max_p:.1f}")

        pdb_path = try_save_pdb(output, seq_id, OUT_DIR)
        if pdb_path:
            print(f"         PDB -> {pdb_path}")

        results.append({**entry,
            "mean_plddt": mean_p,
            "min_plddt":  min_p,
            "max_plddt":  max_p,
            "pdb_path":   pdb_path or "",
            "status":     "ok",
        })

    except Exception as e:
        print(f"         ERROR: {e}")
        results.append({**entry,
            "mean_plddt": None,
            "min_plddt":  None,
            "max_plddt":  None,
            "pdb_path":   "",
            "status":     f"error: {e}",
        })

# -- write score CSV ----------------------------------------------------------
fields = ["sequence_id","backbone_id","temperature","binder_length",
          "mean_plddt","min_plddt","max_plddt","pdb_path","status",
          "binder_chain_sequence"]
with open(SCORE_CSV, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
    w.writeheader()
    w.writerows(results)
print(f"\nScore CSV written -> {SCORE_CSV}")

# -- summary ------------------------------------------------------------------
ok = [r for r in results if r["status"] == "ok" and r["mean_plddt"] is not None]

print("\n== Per-sequence pLDDT ================================================")
print(f"  {'sequence_id':<42} {'len':>4}  {'mean':>6}  {'min':>6}  {'max':>6}  temp")
print(f"  {'-'*42} {'-'*4}  {'-'*6}  {'-'*6}  {'-'*6}  ----")
for r in sorted(ok, key=lambda x: -x["mean_plddt"]):
    print(f"  {r['sequence_id']:<42} {r['binder_length']:>4}  "
          f"{r['mean_plddt']:>6.1f}  {r['min_plddt']:>6.1f}  "
          f"{r['max_plddt']:>6.1f}  {r['temperature']}")

print("\n== Threshold summary =================================================")
for thresh in [80, 70, 60, 50]:
    n = sum(1 for r in ok if r["mean_plddt"] >= thresh)
    print(f"  mean pLDDT >= {thresh}: {n}/{len(ok)}")

# Gate used for downstream screening
gate = [r for r in ok if r["mean_plddt"] >= 70 and r["min_plddt"] >= 55]
print(f"\n  GATE (mean>=70 AND min>=55): {len(gate)}/{len(ok)}")

print("\n== Distribution =======================================================")
temp_pass = Counter(r["temperature"] for r in ok)
print("  By temperature:")
for t in sorted(temp_pass):
    print(f"    {t}: {temp_pass[t]} sequences")

bb_pass = Counter(r["backbone_id"] for r in ok)
print("  Backbone hits (all):")
for bb, cnt in sorted(bb_pass.items(), key=lambda x: (-x[1], x[0])):
    print(f"    {bb}: {cnt} sequence(s)")

errors = [r for r in results if r["status"] != "ok"]
if errors:
    print(f"\nERRORS ({len(errors)}):")
    for r in errors:
        print(f"  {r['sequence_id']}: {r['status']}")
else:
    print(f"\nNo errors.")
