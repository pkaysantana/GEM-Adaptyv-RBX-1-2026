#!/usr/bin/env python3
"""
Extract the C-terminal CUL1 contact region (residues 655-762) + RBX-1
as a second structural template for ProteinMPNN.
This covers the other CUL1 contact segments: 668-676, 703-709, 752-762.
"""
from Bio.PDB import PDBParser, PDBIO, Select

class SecondInterface(Select):
    def accept_chain(self, chain):
        return chain.get_id() in ('A', 'B')
    def accept_residue(self, res):
        cid = res.get_parent().get_id()
        rn  = res.get_id()[1]
        if cid == 'B': return True          # all of RBX-1
        if cid == 'A': return 655 <= rn <= 762  # second contact span ~108 AA
        return False

parser = PDBParser(QUIET=True)
s = parser.get_structure('1LDJ', '/home/on/ProteinMPNN/inputs/rbx1/1LDJ.pdb')
io = PDBIO()
io.set_structure(s)
io.save('/home/on/ProteinMPNN/inputs/rbx1/interface2_complex.pdb', SecondInterface())
print('Wrote interface2_complex.pdb: CUL1 655-762 (108 AA) + full RBX-1')
