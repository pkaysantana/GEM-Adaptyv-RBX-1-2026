#!/usr/bin/env python3
"""
Extract CUL1 residues that contact RBX-1 from PDB 1LDJ.
Outputs a mini-PDB of the binding interface for ProteinMPNN input.
"""
from Bio.PDB import PDBParser, PDBIO, Select
import sys

CONTACT_CUTOFF = 8.0  # Angstroms, CA-CA distance
PDB_FILE = "/home/on/ProteinMPNN/inputs/rbx1/1LDJ.pdb"
OUT_INTERFACE_PDB = "/home/on/ProteinMPNN/inputs/rbx1/cul1_interface.pdb"
OUT_COMPLEX_PDB = "/home/on/ProteinMPNN/inputs/rbx1/interface_complex.pdb"

parser = PDBParser(QUIET=True)
structure = parser.get_structure("1LDJ", PDB_FILE)
model = structure[0]

chain_A = model["A"]  # CUL1
chain_B = model["B"]  # RBX-1

# Get all chain B CA atoms
rbx1_ca = []
for res in chain_B.get_residues():
    if "CA" in res:
        rbx1_ca.append(res["CA"])

# Find chain A residues within CONTACT_CUTOFF of any chain B CA
contact_residues = []
for res_a in chain_A.get_residues():
    if "CA" not in res_a:
        continue
    ca_a = res_a["CA"]
    for ca_b in rbx1_ca:
        dist = ca_a - ca_b
        if dist <= CONTACT_CUTOFF:
            contact_residues.append(res_a.get_id()[1])
            break

contact_residues = sorted(set(contact_residues))
print(f"CUL1 residues contacting RBX-1 (within {CONTACT_CUTOFF}Å): {len(contact_residues)}")
print(f"Residue numbers: {contact_residues}")

# Extend to a contiguous fragment (fill gaps <= 3 residues)
extended = set(contact_residues)
for r in contact_residues:
    for gap in range(1, 4):
        extended.add(r + gap)
        extended.add(r - gap)
extended = sorted(extended)

# Find contiguous segments
segments = []
seg_start = extended[0]
seg_end = extended[0]
for r in extended[1:]:
    if r == seg_end + 1:
        seg_end = r
    else:
        segments.append((seg_start, seg_end))
        seg_start = r
        seg_end = r
segments.append((seg_start, seg_end))
print(f"\nContiguous segments in CUL1: {segments}")
print(f"Segment lengths: {[e-s+1 for s,e in segments]}")

# Take the longest segment (most likely the main binding helix/loop)
longest = max(segments, key=lambda x: x[1] - x[0])
print(f"\nLongest contact segment: residues {longest[0]}-{longest[1]} ({longest[1]-longest[0]+1} AA)")

# Also check if combining segments gives 40-120 AA total
total_contact_aa = sum(e - s + 1 for s, e in segments)
print(f"Total contact AA: {total_contact_aa}")

# Write the interface mini-PDB (longest segment only)
class InterfaceSelect(Select):
    def __init__(self, chain_id, res_range):
        self.chain_id = chain_id
        self.res_min, self.res_max = res_range

    def accept_chain(self, chain):
        return chain.get_id() == self.chain_id

    def accept_residue(self, residue):
        res_num = residue.get_id()[1]
        return self.res_min <= res_num <= self.res_max

io = PDBIO()
io.set_structure(structure)
io.save(OUT_INTERFACE_PDB, InterfaceSelect("A", longest))
print(f"\nWrote interface mini-PDB: {OUT_INTERFACE_PDB}")

# Write complex (interface region + full RBX-1) for ProteinMPNN context
class ComplexSelect(Select):
    def __init__(self, res_range):
        self.res_min, self.res_max = res_range

    def accept_chain(self, chain):
        return chain.get_id() in ("A", "B")

    def accept_residue(self, residue):
        chain_id = residue.get_parent().get_id()
        if chain_id == "B":
            return True  # Keep all of RBX-1
        res_num = residue.get_id()[1]
        return self.res_min <= res_num <= self.res_max

io.save(OUT_COMPLEX_PDB, ComplexSelect(longest))
print(f"Wrote interface complex PDB: {OUT_COMPLEX_PDB}")
print("\nNext step: run ProteinMPNN on interface_complex.pdb with chain B fixed")
