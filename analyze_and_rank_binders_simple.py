#!/usr/bin/env python3
"""
Analyze and rank RBX-1 binder sequences for optimal competition submission
Simple version without numpy/pandas dependencies
"""

import csv
import glob
import math
import os
import re
from typing import List, Dict, Tuple

# Output files produced by this script — never treated as sources
_OUTPUT_FILES = {
    'final_rbx1_submission.csv',
    'final_rbx1_submission_competition.csv',
}

def load_sequences(csv_file: str = None) -> List[Tuple[str, str]]:
    """Load and deduplicate sequences from all rbx1_*.csv source files."""
    if csv_file:
        # Legacy single-file path (kept for compatibility)
        source_files = [csv_file]
    else:
        source_files = [
            f for f in glob.glob('rbx1_*.csv')
            if os.path.basename(f) not in _OUTPUT_FILES
        ]
        source_files.sort()

    seen_seqs = {}   # sequence -> (name, source_file) — dedup by sequence
    for path in source_files:
        with open(path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                seq = row['Sequence'].strip()
                name = row['Name'].strip()
                if seq and seq not in seen_seqs:
                    seen_seqs[seq] = (name, path)

    sequences = [(name, seq) for seq, (name, _) in seen_seqs.items()]

    if not csv_file:
        print(f"Sources loaded: {source_files}")
        print(f"  Total unique sequences: {len(sequences)}")

    return sequences

def calculate_binding_score(sequence: str) -> float:
    """Calculate predicted binding potential based on sequence features"""

    # Aromatic content (important for protein-protein interactions)
    aromatic_count = sum(sequence.count(aa) for aa in 'FWY')
    aromatic_fraction = aromatic_count / len(sequence)

    # Hydrophobic content (important for binding interfaces)
    hydrophobic_count = sum(sequence.count(aa) for aa in 'AILMFWYV')
    hydrophobic_fraction = hydrophobic_count / len(sequence)

    # Charged residues (can form salt bridges)
    positive_count = sum(sequence.count(aa) for aa in 'KR')
    negative_count = sum(sequence.count(aa) for aa in 'DE')
    charge_balance = min(positive_count, negative_count) / len(sequence)

    # Binding motifs (simple pattern matching)
    motif_score = 0
    binding_motifs = ['WGF', 'RKD', 'HSH', 'FWY', 'HH', 'WW']
    for motif in binding_motifs:
        if motif in sequence:
            motif_score += 1

    # Special patterns for RING domain binding
    if 'WF' in sequence or 'FW' in sequence:
        motif_score += 0.5
    if 'RK' in sequence or 'KR' in sequence:
        motif_score += 0.5

    # Combine scores
    binding_score = (
        aromatic_fraction * 2.0 +          # Weight: 2.0
        hydrophobic_fraction * 1.5 +       # Weight: 1.5
        charge_balance * 1.0 +              # Weight: 1.0
        motif_score * 0.3                   # Weight: 0.3
    )

    return min(binding_score, 3.0)  # Cap at 3.0

def calculate_druggability_score(sequence: str) -> float:
    """Calculate predicted druggability (solubility, aggregation resistance)"""

    length = len(sequence)

    # Length penalty (very long or very short proteins are problematic)
    if 50 <= length <= 80:
        length_score = 1.0
    elif 40 <= length < 50 or 80 < length <= 90:
        length_score = 0.9
    else:
        length_score = 0.7

    # Charge score (moderate positive charge is good for solubility)
    net_charge = sum(sequence.count(aa) for aa in 'KR') - sum(sequence.count(aa) for aa in 'DE')
    if -2 <= net_charge <= 4:
        charge_score = 1.0
    elif -4 <= net_charge <= 6:
        charge_score = 0.8
    else:
        charge_score = 0.6

    # Aggregation resistance (avoid too many hydrophobic residues in a row)
    aggregation_score = 1.0
    hydrophobic_pattern = re.findall(r'[AILMFWYV]{4,}', sequence)
    if hydrophobic_pattern:
        aggregation_score = max(0.5, 1.0 - len(hydrophobic_pattern) * 0.2)

    # Avoid problematic sequences
    problematic_score = 1.0
    if 'PPP' in sequence:  # Too many prolines
        problematic_score *= 0.8
    if sequence.count('C') > 4:  # Too many cysteines
        problematic_score *= 0.9
    if sequence.count('M') > 3:  # Too many methionines
        problematic_score *= 0.95

    druggability_score = length_score * charge_score * aggregation_score * problematic_score

    return druggability_score

def calculate_structural_score(sequence: str) -> float:
    """Calculate predicted structural quality"""

    length = len(sequence)

    # Secondary structure content prediction (very basic)
    helix_formers = sum(sequence.count(aa) for aa in 'AEDKRL')
    sheet_formers = sum(sequence.count(aa) for aa in 'VIFYWTM')
    loop_formers = sum(sequence.count(aa) for aa in 'GNPSTQ')

    helix_fraction = helix_formers / length
    sheet_fraction = sheet_formers / length
    loop_fraction = loop_formers / length

    # Balance of secondary structures (not too much of any one type)
    max_fraction = max(helix_fraction, sheet_fraction, loop_fraction)
    ss_balance = 1.0 - abs(max_fraction - 0.4)  # Target around 40% for dominant structure

    # Avoid glycine-rich regions (can be too flexible)
    glycine_content = sequence.count('G') / length
    if glycine_content > 0.15:
        flexibility_penalty = 0.8
    else:
        flexibility_penalty = 1.0

    # Proline content (moderate amounts are good for structure)
    proline_content = sequence.count('P') / length
    if 0.02 <= proline_content <= 0.12:
        proline_score = 1.0
    else:
        proline_score = 0.8

    structural_score = ss_balance * flexibility_penalty * proline_score

    return max(0.1, structural_score)  # Minimum score of 0.1

def calculate_diversity_score(sequence: str, scaffold_type: str) -> float:
    """Calculate diversity based on scaffold type and composition"""

    # Scaffold diversity
    scaffold_bonus = {
        'loop_rich': 1.0,
        'helical': 0.9,
        'beta_sheet': 0.8,
        'mixed': 1.1
    }

    # Extract scaffold type from name
    if 'loop_rich' in scaffold_type:
        type_score = scaffold_bonus['loop_rich']
    elif 'helical' in scaffold_type:
        type_score = scaffold_bonus['helical']
    elif 'beta_sheet' in scaffold_type:
        type_score = scaffold_bonus['beta_sheet']
    elif 'mixed' in scaffold_type:
        type_score = scaffold_bonus['mixed']
    else:
        type_score = 0.9

    # Amino acid diversity (number of different amino acids used)
    aa_counts = [sequence.count(aa) for aa in 'ACDEFGHIKLMNPQRSTVWY']
    unique_aas = len([c for c in aa_counts if c > 0])
    aa_diversity = min(1.0, unique_aas / 15)  # Target 15+ different amino acids

    # Length diversity (prefer variety in lengths)
    length = len(sequence)
    if 55 <= length <= 75:  # Mid-range
        length_score = 1.0
    elif length < 55 or length > 75:  # Extremes add diversity
        length_score = 1.1
    else:
        length_score = 0.9

    diversity_score = type_score * aa_diversity * length_score

    return min(diversity_score, 1.5)

def calculate_novelty_score(sequence: str) -> float:
    """Calculate novelty score (avoiding similarity to known proteins)"""

    # Avoid common protein domain signatures
    common_signatures = [
        'DEADH',     # DEAD-box helicase
        'HRCHL',     # HERC domain
        'CPXCG',     # RING domain (avoid too much similarity to target)
        'WDXL',      # WD40 repeat
        'EFHAND'     # EF-hand motif
    ]

    novelty_penalty = 0
    for sig in common_signatures:
        # Simple substring check
        if any(sig[:3] in sequence and sig[-2:] in sequence for sig in common_signatures):
            novelty_penalty += 0.1

    # Prefer sequences with unusual amino acid patterns
    aa_counts = [sequence.count(aa) for aa in 'ACDEFGHIKLMNPQRSTVWY']

    # Avoid sequences dominated by common amino acids
    common_aa_fraction = sum(sequence.count(aa) for aa in 'ALES') / len(sequence)
    if common_aa_fraction > 0.4:
        novelty_penalty += 0.1

    # Bonus for having rare amino acids in good proportions
    rare_aa_count = sum(sequence.count(aa) for aa in 'CMWY')
    if 0.05 <= rare_aa_count / len(sequence) <= 0.15:
        rare_bonus = 0.1
    else:
        rare_bonus = 0

    novelty_score = max(0.6, 1.0 - novelty_penalty + rare_bonus)

    return novelty_score

def rank_sequences(sequences: List[Tuple[str, str]]) -> List[Tuple[str, str, float, Dict]]:
    """Rank sequences based on composite scoring"""

    ranked_sequences = []

    for name, sequence in sequences:
        # Calculate individual scores
        binding_score = calculate_binding_score(sequence)
        druggability_score = calculate_druggability_score(sequence)
        structural_score = calculate_structural_score(sequence)
        diversity_score = calculate_diversity_score(sequence, name)
        novelty_score = calculate_novelty_score(sequence)

        # Composite score (weighted combination)
        weights = {
            'binding': 0.35,
            'druggability': 0.25,
            'structural': 0.20,
            'diversity': 0.15,
            'novelty': 0.05
        }

        composite_score = (
            binding_score * weights['binding'] +
            druggability_score * weights['druggability'] +
            structural_score * weights['structural'] +
            diversity_score * weights['diversity'] +
            novelty_score * weights['novelty']
        )

        scores_dict = {
            'binding': binding_score,
            'druggability': druggability_score,
            'structural': structural_score,
            'diversity': diversity_score,
            'novelty': novelty_score,
            'composite': composite_score
        }

        ranked_sequences.append((name, sequence, composite_score, scores_dict))

    # Sort by composite score (descending)
    ranked_sequences.sort(key=lambda x: x[2], reverse=True)

    return ranked_sequences

def optimize_final_selection(ranked_sequences: List, target_count: int = 100) -> List:
    """Select top sequences purely by composite score — no diversity caps."""
    return ranked_sequences[:target_count]

def create_submission_files(final_sequences: List, prefix: str = "final_rbx1_submission"):
    """Create final submission files"""

    # CSV format for analysis
    csv_filename = f"{prefix}.csv"
    with open(csv_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Rank', 'Name', 'Sequence', 'Length', 'Composite_Score',
                        'Binding_Score', 'Druggability_Score', 'Structural_Score'])

        for rank, (name, sequence, composite_score, scores) in enumerate(final_sequences, 1):
            writer.writerow([
                rank, name, sequence, len(sequence), f"{composite_score:.3f}",
                f"{scores['binding']:.3f}", f"{scores['druggability']:.3f}",
                f"{scores['structural']:.3f}"
            ])

    # Competition submission CSV (simple format)
    submission_csv = f"{prefix}_competition.csv"
    with open(submission_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Name', 'Sequence'])
        for rank, (name, sequence, _, _) in enumerate(final_sequences, 1):
            comp_name = f"RBX1_Binder_R{rank:03d}"
            writer.writerow([comp_name, sequence])

    # FASTA format
    fasta_filename = f"{prefix}.fasta"
    with open(fasta_filename, 'w') as f:
        for rank, (name, sequence, composite_score, scores) in enumerate(final_sequences, 1):
            comp_name = f"RBX1_Binder_R{rank:03d}"
            f.write(f">{comp_name} Score={composite_score:.3f}\n{sequence}\n")

    return csv_filename, submission_csv, fasta_filename

if __name__ == "__main__":
    print("Analyzing and ranking RBX-1 binder sequences...")

    # Load and merge all rbx1_*.csv source files
    sequences = load_sequences()
    print(f"Loaded {len(sequences)} sequences")

    # Rank sequences
    print("Calculating scores and ranking...")
    ranked_sequences = rank_sequences(sequences)

    # Optimize final selection
    print("Optimizing final selection for diversity...")
    final_selection = optimize_final_selection(ranked_sequences, target_count=100)

    # Create submission files
    print("Creating final submission files...")
    analysis_csv, submission_csv, fasta_file = create_submission_files(final_selection)

    # Print summary
    print(f"\n=== FINAL SELECTION SUMMARY ===")
    print(f"Selected {len(final_selection)} sequences")
    print(f"Analysis file: {analysis_csv}")
    print(f"Competition submission: {submission_csv}")
    print(f"FASTA file: {fasta_file}")

    # Top 10 summary
    print(f"\nTop 10 sequences:")
    for i, (name, sequence, score, scores) in enumerate(final_selection[:10], 1):
        length = len(sequence)
        print(f"{i:2d}. {name[:25]:25s} L={length:2d} Score={score:.3f} "
              f"(B:{scores['binding']:.2f} D:{scores['druggability']:.2f} S:{scores['structural']:.2f})")

    # Length distribution
    lengths = [len(seq) for _, seq, _, _ in final_selection]
    print(f"\nLength statistics:")
    print(f"  Range: {min(lengths)}-{max(lengths)} AA")
    print(f"  Mean: {sum(lengths)/len(lengths):.1f} AA")

    # Score distribution
    composite_scores = [score for _, _, score, _ in final_selection]
    print(f"\nScore statistics:")
    print(f"  Mean: {sum(composite_scores)/len(composite_scores):.3f}")
    print(f"  Range: {min(composite_scores):.3f} - {max(composite_scores):.3f}")

    # Scaffold distribution
    scaffold_counts = {'loop_rich': 0, 'helical': 0, 'beta_sheet': 0, 'mixed': 0}
    for name, _, _, _ in final_selection:
        if 'loop_rich' in name:
            scaffold_counts['loop_rich'] += 1
        elif 'helical' in name:
            scaffold_counts['helical'] += 1
        elif 'beta_sheet' in name:
            scaffold_counts['beta_sheet'] += 1
        elif 'mixed' in name:
            scaffold_counts['mixed'] += 1

    print(f"\nScaffold distribution:")
    for scaffold, count in scaffold_counts.items():
        print(f"  {scaffold}: {count}")

    print(f"\n[READY] Competition submission prepared!")
    print(f"\n[NEXT] Upload {submission_csv} to the competition portal")