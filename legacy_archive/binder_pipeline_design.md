# RBX-1 Binder Design Pipeline

## Overview
Multi-stage computational pipeline to generate 100 high-quality, diverse protein binders against RBX-1 for the GEM-Adaptyv competition.

## Pipeline Architecture

### Stage 1: Target Preparation and Analysis
**Goal**: Prepare RBX-1 structures and identify optimal binding sites

#### 1.1 Structure Preparation
```bash
# Clean and prepare PDB structures
amina run pdb-cleaner --pdb 1LDJ.cif --output cleaned/1LDJ_clean.pdb
amina run pdb-cleaner --pdb 1U6G.cif --output cleaned/1U6G_clean.pdb
amina run pdb-cleaner --pdb 2HYE.cif --output cleaned/2HYE_clean.pdb
amina run pdb-cleaner --pdb 2LGV.cif --output cleaned/2LGV_clean.pdb
amina run pdb-cleaner --pdb 4F52.cif --output cleaned/4F52_clean.pdb
```

#### 1.2 Binding Site Identification
```bash
# Identify potential binding pockets
amina run p2rank --pdb cleaned/1LDJ_clean.pdb --output analysis/p2rank_1LDJ/
amina run p2rank --pdb cleaned/1U6G_clean.pdb --output analysis/p2rank_1U6G/

# Predict binding interfaces for different binding modes
amina run pesto --pdb cleaned/1LDJ_clean.pdb --output analysis/pesto_1LDJ/
```

#### 1.3 Interface Analysis
```bash
# Extract RBX-1 chain from complexes for binder design
amina run pdb-chain-select --pdb cleaned/1LDJ_clean.pdb --chains B --output targets/rbx1_1LDJ.pdb

# Identify existing interfaces in complexes
amina run interface-identifier --pdb cleaned/1LDJ_clean.pdb --output analysis/interfaces_1LDJ/
```

### Stage 2: Backbone Generation
**Goal**: Generate diverse protein backbones targeting multiple epitopes on RBX-1

#### 2.1 RFdiffusion Binder Design
```bash
# Target the structured RING domain (multiple hotspots)
amina run rfdiffusion \
    --mode binder-design \
    --target targets/rbx1_1LDJ.pdb \
    --hotspots "A45,A47,A50,A55,A60" \
    --length 60-120 \
    --num_designs 50 \
    --output designs/rfdiff_ring_domain/ \
    --background

# Target alternative binding sites
amina run rfdiffusion \
    --mode binder-design \
    --target targets/rbx1_1LDJ.pdb \
    --hotspots "A70,A72,A75,A80,A85" \
    --length 40-80 \
    --num_designs 30 \
    --output designs/rfdiff_alt_site/ \
    --background

# Target potential allosteric sites
amina run rfdiffusion \
    --mode binder-design \
    --target targets/rbx1_1LDJ.pdb \
    --hotspots "A30,A35,A38,A42" \
    --length 50-100 \
    --num_designs 30 \
    --output designs/rfdiff_allosteric/ \
    --background
```

#### 2.2 Multiple Target Conformations
```bash
# Use different PDB conformations to capture flexibility
amina run rfdiffusion \
    --mode binder-design \
    --target targets/rbx1_2HYE.pdb \
    --hotspots "A45,A47,A50" \
    --length 60-100 \
    --num_designs 25 \
    --output designs/rfdiff_conf2/ \
    --background
```

### Stage 3: Sequence Design
**Goal**: Generate optimized sequences for the designed backbones

#### 3.1 ProteinMPNN Sequence Design
```bash
# Design sequences for all generated backbones
amina run proteinmpnn \
    --pdb designs/rfdiff_ring_domain/ \
    --num_seqs_per_target 5 \
    --sampling_temp 0.1 \
    --output sequences/mpnn_ring/ \
    --background

amina run proteinmpnn \
    --pdb designs/rfdiff_alt_site/ \
    --num_seqs_per_target 5 \
    --sampling_temp 0.1 \
    --output sequences/mpnn_alt/ \
    --background
```

#### 3.2 ESM-IF1 Alternative Design
```bash
# Alternative sequence design method
amina run esm-if1 \
    --pdb designs/rfdiff_ring_domain/ \
    --num_seqs_per_target 3 \
    --output sequences/esmif1_ring/ \
    --background
```

### Stage 4: Structure Prediction and Validation
**Goal**: Predict 3D structures and assess quality

#### 4.1 Structure Prediction
```bash
# Fast prediction with ESMFold
amina run esmfold \
    --fasta sequences/mpnn_ring/sequences.fasta \
    --output predicted/esmfold_ring/ \
    --background

# High-quality prediction with Boltz-2 for top candidates
amina run boltz2 \
    --fasta top_candidates.fasta \
    --output predicted/boltz2_top/ \
    --background
```

#### 4.2 Complex Prediction
```bash
# Predict binder-target complexes
amina run boltz2 \
    --fasta complex_sequences.fasta \
    --output predicted/complexes/ \
    --background
```

### Stage 5: Quality Assessment and Filtering
**Goal**: Filter and rank candidates based on multiple criteria

#### 5.1 Structural Quality Assessment
```bash
# Assess predicted structure quality
amina run pdb-quality-assessment \
    --pdb predicted/esmfold_ring/ \
    --output quality/esmfold_quality/

# Calculate RMSD to designed backbone
amina run rmsd-analysis \
    --reference designs/rfdiff_ring_domain/ \
    --mobile predicted/esmfold_ring/ \
    --output quality/rmsd_analysis/
```

#### 5.2 Binding Assessment
```bash
# Assess binding interfaces
amina run dockq \
    --pdb predicted/complexes/ \
    --output binding/dockq_scores/

# Verify designed interfaces
amina run interface-identifier \
    --pdb predicted/complexes/ \
    --output binding/interface_analysis/
```

#### 5.3 Physicochemical Properties
```bash
# Predict solubility
amina run aminosol \
    --fasta sequences/all_candidates.fasta \
    --output properties/solubility/

# Analyze surface properties
amina run surface-charge \
    --pdb predicted/esmfold_ring/ \
    --output properties/electrostatics/

# Calculate hydrophobicity
amina run hydrophobicity \
    --pdb predicted/esmfold_ring/ \
    --output properties/hydrophobicity/
```

### Stage 6: Diversity and Novelty Analysis
**Goal**: Ensure sequence diversity and novelty requirements

#### 6.1 Clustering for Diversity
```bash
# Cluster sequences to ensure diversity
amina run mmseqs2-cluster \
    --fasta sequences/all_candidates.fasta \
    --identity 0.7 \
    --output clustering/diversity_analysis/
```

#### 6.2 Novelty Verification
```bash
# This step requires external database searches against UniRef50
# Will be implemented separately
```

### Stage 7: Final Ranking and Selection
**Goal**: Select top 100 binders using composite scoring

#### 7.1 Composite Scoring
- **Structure Quality (25%)**: pLDDT scores, Ramachandran, geometry
- **Binding Prediction (30%)**: DockQ scores, interface metrics
- **Druggability (20%)**: Solubility, surface properties, size
- **Diversity (15%)**: Sequence/structure diversity from cluster analysis
- **Novelty (10%)**: Distance from known proteins

#### 7.2 Final Selection Strategy
1. **Tier 1 (40 binders)**: High-confidence RING domain binders
2. **Tier 2 (30 binders)**: Alternative binding site binders
3. **Tier 3 (20 binders)**: Allosteric/novel site binders
4. **Tier 4 (10 binders)**: Experimental/diverse conformations

## Pipeline Parameters

### Quality Thresholds
- **pLDDT**: >70 average, >80 for binding interface
- **DockQ**: >0.23 (acceptable), >0.49 (medium), >0.80 (high)
- **Length**: 40-120 residues (competition limit: ≤250)
- **Solubility**: >0.5 probability (E. coli expression)

### Diversity Requirements
- **Sequence identity**: <70% within final set
- **Structural diversity**: Multiple epitopes covered
- **Size diversity**: Range of 40-120 residues
- **Chemical diversity**: Different surface properties

### Computational Resources
- **Total designs**: ~150-200 initial backbones
- **Sequences per backbone**: 3-5 sequences
- **Total sequences**: ~500-800 candidates
- **Final selection**: Top 100 binders

## Timeline Estimate
- **Stage 1-2**: 2 days (structure prep + backbone generation)
- **Stage 3**: 1 day (sequence design)
- **Stage 4**: 2 days (structure prediction)
- **Stage 5-6**: 2 days (analysis and filtering)
- **Stage 7**: 1 day (final ranking and selection)
- **Total**: ~8-10 days including analysis and refinement

## Output Files
- `final_binders.csv`: Top 100 ranked sequences
- `method_description.pdf`: 2-page method description
- `structures/`: Optional predicted structure files
- `analysis/`: Comprehensive analysis results