"""
extract_rbx1_hotspots.py
------------------------
Robust hotspot extraction for RBX1-directed RFdiffusion runs.

Outputs:
  - hotspot_manifest.json
  - hotspot_manifest.tsv

Hotspot sets:
  1. glomulin_interface_4f52
     RBX1 residues contacting Glomulin in 4F52.
  2. non_cullin_exposed_face_1ldj
     RBX1 residues in 1LDJ that are solvent-exposed and not contacting CUL1
     or other non-RBX1 chains in that assembly. This is a free-surface proxy,
     not a verified E2 interface.
  3. monomer_exposed_surface_2lgv
     RBX1 residues in 2LGV with high per-residue SASA on the structured region.
  4. curated_rfdiffusion_seed
     Small operational seed set built from overlap and weighted support across
     the three raw sets. Intended for RFdiffusion hotspot conditioning, not as
     a claim of biological truth.

Notes:
  - Residues < 40 are excluded by default because the RBX1 N-terminus is treated
    as disordered/high-risk for hotspot conditioning.
  - Chain IDs are validated but still use known defaults for the local files:
      4F52: RBX1=B, CUL1=A, GLMN=C
      1LDJ: RBX1=B, CUL1=A
      2LGV: RBX1=A
"""

from __future__ import annotations

import json
import math
import os
from collections import Counter
from dataclasses import dataclass, asdict
from typing import Dict, List, Iterable, Tuple, Set

from Bio.PDB import MMCIFParser, NeighborSearch, ShrakeRupley
from Bio.PDB.Residue import Residue
from Bio.PDB.Chain import Chain
from Bio.PDB.Structure import Structure

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CIF_DIR = SCRIPT_DIR

MIN_RES = 40
CONTACT_CUTOFF_ANG = 4.5
SASA_Q = 0.70          # top 30% SASA within structured RBX1 region
STRICT_CONTACT_CUTOFF_ANG = 4.0

KNOWN_CHAINS = {
    "4F52": {"rbx1": "B", "cul1": "A", "partner": "C"},
    "1LDJ": {"rbx1": "B", "cul1": "A"},
    "2LGV": {"rbx1": "A"},
}


@dataclass
class HotspotSet:
    name: str
    source_pdb: str
    chain_id: str
    residues: List[int]
    rationale: str
    method: str
    notes: List[str]


def parse_structure(cif_path: str, structure_id: str) -> Structure:
    parser = MMCIFParser(QUIET=True)
    return parser.get_structure(structure_id, cif_path)


def is_standard_polymer_residue(res: Residue) -> bool:
    hetflag, _, _ = res.get_id()
    return hetflag == " "


def chain_residues(chain: Chain, min_res: int = MIN_RES) -> List[Residue]:
    out = []
    for res in chain.get_residues():
        if not is_standard_polymer_residue(res):
            continue
        if res.get_id()[1] < min_res:
            continue
        out.append(res)
    return out


def chain_summary(chain: Chain) -> dict:
    residues = [r for r in chain.get_residues() if is_standard_polymer_residue(r)]
    ids = [r.get_id()[1] for r in residues]
    return {
        "chain_id": chain.id,
        "n_residues": len(residues),
        "min_resseq": min(ids) if ids else None,
        "max_resseq": max(ids) if ids else None,
        "first_five": [
            f"{r.get_resname()}:{r.get_id()[1]}{r.get_id()[2].strip() or ''}"
            for r in residues[:5]
        ],
    }


def get_chain_or_raise(structure: Structure, pdb_id: str, role: str) -> Chain:
    model = structure[0]
    expected = KNOWN_CHAINS[pdb_id][role]
    if expected not in model:
        raise KeyError(
            f"{pdb_id}: expected chain {expected!r} for role {role!r}, "
            f"but available chains are {[c.id for c in model.get_chains()]}"
        )
    return model[expected]


def heavy_atoms(chain: Chain) -> list:
    atoms = []
    for res in chain.get_residues():
        if not is_standard_polymer_residue(res):
            continue
        for atom in res.get_atoms():
            if atom.element != "H":
                atoms.append(atom)
    return atoms


def contacting_residues(
    source_chain: Chain,
    partner_chain: Chain,
    cutoff: float = CONTACT_CUTOFF_ANG,
) -> Set[int]:
    ns = NeighborSearch(heavy_atoms(partner_chain))
    hits: Set[int] = set()
    for res in source_chain.get_residues():
        if not is_standard_polymer_residue(res):
            continue
        resseq = res.get_id()[1]
        if resseq < MIN_RES:
            continue
        for atom in res.get_atoms():
            if atom.element == "H":
                continue
            if ns.search(atom.coord, cutoff, level="A"):
                hits.add(resseq)
                break
    return hits


def contacting_residues_any(
    source_chain: Chain,
    partner_chains: Iterable[Chain],
    cutoff: float = CONTACT_CUTOFF_ANG,
) -> Set[int]:
    combined: Set[int] = set()
    for ch in partner_chains:
        combined |= contacting_residues(source_chain, ch, cutoff=cutoff)
    return combined


def compute_residue_sasa(structure: Structure) -> Dict[Tuple[str, int, str], float]:
    """
    Compute per-residue SASA using ShrakeRupley and return:
      {(chain_id, resseq, icode): sasa}
    """
    sr = ShrakeRupley()
    sr.compute(structure, level="R")
    out: Dict[Tuple[str, int, str], float] = {}
    for model in structure:
        for chain in model:
            for res in chain:
                if not is_standard_polymer_residue(res):
                    continue
                _, resseq, icode = res.get_id()
                sasa = getattr(res, "sasa", None)
                if sasa is None:
                    continue
                out[(chain.id, resseq, icode.strip())] = float(sasa)
        break  # first model only
    return out


def quantile(values: List[float], q: float) -> float:
    if not values:
        raise ValueError("Cannot compute quantile of empty list")
    xs = sorted(values)
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    frac = pos - lo
    return xs[lo] * (1 - frac) + xs[hi] * frac


def write_manifest_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def write_manifest_tsv(path: str, hotspot_sets: List[HotspotSet]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("set_name\tsource_pdb\tchain_id\tresidues\trationale\tmethod\n")
        for hs in hotspot_sets:
            residues = ",".join(map(str, hs.residues))
            rationale = hs.rationale.replace("\t", " ").replace("\n", " ")
            method = hs.method.replace("\t", " ").replace("\n", " ")
            f.write(
                f"{hs.name}\t{hs.source_pdb}\t{hs.chain_id}\t{residues}\t"
                f"{rationale}\t{method}\n"
            )


# ──────────────────────────────────────────────────────────────────────────────
# Extraction functions
# ──────────────────────────────────────────────────────────────────────────────

def extract_glomulin_interface(cif_path: str) -> Tuple[HotspotSet, dict]:
    structure = parse_structure(cif_path, "4F52")
    model = structure[0]
    rbx1 = get_chain_or_raise(structure, "4F52", "rbx1")
    glmn = get_chain_or_raise(structure, "4F52", "partner")

    loose = contacting_residues(rbx1, glmn, cutoff=CONTACT_CUTOFF_ANG)
    strict = contacting_residues(rbx1, glmn, cutoff=STRICT_CONTACT_CUTOFF_ANG)
    residues = sorted(loose)

    summary = {
        "chains": [c.id for c in model.get_chains()],
        "rbx1_summary": chain_summary(rbx1),
        "partner_summary": chain_summary(glmn),
        "strict_contact_residues": sorted(strict),
        "loose_contact_residues": residues,
    }

    hs = HotspotSet(
        name="glomulin_interface_4f52",
        source_pdb="4F52",
        chain_id=rbx1.id,
        residues=residues,
        rationale=(
            "RBX1 residues contacting Glomulin in 4F52. This is the strongest "
            "structure-grounded protein-binding surface in the set because GLMN "
            "occupies the RBX1 RING-domain face in the solved complex."
        ),
        method=(
            f"Heavy-atom contact extraction between RBX1 and GLMN at "
            f"{CONTACT_CUTOFF_ANG:.1f} A; strict contact set also recorded at "
            f"{STRICT_CONTACT_CUTOFF_ANG:.1f} A."
        ),
        notes=[
            "Residues < 40 excluded.",
            "Use this as a high-priority hotspot source for RFdiffusion.",
        ],
    )
    return hs, summary


def extract_non_cullin_exposed_face(cif_path: str) -> Tuple[HotspotSet, dict]:
    structure = parse_structure(cif_path, "1LDJ")
    model = structure[0]
    rbx1 = get_chain_or_raise(structure, "1LDJ", "rbx1")
    cul1 = get_chain_or_raise(structure, "1LDJ", "cul1")
    other_chains = [c for c in model.get_chains() if c.id not in {rbx1.id, cul1.id}]

    sasa_map = compute_residue_sasa(structure)
    all_rbx1_res = chain_residues(rbx1, min_res=MIN_RES)
    all_resseqs = [r.get_id()[1] for r in all_rbx1_res]

    cul1_contacts = contacting_residues(rbx1, cul1, cutoff=CONTACT_CUTOFF_ANG)
    non_rbx1_contacts = contacting_residues_any(
        rbx1, other_chains, cutoff=CONTACT_CUTOFF_ANG
    )

    sasa_vals = []
    residue_sasa = {}
    for res in all_rbx1_res:
        _, resseq, icode = res.get_id()
        key = (rbx1.id, resseq, icode.strip())
        sasa = sasa_map.get(key, 0.0)
        residue_sasa[resseq] = sasa
        sasa_vals.append(sasa)

    sasa_cut = quantile(sasa_vals, SASA_Q)
    exposed = {resseq for resseq, sasa in residue_sasa.items() if sasa >= sasa_cut}

    free_surface = sorted(set(all_resseqs) - cul1_contacts - non_rbx1_contacts)
    exposed_free_surface = sorted(set(free_surface) & exposed)

    summary = {
        "chains": [c.id for c in model.get_chains()],
        "rbx1_summary": chain_summary(rbx1),
        "cul1_summary": chain_summary(cul1),
        "other_chain_ids": [c.id for c in other_chains],
        "cul1_contact_residues": sorted(cul1_contacts),
        "other_chain_contact_residues": sorted(non_rbx1_contacts),
        "free_surface_residues": free_surface,
        "sasa_cutoff": sasa_cut,
        "exposed_free_surface_residues": exposed_free_surface,
    }

    hs = HotspotSet(
        name="non_cullin_exposed_face_1ldj",
        source_pdb="1LDJ",
        chain_id=rbx1.id,
        residues=exposed_free_surface,
        rationale=(
            "RBX1 residues in 1LDJ that are solvent-exposed and not contacting "
            "CUL1 or other chains in that SCF assembly. This is a free-surface "
            "proxy, not a verified E2 interface."
        ),
        method=(
            "Subtract 4.5 A heavy-atom contact residues to non-RBX1 chains, then "
            f"retain only residues with SASA in the top {(1-SASA_Q)*100:.0f}% "
            "within RBX1 residues >= 40."
        ),
        notes=[
            "Do not interpret this set as a proven E2-binding site.",
            "Useful as a non-CUL1-biased alternative RFdiffusion seed.",
        ],
    )
    return hs, summary


def extract_monomer_exposed_surface(cif_path: str) -> Tuple[HotspotSet, dict]:
    structure = parse_structure(cif_path, "2LGV")
    model = structure[0]
    rbx1 = get_chain_or_raise(structure, "2LGV", "rbx1")

    sasa_map = compute_residue_sasa(structure)
    residues = chain_residues(rbx1, min_res=MIN_RES)

    residue_sasa = {}
    for res in residues:
        _, resseq, icode = res.get_id()
        key = (rbx1.id, resseq, icode.strip())
        residue_sasa[resseq] = sasa_map.get(key, 0.0)

    sasa_vals = list(residue_sasa.values())
    sasa_cut = quantile(sasa_vals, SASA_Q)
    exposed = sorted([resseq for resseq, sasa in residue_sasa.items() if sasa >= sasa_cut])

    summary = {
        "chains": [c.id for c in model.get_chains()],
        "rbx1_summary": chain_summary(rbx1),
        "sasa_cutoff": sasa_cut,
        "residue_sasa": {str(k): v for k, v in sorted(residue_sasa.items())},
        "selected_residues": exposed,
        "nmr_model_index_used": 0,
    }

    hs = HotspotSet(
        name="monomer_exposed_surface_2lgv",
        source_pdb="2LGV",
        chain_id=rbx1.id,
        residues=exposed,
        rationale=(
            "Most solvent-exposed residues on the structured RBX1 monomer in 2LGV. "
            "This gives an accessibility-biased view without cullin occupancy."
        ),
        method=(
            f"Per-residue SASA via ShrakeRupley on model 0; select top "
            f"{(1-SASA_Q)*100:.0f}% SASA residues among RBX1 residues >= 40."
        ),
        notes=[
            "2LGV is an NMR entry; this script uses model 0 only.",
            "This is a monomer accessibility set, not an interface truth set.",
        ],
    )
    return hs, summary


def build_curated_seed(
    sets: List[HotspotSet],
    max_residues: int = 12,
) -> HotspotSet:
    weights = {
        "glomulin_interface_4f52": 3,
        "non_cullin_exposed_face_1ldj": 2,
        "monomer_exposed_surface_2lgv": 1,
    }
    votes = Counter()
    for hs in sets:
        w = weights.get(hs.name, 1)
        for r in hs.residues:
            votes[r] += w

    ranked = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))
    curated = [r for r, _ in ranked[:max_residues]]

    return HotspotSet(
        name="curated_rfdiffusion_seed",
        source_pdb="4F52+1LDJ+2LGV",
        chain_id="RBX1-mapped",
        residues=sorted(curated),
        rationale=(
            "Operational hotspot seed set for RFdiffusion, built from overlap and "
            "weighted support across the three raw structure-derived sets."
        ),
        method=(
            "Weighted vote: GLMN interface=3, non-CUL1 exposed face=2, "
            "monomer exposed surface=1; top residues retained."
        ),
        notes=[
            "This set is for RFdiffusion conditioning convenience.",
            "Treat the raw sets as primary evidence; treat this curated set as an operational summary.",
        ],
    )


def main() -> None:
    cif_files = {
        "4F52": os.path.join(CIF_DIR, "4F52.cif"),
        "1LDJ": os.path.join(CIF_DIR, "1LDJ.cif"),
        "2LGV": os.path.join(CIF_DIR, "2LGV.cif"),
    }

    missing = [p for p in cif_files.values() if not os.path.exists(p)]
    if missing:
        raise FileNotFoundError(f"Missing CIF files: {missing}")

    hs_glmn, sum_glmn = extract_glomulin_interface(cif_files["4F52"])
    hs_free, sum_free = extract_non_cullin_exposed_face(cif_files["1LDJ"])
    hs_mono, sum_mono = extract_monomer_exposed_surface(cif_files["2LGV"])
    hs_seed = build_curated_seed([hs_glmn, hs_free, hs_mono], max_residues=12)

    hotspot_sets = [hs_glmn, hs_free, hs_mono, hs_seed]

    manifest = {
        "metadata": {
            "min_residue": MIN_RES,
            "contact_cutoff_angstrom": CONTACT_CUTOFF_ANG,
            "strict_contact_cutoff_angstrom": STRICT_CONTACT_CUTOFF_ANG,
            "sasa_quantile_threshold": SASA_Q,
            "files": cif_files,
        },
        "chain_validation": {
            "4F52": sum_glmn,
            "2LGV": sum_mono,
            "1LDJ": sum_free,
        },
        "hotspot_sets": {hs.name: asdict(hs) for hs in hotspot_sets},
    }

    json_path = os.path.join(SCRIPT_DIR, "hotspot_manifest.json")
    tsv_path = os.path.join(SCRIPT_DIR, "hotspot_manifest.tsv")
    write_manifest_json(json_path, manifest)
    write_manifest_tsv(tsv_path, hotspot_sets)

    print(f"Saved: {json_path}")
    print(f"Saved: {tsv_path}")
    print("\n=== HOTSPOT SUMMARY ===")
    for hs in hotspot_sets:
        print(f"{hs.name}: {len(hs.residues)} residues -> {hs.residues}")

    print("\n=== CHAIN VALIDATION ===")
    for pdb_id, summary in [("4F52", sum_glmn), ("1LDJ", sum_free), ("2LGV", sum_mono)]:
        print(f"\n{pdb_id}:")
        print(f"  chains present: {summary['chains']}")
        rbx1_sum = summary["rbx1_summary"]
        print(f"  RBX1 chain {rbx1_sum['chain_id']}: "
              f"{rbx1_sum['n_residues']} residues, "
              f"range {rbx1_sum['min_resseq']}-{rbx1_sum['max_resseq']}, "
              f"first five: {rbx1_sum['first_five']}")


if __name__ == "__main__":
    main()
