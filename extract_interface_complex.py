#!/usr/bin/env python3
from Bio.PDB import PDBParser, PDBIO, Select

class InterfaceComplex(Select):
    def accept_chain(self, chain):
        return chain.get_id() in ('A', 'B')
    def accept_residue(self, res):
        cid = res.get_parent().get_id()
        rn = res.get_id()[1]
        if cid == 'B': return True              # all of RBX-1
        if cid == 'A': return 530 <= rn <= 621  # CUL1 main contact span
        return False

parser = PDBParser(QUIET=True)
s = parser.get_structure('1LDJ', '/home/on/ProteinMPNN/inputs/rbx1/1LDJ.pdb')
io = PDBIO()
io.set_structure(s)
io.save('/home/on/ProteinMPNN/inputs/rbx1/interface_complex.pdb', InterfaceComplex())
print('Wrote interface_complex.pdb: CUL1 residues 530-621 (92 AA) + full RBX-1 chain B (90 AA)')
