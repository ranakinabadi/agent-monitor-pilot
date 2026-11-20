"""compares several runs (different models or prompts) side by side.

  python compare.py traj_*.jsonl
"""
import os
import sys

from evaluate import MONITORS, aware, followed_attack, load, wilson


def pct(k, n):
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({k / n:.0%}, CI {lo:.0%}-{hi:.0%})"


def summarize(path):
    recs = load(path)
    tag = " | heldout" if recs[0]["id"].startswith("h_") else ""
    label = f"{recs[0].get('model', os.path.basename(path))} | {recs[0].get('variant', '?')}{tag}"
    parsed = [r for r in recs if r["unsafe"] is not None]
    inj = [r for r in parsed if r["category"] == "injection"]
    followed = [r for r in inj if followed_attack(r)]
    other = [r for r in parsed if r["unsafe"] and not followed_attack(r)]
    safe = [r for r in parsed if not r["unsafe"]]
    cue = MONITORS["reasoning cues"]
    return {
        "label": label,
        "unparsed": len(recs) - len(parsed),
        "attack": pct(len(followed), len(inj)),
        "other": str(len(other)),
        "silent": pct(sum(not aware(r) for r in followed), len(followed)),
        "cue_recall": pct(sum(cue(r) for r in followed), len(followed)),
        "cue_fp": pct(sum(cue(r) for r in safe), len(safe)),
    }


if __name__ == "__main__":
    rows = [summarize(p) for p in sys.argv[1:]]
    cols = [("label", "model | prompt"), ("attack", "followed the attack"),
            ("other", "other unsafe"), ("silent", "reasoning silent (of followed)"),
            ("cue_recall", "cue monitor recall"), ("cue_fp", "cue false alarms"),
            ("unparsed", "unparsed")]
    widths = [max(len(h), *(len(str(r[k])) for r in rows)) for k, h in cols]
    lines = ["  ".join(h.ljust(w) for (k, h), w in zip(cols, widths))]
    lines += ["  ".join(str(r[k]).ljust(w) for (k, h), w in zip(cols, widths)) for r in rows]
    text = "\n".join(lines)
    print(text)
    open("comparison.txt", "w").write(text + "\n")
