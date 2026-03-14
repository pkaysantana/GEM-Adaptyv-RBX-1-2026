#!/usr/bin/env python3
"""
ESMFold validation via HuggingFace transformers.
Batched inference for maximum GPU throughput.
"""
import csv, gc, sys
import torch
from pathlib import Path
from transformers import EsmForProteinFolding, AutoTokenizer

CANDIDATES = Path('/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/final_rbx1_submission_competition.csv')
OUT_SCORED = Path('/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/rbx1_esmfold_scored.csv')
OUT_CSV    = Path('/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/final_rbx1_submission_competition.csv')

BATCH_SIZE = 1   # batched fp16 hits a compute_tm padding bug; single-seq is safe

def flush(msg):
    print(msg, flush=True)

seqs = list(csv.DictReader(CANDIDATES.open()))
flush(f"Loaded {len(seqs)} sequences")

flush("Loading ESMFold model (fp16)...")
tokenizer = AutoTokenizer.from_pretrained("facebook/esmfold_v1")
model     = EsmForProteinFolding.from_pretrained("facebook/esmfold_v1", low_cpu_mem_usage=True)
model     = model.cuda().bfloat16().eval()
model.trunk.set_chunk_size(64)
flush(f"Model loaded — GPU: {torch.cuda.memory_allocated()/1e9:.1f} GB / {torch.cuda.get_device_properties(0).total_memory/1e9:.1f} GB")

# Fully replace compute_tm — nan-safe fp32 version (fixes fp16 NaN → empty nonzero)
import transformers.models.esm.modeling_esmfold as _esmfold_mod
from transformers.models.esm.openfold_utils.loss import _calculate_bin_centers
import torch.nn.functional as _F

def _safe_compute_tm(logits, residue_weights=None, max_bin=31, no_bins=64, eps=1e-8, **kwargs):
    logits = logits.float()
    logits = torch.nan_to_num(logits, nan=0.0, posinf=0.0, neginf=0.0)
    if residue_weights is None:
        residue_weights = logits.new_ones(logits.shape[-2])
    boundaries   = torch.linspace(0, max_bin, steps=(no_bins - 1), device=logits.device)
    bin_centers  = _calculate_bin_centers(boundaries)
    n            = logits.shape[-2]
    d0           = 1.24 * (max(n, 19) - 15) ** (1.0 / 3) - 1.8
    probs        = _F.softmax(logits, dim=-1)
    tm_per_bin   = 1.0 / (1 + (bin_centers ** 2) / (d0 ** 2))
    pred_tm      = torch.sum(probs * tm_per_bin, dim=-1)
    normed_mask  = residue_weights / (eps + residue_weights.sum())
    per_align    = torch.sum(pred_tm * normed_mask, dim=-1)
    weighted     = torch.nan_to_num(per_align * residue_weights, nan=0.0)
    if weighted.numel() == 0:
        return logits.new_zeros(())
    idx = weighted.argmax()
    return per_align.flatten()[idx] if per_align.dim() > 0 else per_align

_esmfold_mod.compute_tm = _safe_compute_tm
flush("Replaced compute_tm with nan-safe fp32 version")

results = []
names   = [r['Name']     for r in seqs]
seqlist = [r['Sequence'] for r in seqs]

# Process in batches
for batch_start in range(0, len(seqlist), BATCH_SIZE):
    batch_names = names[batch_start : batch_start + BATCH_SIZE]
    batch_seqs  = seqlist[batch_start : batch_start + BATCH_SIZE]

    try:
        inputs = tokenizer(batch_seqs, return_tensors="pt",
                           add_special_tokens=False, padding=True)
        inputs = {k: v.cuda() for k, v in inputs.items()}

        with torch.no_grad():
            output = model(**inputs)

        # output.plddt shape: [batch, L, 1] or [batch, L]
        plddt_batch = output.plddt.squeeze(-1).float()  # [batch, L]

        for i, (name, seq) in enumerate(zip(batch_names, batch_seqs)):
            # Only average over real (non-padded) positions
            L = len(seq)
            mean_plddt = plddt_batch[i, :L].mean().item() * 100
            results.append({'name': name, 'sequence': seq, 'plddt': mean_plddt})
            flush(f"  {name}: pLDDT={mean_plddt:.1f}")

    except RuntimeError as e:
        if "out of memory" in str(e):
            flush(f"  OOM on batch {batch_start}-{batch_start+BATCH_SIZE}, falling back to batch_size=1")
            torch.cuda.empty_cache()
            for name, seq in zip(batch_names, batch_seqs):
                try:
                    inp = tokenizer([seq], return_tensors="pt", add_special_tokens=False)
                    inp = {k: v.cuda() for k, v in inp.items()}
                    with torch.no_grad():
                        out = model(**inp)
                    plddt = out.plddt.squeeze().float()[:len(seq)].mean().item() * 100
                    results.append({'name': name, 'sequence': seq, 'plddt': plddt})
                    flush(f"  {name}: pLDDT={plddt:.1f}")
                    torch.cuda.empty_cache()
                except Exception as e2:
                    flush(f"  {name} FAILED: {e2}")
                    results.append({'name': name, 'sequence': seq, 'plddt': 0.0})
        else:
            flush(f"  Batch error: {e}")
            for name, seq in zip(batch_names, batch_seqs):
                results.append({'name': name, 'sequence': seq, 'plddt': 0.0})

    torch.cuda.empty_cache()
    gc.collect()

# Sort by pLDDT descending
results.sort(key=lambda x: x['plddt'], reverse=True)

plddt_vals = [r['plddt'] for r in results]
flush(f"\n{'='*50}")
flush(f"pLDDT results ({len(results)} sequences):")
flush(f"  Mean:   {sum(plddt_vals)/len(plddt_vals):.1f}")
flush(f"  Range:  {min(plddt_vals):.1f} - {max(plddt_vals):.1f}")
flush(f"  >= 70:  {sum(1 for p in plddt_vals if p >= 70)}")
flush(f"  >= 60:  {sum(1 for p in plddt_vals if p >= 60)}")
flush(f"  >= 50:  {sum(1 for p in plddt_vals if p >= 50)}")

# Write scored CSV
with OUT_SCORED.open('w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Name', 'Sequence', 'pLDDT'])
    for r in results:
        w.writerow([r['name'], r['sequence'], f"{r['plddt']:.2f}"])
flush(f"\nWrote: {OUT_SCORED}")

# Rewrite competition CSV ranked by pLDDT
with OUT_CSV.open('w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Name', 'Sequence'])
    for i, r in enumerate(results[:100], 1):
        w.writerow([f"RBX1_MPNN_{i:03d}", r['sequence']])
flush(f"Wrote: {OUT_CSV} (re-ranked by pLDDT)")

flush("\nTop 10 by pLDDT:")
for r in results[:10]:
    flush(f"  {r['name']}: {r['plddt']:.1f}  {r['sequence'][:50]}...")
