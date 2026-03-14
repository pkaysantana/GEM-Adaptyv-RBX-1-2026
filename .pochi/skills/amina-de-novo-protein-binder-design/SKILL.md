---
name: amina-de-novo-protein-binder-design
description: De novo protein binder design pipeline -- autonomous backbone generation, sequence design, and multi-metric validation. Use when asked to "design a binder", "create a protein binder", "de novo binder design", "binder for [target]", "design something that binds [protein]", or any task involving computational protein binder engineering from a target structure.
---

# De Novo Protein Binder Design Pipeline

## Overview

This pipeline designs novel protein binders for a target protein structure through six phases:

1. **Target Preparation** -- Clean and validate the input PDB
2. **Epitope Selection** -- Identify binding sites via PeSTo + DBSCAN clustering
3. **Binder Length Optimization** -- Calculate optimal binder size from epitope geometry
4. **Backbone Generation** -- Generate candidate scaffolds with RFdiffusion
5. **Sequence Design** -- Design sequences via inverse folding (ProteinMPNN / ESM-IF1)
6. **Validation** -- Multi-metric screening with early termination
7. **Round Advancement** -- Iterate or finalize based on results

### Interaction Model

**Phases 0--1.5 (preparation)**: Run autonomously -- clean the target, select epitopes, determine binder length. No user approval needed.

**Before Phase 2 (backbone generation)**: Present a design plan to the user summarizing: target info, selected epitope and hotspot residues, proposed binder length, number of backbones, and any concerns (large target, polar epitope, etc.). Wait for user approval before proceeding.

**Phases 2--5 (generation + validation)**: Run autonomously after approval. Report results at natural checkpoints (after each round).

### Design Principles

- **Fixed tool pipeline** -- The tools and their order are prescribed (see each phase). Parameters and scale are flexible based on context.
- **Early termination** -- Run cheap checks (solubility) before expensive ones (structure prediction) to save compute.
- **Iterative refinement** -- Start with high-diversity sequence sampling and progressively lower temperature for convergence.

---

## Phase 0: Target Preparation

**Input**: Raw PDB file (from database or user upload).

### Steps

1. Parse PDB for metadata -- Extract experimental method, resolution, chain composition, sequences.
2. Clean structure -- Remove waters/heterogens, restore missing heavy atoms, add hydrogens at physiological pH, standardize non-canonical residues, detect disulfide bonds.
3. Select chains of interest -- Extract relevant chain(s). Can be user-specified or automatic.
4. Quality checks (warnings, not blockers):
   - Targets >2000 residues are computationally expensive downstream
   - Multi-chain targets add complexity to epitope selection

**Output**: Cleaned PDB with metadata (sequences, chain IDs, residue counts).

---

## Phase 1: Epitope Selection

**Purpose**: Identify and rank candidate binding sites on the target surface.

### Step 1: Binding Interface Prediction (PeSTo)

Run PeSTo (Protein Structure Transformer, model `i_v4_1`) to get per-residue protein-protein binding probabilities (0.0--1.0). Classify residues above a threshold (recommended: 0.3) as binding candidates.

### Step 2: Glycosylation Filtering (Optional)

Run glycosylation prediction ensemble (EMNgly, LMNglyPred, ISOGlyP) to identify residues at risk of post-translational glycosylation. Penalize high-risk sites during scoring since glycans physically occlude the surface.

### Step 3: DBSCAN Spatial Clustering

Cluster binding residues by CA coordinates using DBSCAN to group spatially proximal residues into discrete epitope regions. Discard unclustered noise residues.

### Step 4: Hotspot Selection

Rank residues within each cluster by composite score that weighs:
- PeSTo binding probability (primary signal)
- Hydrophobic/aromatic character (favorable for binding interfaces)
- Glycosylation risk (penalty)

Select the best cluster and pick the top-scoring residues (recommended: 3--6) as hotspot residues for RFdiffusion.

> Scoring weights and parameter defaults: `references/parameters.md` -- load when adjusting epitope selection behavior.

---

## Phase 1.5: Binder Length Optimization

**Runs only if** the user did not specify a custom binder length.

### Approach

1. Compute pairwise CA distances between all epitope residues.
2. Take the maximum distance as the **epitope span**.
3. Choose a binder length proportional to the span -- larger epitopes need longer binders to cover the interface. General guidelines:

| Epitope Span | Suggested Binder Length |
|---|---|
| < 20 A (compact) | 50--80 residues |
| 20--40 A (medium) | 70--110 residues |
| 40--60 A (large) | 90--140 residues |
| > 60 A (extended) | 120--180 residues |

Binder length should stay within 50--200 residues. When in doubt, err toward longer binders.

---

## Phase 2: Backbone Generation (RFdiffusion)

**Purpose**: Generate diverse backbone structures complementary to the target epitope.

### Inputs

- Cleaned target PDB from Phase 0
- Hotspot residues from Phase 1 (e.g., `["A42", "A45", "A78"]`)
- Binder length range from Phase 1.5 (e.g., `"70-110"`)
- Number of designs (scale based on target difficulty -- typically 50--200 backbones)

### Execution

- Each call produces backbone PDB files with backbone atoms (N, CA, C, O) for both binder (chain X) and target chains.
- **Parallelization**: Each RFdiffusion call should generate at most **10 designs**. For larger counts, split into parallel calls (e.g., 100 designs = 10 parallel calls x 10 designs each). This is significantly faster than a single call with `num_designs=100`.
- Optional beta model variant available (`use_beta_model`, default: off).

### Output

Independent backbone scaffolds, registered for downstream sequence design.

> Design tips for hotspot selection, target truncation, and scale: `references/design-tips.md` -- load when planning a design campaign or troubleshooting RFdiffusion.

---

## Phase 3: Sequence Design

**Purpose**: Design amino acid sequences predicted to fold into each backbone.

### Temperature Schedule

Use exponential decay across sequence rounds to shift from exploration to convergence. Recommended starting point:

| Round | Temperature | Behavior |
|---|---|---|
| 1 | ~1.0 | High diversity -- broad exploration |
| 2 | ~0.1 | Convergent -- focused sampling |
| 3 | ~0.01 | Refinement -- near-deterministic |

Adjust the decay rate and number of rounds based on how quickly valid designs emerge. If round 1 already produces many valid designs, fewer rounds are needed.

### Tool Selection

**ProteinMPNN** (default): Graph neural network for inverse folding.
- `model_type`: `"soluble"`
- `chains_to_design`: `"X"` (binder only; target fixed)
- `omit_AAs`: `"X"` (exclude non-standard)
- Confidence: native 0--1 range (higher = better)

**ESM-IF1** (alternative): Structure-conditioned language model.
- `mode`: `"sample"`, `multichain_backbone`: True
- Confidence normalization: `1 / (1 + exp(-(log_likelihood + 2.0) * 1.5))`

### Sequence Filtering

1. Over-generate candidates (e.g., 10x the desired count), then keep only the top sequences by confidence score.
2. Deduplicate -- skip any sequence already generated in the current or prior rounds.

> Full parameter tables: `references/parameters.md`

---

## Phase 4: Validation

**Purpose**: Multi-metric validation with early termination for failing designs.

### Validation Pipeline (ordered by cost)

```
Sequence --> Solubility --> Boltz-2 --> Metrics --> US-align --> DockQ --> Pass/Fail
```

#### Step 1: Solubility Screening

Fine-tuned ESM-2 classifier predicts E. coli expression solubility. Binary decision:
- **Soluble**: proceed to structure prediction
- **Insoluble**: **early termination** -- skip all remaining steps

#### Step 2: Structure Prediction (Boltz-2)

Predict binder-target complex structure from sequences.
- Binder chain X: single-sequence mode (no MSA)
- Target chains: MSAs auto-generated by Boltz-2

#### Step 3: Extract Confidence Metrics

From Boltz-2 output:
- **pLDDT**: Per-residue confidence averaged across full structure (0--100)
- **iPTM**: Interface predicted TM-score across chain interfaces (0--1)
- **ipSAE**: `avg(d0res_min, d0res_max)` for binder-target pairs only (0--1). Skipped if no interface detected.

#### Step 4: Structural Alignment (US-align)

Compare predicted binder (chain X) vs RFdiffusion backbone (chain X) in monomer mode.
- **Output**: TM-score (0--1) -- whether the sequence folds into the intended shape

#### Step 5: Interface Quality (DockQ)

Evaluate predicted complex vs RFdiffusion design. Binder-target pairs only (e.g., `[["X", "A"]]`).
- **Output**: DockQ score (0--1) plus iRMSD, LRMSD, fnat components

#### Step 6: Pass/Fail Decision

A binder passes only if **ALL** metrics meet their thresholds (AND logic). Check all metrics and report all failures, not just the first.

**Recommended thresholds (balanced)**:

| Metric | Threshold | Direction |
|---|---|---|
| pLDDT | >= 70.0 | Higher is better |
| iPTM | >= 0.65 | Higher is better |
| ipSAE | >= 0.5 | Higher is better |
| TM-score | >= 0.5 | Higher is better |
| DockQ | >= 0.23 | Higher is better |

Adjust thresholds based on campaign goals -- use lenient thresholds for difficult targets to avoid rejecting everything, or strict thresholds when high confidence is required.

> Lenient and strict threshold variants: `references/parameters.md`
> Detailed metric definitions and interpretation: `references/validation-metrics.md` -- load when interpreting results or adjusting thresholds.

---

## Phase 5: Round Advancement

**Purpose**: After validating all designs in a round, decide whether to continue or finalize.

### Decision Guidelines

After each validation round, decide the next action:

1. **Finalize** -- If enough valid designs have been found (target met), or if the user is satisfied with results so far.
2. **Advance sequence round** -- If the current backbone produced some promising results, try new sequences at a lower temperature to refine around successful folds. Same backbone, narrower sampling.
3. **Advance backbone** -- If the current backbone's sequence rounds are exhausted or producing diminishing returns, move to the next backbone and reset the temperature schedule.
4. **Finalize with partial results** -- If all backbones and rounds are exhausted, report whatever valid designs were found.

Use the valid design rate and per-metric failure patterns to guide the decision. If most failures are on the same metric (e.g., DockQ), the issue is likely the backbone geometry rather than sequence design -- advancing to a new backbone is more productive than more sequence rounds.

### Reporting

- **Round report**: After each round -- iterations tested, valid found, failures by metric, temperature used, duplicates skipped.
- **Final report**: At completion -- comprehensive summary of entire design campaign.

---

## Reference Files

| File | Contents | Load when... |
|---|---|---|
| `references/parameters.md` | All parameter tables by phase: epitope scoring, backbone generation, sequence design, validation thresholds (lenient/balanced/strict), Boltz-2 config, iteration limits | Adjusting parameters or troubleshooting thresholds |
| `references/validation-metrics.md` | Metric definitions: pLDDT, iPTM, ipSAE, TM-score, DockQ, Solubility -- range, source, interpretation, pipeline usage | Interpreting validation results or explaining metrics |
| `references/design-tips.md` | Practical guidance: hotspot selection heuristics, target truncation for large proteins, design scale recommendations, common failure modes | Planning a design campaign or troubleshooting poor results |
