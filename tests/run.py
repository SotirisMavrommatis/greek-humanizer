#!/usr/bin/env python3
"""Run the checker over every before/after pair in tests/corpus and print a summary."""
import difflib, glob, os, statistics, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, "..", "skills", "greek-humanizer", "scripts"))
from check import compare

rows = []
for b in sorted(glob.glob(os.path.join(here, "corpus", "*.before.txt"))):
    name = os.path.basename(b)[:-len(".before.txt")]
    before = open(b, encoding="utf-8").read()
    after = open(b.replace(".before.", ".after."), encoding="utf-8").read()
    r = compare(before, after)
    sim = difflib.SequenceMatcher(None, before, after).ratio()
    rows.append((name, r, sim))
    print(f"{name:24} tells/100w {r['density_before']:5} -> {r['density_after']:4}  "
          f"len {r['length_ratio']:4}  kept {sim:.2f}  lost={r['facts_lost'] or '-'}")
d = [r['density_after'] for _, r, _ in rows]
print(f"\n{len(rows)} texts | mean after {statistics.mean(d):.2f} | max after {max(d)} | "
      f"numbers added {sum(len(r['numbers_added']) for _, r, _ in rows)}")
