#!/usr/bin/env python3
import csv, re
from pathlib import Path
from collections import Counter

def parse_fa(fa_path, scaffold_tag):
    seqs, meta = [], {}
    for line in Path(fa_path).read_text().splitlines():
        if line.startswith('>'):
            m_sc = re.search(r'score=([\d.]+)', line)
            m_t  = re.search(r'T=([\d.]+)', line)
            m_s  = re.search(r'sample=(\d+)', line)
            meta = {
                'score':    float(m_sc.group(1)) if m_sc else 999,
                'temp':     float(m_t.group(1))  if m_t  else 0,
                'sample':   int(m_s.group(1))    if m_s  else 0,
                'scaffold': scaffold_tag,
            }
        else:
            seq = line.strip()
            if seq and meta.get('sample', 0) > 0 and 40 <= len(seq) <= 120:
                seqs.append({**meta, 'sequence': seq})
    return seqs

pool = (
    parse_fa('/home/on/ProteinMPNN/outputs/rbx1_binders/seqs/interface_complex.fa',    'if1') +
    parse_fa('/home/on/ProteinMPNN/outputs/rbx1_diverse/seqs/interface_complex.fa',    'if1') +
    parse_fa('/home/on/ProteinMPNN/outputs/rbx1_if2_low/seqs/interface2_complex.fa',   'if2') +
    parse_fa('/home/on/ProteinMPNN/outputs/rbx1_if2_high/seqs/interface2_complex.fa',  'if2') +
    parse_fa('/home/on/ProteinMPNN/outputs/rbx1_if2_biased/seqs/interface2_complex.fa','if2')
)

seen, unique = set(), []
for s in pool:
    if s['sequence'] not in seen:
        seen.add(s['sequence'])
        unique.append(s)

print(f'Total pool: {len(unique)} unique sequences')
scaffolds = Counter(s['scaffold'] for s in unique)
lengths   = Counter(len(s['sequence']) for s in unique)
print(f'Scaffold: {dict(scaffolds)}')
print(f'Lengths:  {dict(lengths)}')

unique.sort(key=lambda x: x['score'])

def is_biophysically_sane(seq):
    n = len(seq)
    # Max any single AA: 20%
    if max(seq.count(aa) for aa in 'ACDEFGHIKLMNPQRSTVWY') / n > 0.20:
        return False
    # Charged residues R+K: max 25%
    if (seq.count('R') + seq.count('K')) / n > 0.25:
        return False
    # Aromatic F+W+Y: max 25% (avoid heuristic-style stuffing)
    if (seq.count('F') + seq.count('W') + seq.count('Y')) / n > 0.25:
        return False
    # Net charge: must be between -8 and +8
    net = (seq.count('K') + seq.count('R')) - (seq.count('D') + seq.count('E'))
    if abs(net) > 8:
        return False
    # Proline: max 12% (too many = can't fold)
    if seq.count('P') / n > 0.12:
        return False
    return True

pre_filter = len(unique)
unique = [s for s in unique if is_biophysically_sane(s['sequence'])]
print(f'After biophysical filter: {len(unique)}/{pre_filter} sequences pass')

def identity(a, b):
    return sum(x == y for x, y in zip(a, b)) / max(len(a), len(b))

selected = []
for cand in unique:
    if len(selected) >= 100:
        break
    if not any(identity(cand['sequence'], s['sequence']) > 0.65 for s in selected):
        selected.append(cand)

print(f'\nSelected: {len(selected)} sequences')
sel_scaffolds = Counter(s['scaffold'] for s in selected)
sel_temps     = Counter(round(s['temp'], 1) for s in selected)
sel_lengths   = Counter(len(s['sequence']) for s in selected)
print(f'Scaffold mix: {dict(sel_scaffolds)}')
print(f'Temp mix:     {dict(sorted(sel_temps.items()))}')
print(f'Length mix:   {dict(sel_lengths)}')

scores = [s['score'] for s in selected]
print(f'Score range:  {min(scores):.4f}-{max(scores):.4f}  Mean: {sum(scores)/len(scores):.4f}')

ref    = selected[0]['sequence']
idents = [identity(ref, s['sequence']) for s in selected[1:]]
print(f'Identity to rank-1 — mean: {sum(idents)/len(idents):.1%}  min: {min(idents):.1%}')

out       = Path('/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/final_rbx1_submission_competition.csv')
fasta_out = Path('/mnt/c/Users/Don/GEM-Adaptyv-RBX-1 2026/GEM-Adaptyv-RBX-1-2026/final_rbx1_submission.fasta')

with open(out, 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Name', 'Sequence'])
    for i, s in enumerate(selected, 1):
        w.writerow([f'RBX1_MPNN_{i:03d}', s['sequence']])

with open(fasta_out, 'w') as f:
    for i, s in enumerate(selected, 1):
        name   = f'RBX1_MPNN_{i:03d}'
        region = 'CUL1_530-621' if s['scaffold'] == 'if1' else 'CUL1_655-762'
        f.write(f'>{name} | scaffold={region} | T={s["temp"]} | score={s["score"]:.4f}\n{s["sequence"]}\n')

print(f'\nWrote: {out}')
print(f'Wrote: {fasta_out}')
print('\nTop 5:')
for i, s in enumerate(selected[:5], 1):
    print(f'  {i}. [{s["scaffold"]}] T={s["temp"]} score={s["score"]:.4f} L={len(s["sequence"])} {s["sequence"][:50]}...')
