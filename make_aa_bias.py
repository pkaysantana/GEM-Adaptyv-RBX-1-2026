#!/usr/bin/env python3
"""Write ProteinMPNN AA bias JSON: penalise R/K, boost E/D/L/A for balance."""
import json
from pathlib import Path

# Negative = penalise, positive = favour
bias = {
    "A":  0.5, "C":  0.0, "D":  0.5, "E":  0.5,
    "F": -0.3, "G":  0.0, "H":  0.0, "I":  0.3,
    "K": -1.5, "L":  0.5, "M":  0.0, "N":  0.3,
    "P":  0.0, "Q":  0.3, "R": -1.5, "S":  0.3,
    "T":  0.3, "V":  0.3, "W": -0.5, "Y": -0.3,
}

out = Path("/home/on/ProteinMPNN/inputs/rbx1/aa_bias.jsonl")
with open(out, "w") as f:
    json.dump(bias, f)
    f.write("\n")
print(f"Wrote {out}")
