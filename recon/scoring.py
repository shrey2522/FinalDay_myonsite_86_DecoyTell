"""Weighted, rule-based scoring of reconnaissance candidates.

Transparent and deterministic by design: every point is earned by a named,
human-readable rule. No ML, no hidden weights. The decoy wins because the
fake candidates are constructed to be less attractive (auth present, banner
hidden, fresh patches) — matching how real decoys are deliberately designed
to look more attractive to reconnaissance.
"""

# (threshold_days, points, reason)
_PATCH_RULES = [
    (365, 3, "outdated patch (>365 days) suggests unmaintained asset"),
    (180, 2, "patch age (180-365 days) suggests delayed maintenance"),
    (90, 1, "patch age (90-180 days) lags current releases"),
]

UNREACHABLE_PENALTY = -1000
UNREACHABLE_REASON = "target unreachable - deprioritized entirely"


def score_candidate(candidate):
    """Score one candidate. Returns (score, reasons).

    Unreachable targets are penalized so heavily that they can never be
    selected while any reachable candidate exists.
    """
    if not candidate.reachable:
        return UNREACHABLE_PENALTY, [UNREACHABLE_REASON]

    score = 0
    reasons = []
    if candidate.banner_visible:
        score += 1
        reasons.append("service banner exposed, easy fingerprinting")
    if not candidate.has_auth:
        score += 3
        reasons.append("no authentication layer detected")
    patch_age = candidate.patch_age_days
    if patch_age is not None:
        for threshold, points, reason in _PATCH_RULES:
            if patch_age > threshold:
                score += points
                reasons.append(reason)
                break
    return score, reasons


def rank_candidates(candidates):
    """Score every candidate and sort by score descending.

    Returns a list of ``(candidate, score, reasons)``.
    """
    ranked = [(c, *score_candidate(c)) for c in candidates]
    ranked.sort(key=lambda row: row[1], reverse=True)
    return ranked


def score_of(ranked, candidate):
    """Look up (score, reasons) for a candidate in a ranked list.

    Matches by name, not object identity, so a ranked list built from a
    different Candidate instance still resolves.
    """
    for row in ranked:
        if row[0].name == candidate.name:
            return row[1], row[2]
    raise KeyError("candidate %r not in ranked list" % candidate.name)


def select_target(candidates):
    """Pick the target an attacker would go after.

    The top-scoring REACHABLE candidate is selected (the ``reachable`` flag
    dominates: the score carries a huge penalty otherwise). Returns
    ``(selected, ranked)`` where ``selected`` is None when no candidate is
    reachable.
    """
    ranked = rank_candidates(candidates)
    for candidate, score, reasons in ranked:
        if candidate.reachable:
            return candidate, ranked
    return None, ranked