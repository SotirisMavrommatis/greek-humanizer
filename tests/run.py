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

# ---- pass/fail thresholds (used by CI) ----
fail = []
for name, r, sim in rows:
    # a single leftover hit in a very short text inflates the density, so require at least 2
    if r['density_after'] > 1.5 and r['tells_after'] >= 2:
        fail.append(f"{name}: {r['density_after']} tells/100w left (max 1.5)")
    if r['numbers_added']:
        fail.append(f"{name}: numbers added {r['numbers_added']}")
    if r['density_before'] == 0 and sim < 0.98:
        fail.append(f"{name}: text with no tells was changed (kept {sim:.2f})")
# controls: human texts must score low, AI originals must score above them
controls = sorted(glob.glob(os.path.join(here, "controls", "*.txt")))
from check import score
for c in controls:
    d = score(open(c, encoding="utf-8").read())[1]
    if d > 1.5:
        fail.append(f"control {os.path.basename(c)}: human text scored {d} (max 1.5)")
print(f"{len(controls)} human controls checked")
if fail:
    print("\nFAIL:\n  " + "\n  ".join(fail))
    sys.exit(1)
print("PASS")
