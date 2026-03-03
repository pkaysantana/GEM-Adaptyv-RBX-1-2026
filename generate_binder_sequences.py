#!/usr/bin/env python3
"""
Generate RBX-1 binder sequences for competition submission
"""

import random
import itertools
from typing import List, Tuple

def generate_rbx1_binder_sequences(num_sequences: int = 100) -> List[Tuple[str, str]]:
    """Generate diverse binder sequences targeting RBX-1 RING domain"""

    # Known structural motifs for RING domain binding
    ring_binding_motifs = [
        "CXXCX{10,30}CXXC",  # Zinc finger motif
        "HXXXH",              # Histidine chelation
        "DXXE",               # Acidic patch
        "KXXR",               # Basic patch
    ]

    # Scaffolds based on successful binder designs
    scaffold_templates = [
        # Small β-sheet scaffolds (40-60 AA)
        "MGXXXXXWXXXXXGXXXXXPXXXXXFXXXXXLXXXXXQXXXXXEVXXXXXT",
        # Helical scaffolds (50-70 AA)
        "MXXEXXXAXXXKXXXLXXXDXXXQXXXRXXXEXXXAXXXLXXXKXXXDXXXQXXXR",
        # Mixed α/β scaffolds (60-80 AA)
        "MGXXXXXWXXXXXGXXXXXPXXXXXFXXXXXLXXXXXQXXXXXEVXXXXXTYXXXXXGXXXXXS",
        # Loop-rich scaffolds (70-90 AA)
        "MXXEXXXAXXXKXXXLXXXDXXXQXXXRXXXEXXXAXXXLXXXKXXXDXXXQXXXRXXXEXXXAX",
    ]

    # Amino acid preferences for binding interfaces
    binding_residues = ['W', 'F', 'Y', 'R', 'K', 'D', 'E', 'H', 'N', 'Q', 'S', 'T']
    hydrophobic_core = ['L', 'I', 'V', 'A', 'F', 'W', 'Y', 'M']
    flexible_linkers = ['G', 'S', 'T', 'N', 'Q']

    sequences = []

    for i in range(num_sequences):
        # Select scaffold length and type
        length = random.randint(40, 90)
        scaffold_type = random.choice(['beta_sheet', 'helical', 'mixed', 'loop_rich'])

        # Generate sequence based on scaffold type
        sequence = generate_sequence_by_scaffold(
            length, scaffold_type, binding_residues, hydrophobic_core, flexible_linkers
        )

        # Add binding motif
        if random.random() < 0.3:  # 30% chance to include explicit binding motif
            sequence = insert_binding_motif(sequence, binding_residues)

        # Ensure good properties
        sequence = optimize_sequence_properties(sequence)

        # Create name
        name = f"RBX1_Binder_{i+1:03d}_{scaffold_type}"

        sequences.append((name, sequence))

    return sequences

def generate_sequence_by_scaffold(length: int, scaffold_type: str, binding_res: List[str],
                                 hydrophobic: List[str], flexible: List[str]) -> str:
    """Generate sequence based on scaffold type"""

    # Start with methionine
    sequence = ['M']
    remaining_length = length - 1

    if scaffold_type == 'beta_sheet':
        # Alternating hydrophobic/hydrophilic pattern
        for i in range(remaining_length):
            if i % 4 in [0, 2]:  # Hydrophobic positions
                sequence.append(random.choice(hydrophobic))
            elif i % 8 == 1:     # Potential binding positions
                sequence.append(random.choice(binding_res))
            else:                # Flexible positions
                sequence.append(random.choice(flexible + ['A', 'V', 'L']))

    elif scaffold_type == 'helical':
        # Helical wheel pattern (i, i+3, i+4, i+7 hydrophobic)
        for i in range(remaining_length):
            pos = i % 7
            if pos in [0, 3, 4]:        # Hydrophobic face
                sequence.append(random.choice(hydrophobic))
            elif pos in [1, 5]:         # Binding positions
                sequence.append(random.choice(binding_res))
            else:                       # Solvent exposed
                sequence.append(random.choice(['K', 'R', 'E', 'D', 'Q', 'N', 'S', 'T']))

    elif scaffold_type == 'mixed':
        # Mix of secondary structures
        ss_pattern = ['H'] * 15 + ['L'] * 8 + ['E'] * 12 + ['L'] * 5 + ['H'] * (remaining_length - 40)
        random.shuffle(ss_pattern)

        for ss_type in ss_pattern[:remaining_length]:
            if ss_type == 'H':    # Helix
                sequence.append(random.choice(['A', 'E', 'K', 'L', 'R']))
            elif ss_type == 'E':  # Sheet
                sequence.append(random.choice(['V', 'I', 'F', 'Y', 'W']))
            else:                 # Loop
                sequence.append(random.choice(binding_res + flexible))

    else:  # loop_rich
        # Random with bias toward binding and flexible residues
        for i in range(remaining_length):
            if random.random() < 0.4:
                sequence.append(random.choice(binding_res))
            elif random.random() < 0.3:
                sequence.append(random.choice(flexible))
            else:
                sequence.append(random.choice(hydrophobic))

    return ''.join(sequence)

def insert_binding_motif(sequence: str, binding_res: List[str]) -> str:
    """Insert known binding motifs into sequence"""

    motifs = [
        'WGF',    # Aromatic stacking
        'RKD',    # Charged triad
        'HSH',    # His coordination
        'DXE',    # Acidic patch
        'FWYF',   # Hydrophobic patch
    ]

    motif = random.choice(motifs)

    # Find good insertion position (avoid N/C termini)
    if len(sequence) > 20:
        pos = random.randint(5, len(sequence) - len(motif) - 5)
        sequence = sequence[:pos] + motif + sequence[pos + len(motif):]

    return sequence

def optimize_sequence_properties(sequence: str) -> str:
    """Optimize sequence for good biophysical properties"""

    seq_list = list(sequence)

    # Avoid long runs of same amino acid
    for i in range(len(seq_list) - 3):
        if seq_list[i] == seq_list[i+1] == seq_list[i+2] == seq_list[i+3]:
            # Break up the run
            seq_list[i+2] = random.choice(['A', 'S', 'T', 'G'])

    # Ensure not too many prolines (can be problematic)
    pro_count = seq_list.count('P')
    if pro_count > len(seq_list) // 10:  # Max 10% prolines
        # Replace some prolines
        while seq_list.count('P') > len(seq_list) // 10:
            pro_indices = [i for i, aa in enumerate(seq_list) if aa == 'P']
            idx = random.choice(pro_indices)
            seq_list[idx] = random.choice(['A', 'S', 'G', 'T'])

    # Ensure good charge distribution
    sequence = ''.join(seq_list)
    charge = sequence.count('K') + sequence.count('R') - sequence.count('D') - sequence.count('E')

    # Target slightly positive charge for binding
    if charge < -2:  # Too negative
        # Add some positive residues
        for i in range(abs(charge + 2)):
            pos = random.randint(1, len(seq_list) - 2)
            if seq_list[pos] in ['A', 'S', 'T', 'G']:
                seq_list[pos] = random.choice(['K', 'R'])

    return ''.join(seq_list)

def calculate_sequence_properties(sequence: str) -> dict:
    """Calculate basic sequence properties"""

    properties = {
        'length': len(sequence),
        'charge': sequence.count('K') + sequence.count('R') - sequence.count('D') - sequence.count('E'),
        'hydrophobic_fraction': sum(sequence.count(aa) for aa in 'AILMFWYV') / len(sequence),
        'aromatic_count': sum(sequence.count(aa) for aa in 'FWY'),
        'positive_count': sum(sequence.count(aa) for aa in 'KR'),
        'negative_count': sum(sequence.count(aa) for aa in 'DE'),
    }

    return properties

if __name__ == "__main__":
    # Generate 100 diverse RBX-1 binder sequences
    print("Generating RBX-1 binder sequences...")

    sequences = generate_rbx1_binder_sequences(100)

    # Write to FASTA format for submission
    with open('rbx1_binder_submission.fasta', 'w') as f:
        for name, seq in sequences:
            f.write(f">{name}\n{seq}\n")

    # Write to CSV format for submission
    with open('rbx1_binder_submission.csv', 'w') as f:
        f.write("Name,Sequence\n")
        for name, seq in sequences:
            f.write(f"{name},{seq}\n")

    # Calculate properties
    print(f"\nGenerated {len(sequences)} sequences:")
    lengths = [len(seq) for _, seq in sequences]
    print(f"Length range: {min(lengths)}-{max(lengths)} AA (avg: {sum(lengths)/len(lengths):.1f})")

    # Check a few examples
    print(f"\nFirst 5 sequences:")
    for i in range(5):
        name, seq = sequences[i]
        props = calculate_sequence_properties(seq)
        print(f"{name}: {seq[:20]}... (L={props['length']}, charge={props['charge']})")

    print(f"\nFiles created:")
    print(f"- rbx1_binder_submission.fasta")
    print(f"- rbx1_binder_submission.csv")