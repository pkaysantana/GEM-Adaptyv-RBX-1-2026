# Validation Metrics Reference

## pLDDT (predicted Local Distance Difference Test)

| Property | Value |
|---|---|
| **Range** | 0--100 |
| **Source tool** | Boltz-2 |
| **What it measures** | Per-residue structural confidence -- how confident the model is in the local structure around each residue |
| **Interpretation** | >90: Very high confidence. 70--90: Confident. 50--70: Low confidence. <50: Very low / disordered |
| **Pipeline usage** | Averaged across all residues in the predicted complex |

## iPTM (interface Predicted TM-score)

| Property | Value |
|---|---|
| **Range** | 0--1 |
| **Source tool** | Boltz-2 |
| **What it measures** | Predicted quality of protein-protein interfaces -- how well the model expects chains to interact |
| **Interpretation** | >0.8: High-confidence interface. 0.6--0.8: Moderate confidence. <0.6: Low confidence / unlikely to interact |
| **Pipeline usage** | Global iPTM across all chain interfaces in the predicted complex |

## ipSAE (interface symmetrized Predicted Alignment Error)

| Property | Value |
|---|---|
| **Range** | 0--1 (higher is better) |
| **Source tool** | Boltz-2, per-chain-pair |
| **What it measures** | Interface structural alignment quality -- averaged over both alignment directions between binder and target chains |
| **Computation** | `avg(d0res_min, d0res_max)` for binder-target chain pairs only; target-target pairs are excluded |
| **Interpretation** | >0.7: Strong interface prediction. 0.5--0.7: Acceptable. <0.5: Weak or absent interface |
| **Pipeline usage** | Binder-target pairs only (chain X vs target chains). Skipped (not failed) if no interface detected |

## TM-score (Template Modeling score)

| Property | Value |
|---|---|
| **Range** | 0--1 |
| **Source tool** | US-align (monomer mode) |
| **What it measures** | Structural similarity between predicted binder fold and the RFdiffusion backbone -- whether the sequence folds into the intended shape |
| **Interpretation** | >0.5: Same fold. 0.3--0.5: Partial similarity. <0.3: Different fold |
| **Pipeline usage** | Binder chain X only; normalized by backbone (reference) length |

## DockQ

| Property | Value |
|---|---|
| **Range** | 0--1 |
| **Source tool** | DockQ |
| **What it measures** | Overall quality of predicted binder-target complex vs RFdiffusion design. Combines interface RMSD, ligand RMSD, and fraction of native contacts |
| **Interpretation** | >=0.80: High quality. >=0.49: Medium quality. >=0.23: Acceptable. <0.23: Incorrect |
| **Component metrics** | iRMSD (interface RMSD), LRMSD (ligand RMSD), fnat (fraction native contacts) |
| **Pipeline usage** | Binder-target interface pairs only (e.g., X-A); excludes target-target pairs |

## Solubility

| Property | Value |
|---|---|
| **Range** | Binary: `"soluble"` or `"insoluble"` (with continuous score) |
| **Source tool** | Fine-tuned ESM-2 classifier |
| **What it measures** | Predicted E. coli expression solubility -- whether the protein would be soluble when recombinantly expressed |
| **Interpretation** | `"soluble"` = proceed to structure prediction; `"insoluble"` = early termination |
| **Pipeline usage** | First validation check; enables early termination before expensive structure prediction |
