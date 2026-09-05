"""Demo: the robot continuously observing the decoy against a live real asset.

The simulated real server runs Apache 2.4.54 until cycle 5, then applies a
security patch and upgrades to 2.4.55. The decoy does not follow. The observe
loop keeps verifying every cycle; once the stale banner leaves the recent
window the drift is caught, the decoy is corrected in place, and it stays
green afterwards.
"""

from decoytell.observe import observe

DECOY_INITIAL = {
    "service_banner": "Apache/2.4.54 (Debian)",
    "patch_cadence_days": 12,
    "timing_band": "fast",
    "account_age_days": 810,
    "monitoring_behavior": "immediate",
}


def main():
    seed = 6001
    print("DecoyTell - continuous observation (simulated live real asset)")
    print("Real asset: Apache/2.4.54 until cycle 5, then patches -> 2.4.55")
    print("Decoy starts as a faithful clone and does NOT follow the patch.")
    print("-" * 70)

    final_decoy, events = observe(seed, DECOY_INITIAL)

    def phase(events):
        blocks = []
        start = None
        prev = None
        for e in events:
            key = (e["verdict"], tuple(f["attribute"] for f in e["corrections"]))
            if key != prev:
                if start is not None:
                    blocks.append((start, e["cycle"] - 1, prev))
                start = e["cycle"]
                prev = key
        if start is not None:
            blocks.append((start, events[-1]["cycle"], prev))
        return blocks

    for lo, hi, (verdict, fixed) in phase(events):
        label = "CORRECTED (%s)" % ", ".join(fixed) if fixed else verdict
        print("cycle %-4d - %-4d  %s" % (lo, hi, label))

    print("-" * 70)
    print("Final decoy state (after continuous monitoring):")
    for k, v in sorted(final_decoy.items()):
        if isinstance(v, float):
            v = ("%.1f" % v).rstrip("0").rstrip(".")
        print("  %-22s %s" % (k, v))


if __name__ == "__main__":
    main()