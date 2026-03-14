# Complete Parameter Reference

## Epitope Selection Parameters

| Parameter | Value | Description |
|---|---|---|
| `pesto_binding_threshold` | 0.3 | Per-residue binding probability cutoff |
| `enable_glycosylation_prediction` | True | Run glycosylation ensemble prediction |
| `glycosylation_high_risk_threshold` | 0.5 | Probability cutoff for high-risk sites |
| `epitope_clustering.eps` | 10.0 A | DBSCAN neighborhood radius |
| `epitope_clustering.min_samples` | 3 | DBSCAN minimum cluster size |
| `epitope_scoring.pesto_weight` | 1.0 | Weight for PeSTo score in composite |
| `epitope_scoring.hydrophobic_bonus` | 0.1 | Bonus for hydrophobic residues |
| `epitope_scoring.aromatic_bonus` | 0.15 | Bonus for aromatic residues |
| `epitope_scoring.glyco_penalty_weight` | 0.3 | Penalty weight for glycosylation risk |
| `epitope_scoring.max_hotspot_residues` | 6 | Maximum residues per cluster for RFdiffusion |

### Amino Acid Classifications

| Category | Residues |
|---|---|
| Hydrophobic | ALA, VAL, ILE, LEU, MET, PHE, TRP, TYR, PRO |
| Aromatic | PHE, TRP, TYR, HIS |
| Positively charged | ARG, LYS |
| Negatively charged | ASP, GLU |
| Polar | SER, THR, ASN, GLN, CYS |

## Backbone Generation Parameters

| Parameter | Value | Description |
|---|---|---|
| `default_binder_length_range` | 150--200 | Fallback binder length (residues) |
| `use_beta_model` | False | Use RFdiffusion beta model variant |
| `max_backbones_per_container` | 10 | Max designs per RFdiffusion worker |

## Sequence Generation Parameters

| Parameter | Value | Description |
|---|---|---|
| `default_initial_temperature` | 1.0 | Starting sampling temperature |
| `temperature_decay_factor` | 0.1 | Exponential decay per round |
| `sequences_per_round` | 10 | Sequences kept per round (after filtering) |
| `max_sequences_per_round` | 100 | Hard cap on generation per round |
| `sequence_generation_tool` | `"proteinmpnn"` | Default inverse folding tool |
| `proteinmpnn_seed` | 37 | Default random seed |
| `binder_chain_id` | `"X"` | Chain ID for binder in RFdiffusion output |

### ProteinMPNN Parameters

| Parameter | Value |
|---|---|
| `model_type` | `"soluble"` |
| `chains_to_design` | `"X"` |
| `omit_AAs` | `"X"` |
| `seed` | 37 |
| `batch_size` | 1 |
| `fixed_residues` | Optional (`"A:10,15,20;B:5,25"`) |

### ESM-IF1 Parameters

| Parameter | Value |
|---|---|
| `mode` | `"sample"` |
| `padding_length` | 10 |
| `multichain_backbone` | True |

Confidence normalization: `1 / (1 + exp(-(log_likelihood + 2.0) * 1.5))`

## Validation Thresholds

| Metric | Lenient | Balanced (default) | Strict |
|---|---|---|---|
| pLDDT | >= 50.0 | >= 70.0 | >= 80.0 |
| iPTM | >= 0.50 | >= 0.65 | >= 0.75 |
| ipSAE | >= 0.3 | >= 0.5 | >= 0.7 |
| TM-score | >= 0.5 | >= 0.5 | >= 0.5 |
| DockQ | >= 0.23 | >= 0.23 | >= 0.23 |

TM-score and DockQ thresholds are fixed across all confidence levels.

## Boltz-2 Structure Prediction Parameters

| Parameter | Value | Description |
|---|---|---|
| `recycling_steps` | 3 | Structure refinement iterations |
| `sampling_steps` | 200 | Diffusion sampling steps |
| `diffusion_samples` | 1 | Number of structure samples |
| `step_scale` | 1.638 | Diffusion step size |

## Iteration Limits

| Parameter | Default | Description |
|---|---|---|
| `backbone_rounds` | 100 | Number of backbone structures to try |
| `sequence_rounds` | 10 | Sequence temperature rounds per backbone |
| `num_designs` | 100 | Target number of valid designs |
| `max_parallel_workers` | 500 | Maximum concurrent validation workers |
