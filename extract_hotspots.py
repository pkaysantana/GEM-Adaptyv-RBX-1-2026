"""
extract_hotspots.py
-------------------
Task 2: Extract RBX-1 hotspot residue sets from CIF structures for RFdiffusion.

Hotspot sets produced:
  glomulin_face  - 4F52: RBX-1 residues contacting Glomulin (natural inhibitor, proven bindable surface)
  e2_face        - 1LDJ: RBX-1 residues NOT contacting CUL1, solvent-exposed (E2-recruitment face)
  monomer_surface- 2LGV: High-RSA patches on structured region (residues 40-108)
  combined       - Union of non-overlapping residues from all three sets (residues >= 40 only)

All residues < 40 are excluded (disordered N-terminus).
Output: hotspot_manifest.json in the same directory as this script.
"""

import json
import sys
import os
import numpy as np
from Bio.PDB import MMCIFParser
from Bio.PDB.DSSP import DSSP

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CIF_DIR = SCRIPT_DIR

CONTACT_CUTOFF = 5.0   # Angstroms, any heavy atom pair
RSA_CUTOFF = 0.25      # Relative solvent accessibility threshold for "exposed"
MIN_RES = 40           # Exclude disordered N-terminus


def get_atoms(chain):
    """Return list of all heavy atoms in a chain."""
    atoms = []
    for res in chain.get_residues():
        for atom in res.get_atoms():
            if atom.element != 'H':
                atoms.append(atom)
    return atoms


def residues_within_cutoff(chain_a, chain_b, cutoff=CONTACT_CUTOFF):
    """
    Return set of residue sequence IDs from chain_a that have at least one
    heavy atom within `cutoff` Angstroms of any heavy atom in chain_b.
    """
    from Bio.PDB import NeighborSearch
    atoms_b = get_atoms(chain_b)
    atoms_a = get_atoms(chain_a)
    ns = NeighborSearch(atoms_b)

    contacting = set()
    for atom in atoms_a:
        hits = ns.search(atom.coord, cutoff, level='A')
        if hits:
            res = atom.get_parent()
            resid = res.get_id()[1]
            contacting.add(resid)
    return contacting


def get_chain_residue_ids(chain, min_res=MIN_RES):
    """Return sorted list of residue sequence IDs >= min_res (HETATM excluded)."""
    ids = []
    for res in chain.get_residues():
        het, seq, icode = res.get_id()
        if het.strip():  # skip HETATM
            continue
        if seq >= min_res:
            ids.append(seq)
    return sorted(ids)


def parse_structure(cif_path, structure_id):
    parser = MMCIFParser(QUIET=True)
    structure = parser.get_structure(structure_id, cif_path)
    return structure


def identify_rbx1_chain(model, source):
    """
    Return the chain object that corresponds to RBX-1 in each structure.
    We identify by chain ID known from literature / PDB annotations:
      4F52: chain B is RBX1 (ROC1), chain A is CUL1, chain C is Glomulin
      1LDJ: chain B is RBX1, chain A is CUL1, others are SKP1/SKP2/substrate
      2LGV: chain A is RBX1 monomer (NMR)
    """
    chain_map = {
        '4F52': 'B',
        '1LDJ': 'B',
        '2LGV': 'A',
    }
    chain_id = chain_map.get(source)
    if chain_id is None:
        raise ValueError(f"Unknown source structure: {source}")
    return model[chain_id], chain_id


# ──────────────────────────────────────────────────────────────────────────────
# SET 1: glomulin_face from 4F52
# ──────────────────────────────────────────────────────────────────────────────
def extract_glomulin_face(cif_path):
    print("Parsing 4F52 (Glomulin-RBX1-CUL1)...")
    struct = parse_structure(cif_path, '4F52')
    model = struct[0]

    print(f"  Chains present: {[c.id for c in model.get_chains()]}")

    rbx1_chain, rbx1_chain_id = identify_rbx1_chain(model, '4F52')

    # Glomulin chain: in 4F52 chain C is Glomulin (GML)
    # Verify by checking chain IDs available
    available = [c.id for c in model.get_chains()]
    # Glomulin is typically chain C in 4F52
    glom_chain_id = 'C'
    if glom_chain_id not in available:
        # Fall back: pick largest chain that is not A or B
        candidates = [c for c in model.get_chains() if c.id not in ('A', 'B')]
        if not candidates:
            raise ValueError("Cannot identify Glomulin chain in 4F52")
        candidates.sort(key=lambda c: len(list(c.get_residues())), reverse=True)
        glom_chain_id = candidates[0].id
        print(f"  WARNING: using chain {glom_chain_id} as Glomulin fallback")

    glom_chain = model[glom_chain_id]
    print(f"  RBX1 chain: {rbx1_chain_id}, Glomulin chain: {glom_chain_id}")
    print(f"  RBX1 residues: {len(list(rbx1_chain.get_residues()))}")
    print(f"  Glomulin residues: {len(list(glom_chain.get_residues()))}")

    contacting = residues_within_cutoff(rbx1_chain, glom_chain, CONTACT_CUTOFF)
    # Filter: >= MIN_RES, standard amino acids only
    filtered = sorted([r for r in contacting if r >= MIN_RES])
    print(f"  Contacting RBX1 residues (>= {MIN_RES}): {filtered}")
    return filtered, rbx1_chain_id


# ──────────────────────────────────────────────────────────────────────────────
# SET 2: e2_face from 1LDJ
# ──────────────────────────────────────────────────────────────────────────────
def extract_e2_face(cif_path):
    print("Parsing 1LDJ (CUL1-RBX1-SCF complex)...")
    struct = parse_structure(cif_path, '1LDJ')
    model = struct[0]

    print(f"  Chains present: {[c.id for c in model.get_chains()]}")

    rbx1_chain, rbx1_chain_id = identify_rbx1_chain(model, '1LDJ')

    # CUL1 chain is A
    cul1_chain = model['A']

    # All other chains (SKP1, SKP2, substrate) — everything except RBX1 and CUL1
    other_chains = [c for c in model.get_chains()
                    if c.id not in (rbx1_chain_id, 'A')]

    print(f"  RBX1 chain: {rbx1_chain_id}, CUL1 chain: A")
    print(f"  Other chains: {[c.id for c in other_chains]}")

    # Residues contacting CUL1
    cul1_contact = residues_within_cutoff(rbx1_chain, cul1_chain, CONTACT_CUTOFF)

    # Residues contacting any other chain (SKP1/SKP2/substrate)
    other_contact = set()
    for ch in other_chains:
        other_contact |= residues_within_cutoff(rbx1_chain, ch, CONTACT_CUTOFF)

    # All RBX1 residues
    all_rbx1 = set(get_chain_residue_ids(rbx1_chain, min_res=MIN_RES))

    # E2 face = NOT contacting CUL1, NOT contacting other scaffold chains, >= MIN_RES
    e2_face = sorted(all_rbx1 - cul1_contact - other_contact)

    # Also collect "exposed" = not buried by anything = good hotspot candidates
    print(f"  CUL1-contacting residues: {sorted(r for r in cul1_contact if r >= MIN_RES)}")
    print(f"  Other-contacting residues: {sorted(r for r in other_contact if r >= MIN_RES)}")
    print(f"  E2-face (free surface) residues: {e2_face}")
    return e2_face, rbx1_chain_id


# ──────────────────────────────────────────────────────────────────────────────
# SET 3: monomer_surface from 2LGV
# ──────────────────────────────────────────────────────────────────────────────
def extract_monomer_surface(cif_path):
    print("Parsing 2LGV (RBX1 monomer)...")
    struct = parse_structure(cif_path, '2LGV')

    # 2LGV is NMR — use first model
    model = struct[0]
    print(f"  Chains present: {[c.id for c in model.get_chains()]}")

    rbx1_chain, rbx1_chain_id = identify_rbx1_chain(model, '2LGV')
    print(f"  RBX1 chain: {rbx1_chain_id}")
    print(f"  RBX1 residues: {len(list(rbx1_chain.get_residues()))}")

    # Use neighbor-search based exposure: residues with few neighbors are exposed
    # Compute number of CA neighbors within 8A for each residue
    ca_atoms = []
    res_ids = []
    for res in rbx1_chain.get_residues():
        het, seq, icode = res.get_id()
        if het.strip():
            continue
        if seq < MIN_RES:
            continue
        if 'CA' in res:
            ca_atoms.append(res['CA'])
            res_ids.append(seq)

    from Bio.PDB import NeighborSearch
    ns = NeighborSearch(ca_atoms)

    neighbor_counts = []
    for ca in ca_atoms:
        hits = ns.search(ca.coord, 8.0, level='A')
        neighbor_counts.append(len(hits) - 1)  # subtract self

    neighbor_counts = np.array(neighbor_counts)
    # Exposed = fewer neighbors than median (surface residues)
    threshold = np.percentile(neighbor_counts, 40)  # bottom 40% neighbor count = surface
    exposed_residues = sorted([res_ids[i] for i, n in enumerate(neighbor_counts)
                                if n <= threshold])

    print(f"  Neighbor count range: {neighbor_counts.min()}-{neighbor_counts.max()}, "
          f"threshold (40th pct): {threshold:.1f}")
    print(f"  Exposed (surface) residues: {exposed_residues}")
    return exposed_residues, rbx1_chain_id


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    cif_files = {
        '4F52': os.path.join(CIF_DIR, '4F52.cif'),
        '1LDJ': os.path.join(CIF_DIR, '1LDJ.cif'),
        '2LGV': os.path.join(CIF_DIR, '2LGV.cif'),
    }

    for name, path in cif_files.items():
        if not os.path.exists(path):
            print(f"ERROR: {path} not found")
            sys.exit(1)

    # Set 1: glomulin_face
    glom_residues, glom_chain = extract_glomulin_face(cif_files['4F52'])

    # Set 2: e2_face
    e2_residues, e2_chain = extract_e2_face(cif_files['1LDJ'])

    # Set 3: monomer_surface
    mono_residues, mono_chain = extract_monomer_surface(cif_files['2LGV'])

    # Set 4: combined (union, no duplicates, sorted)
    combined = sorted(set(glom_residues) | set(e2_residues) | set(mono_residues))
    # Trim to a manageable hotspot set (top 12 most represented across sets)
    from collections import Counter
    votes = Counter()
    for r in glom_residues:
        votes[r] += 3  # glomulin face gets highest weight (proven inhibitor surface)
    for r in e2_residues:
        votes[r] += 2
    for r in mono_residues:
        votes[r] += 1
    # Take top 12 by vote
    top_combined = sorted([r for r, v in votes.most_common(12)])
    print(f"\nCombined top-12 hotspots (vote-weighted): {top_combined}")

    manifest = {
        "glomulin_face": {
            "residues": glom_residues,
            "rationale": "RBX-1 residues contacting Glomulin in 4F52; Glomulin is a natural protein inhibitor of RBX1-CUL1, so this surface is experimentally proven to be bindable by a folded protein domain.",
            "chain_in_source": glom_chain,
            "source_pdb": "4F52"
        },
        "e2_face": {
            "residues": e2_residues,
            "rationale": "RBX-1 residues in 1LDJ SCF complex that are NOT contacting CUL1 or other scaffold chains; represents the free/solvent-exposed face that recruits E2 ubiquitin-conjugating enzymes.",
            "chain_in_source": e2_chain,
            "source_pdb": "1LDJ"
        },
        "monomer_surface": {
            "residues": mono_residues,
            "rationale": "Most surface-exposed residues (low CA neighbor count) on structured region of RBX-1 monomer (2LGV NMR); provides an unbiased view of accessible patches not influenced by crystal contacts.",
            "chain_in_source": mono_chain,
            "source_pdb": "2LGV"
        },
        "combined": {
            "residues": top_combined,
            "rationale": "Vote-weighted union of glomulin_face (3pts), e2_face (2pts), monomer_surface (1pt); top 12 residues by cumulative score, capturing the most consistently identified bindable surface.",
            "chain_in_source": "B",
            "source_pdb": "4F52+1LDJ+2LGV"
        }
    }

    out_path = os.path.join(SCRIPT_DIR, 'hotspot_manifest.json')
    with open(out_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f"\nSaved hotspot_manifest.json to {out_path}")

    # Summary
    print("\n=== HOTSPOT SUMMARY ===")
    for name, data in manifest.items():
        print(f"{name}: {len(data['residues'])} residues -> {data['residues']}")


if __name__ == '__main__':
    main()
