ABNORMAL_PTS = 8
CRITICAL_PTS = 20
ABNORMAL_CAP = 40
CRITICAL_CAP = 60

TIERS = [
    (80, "High",       "red"),
    (70, "Borderline", "orange"),
    (50, "Moderate",   "yellow"),
    (0,  "Low",        "green"),
]


def compute_score(indicators: list) -> int:
    abnormal = sum(1 for i in indicators if i.get("status") == "abnormal")
    critical = sum(1 for i in indicators if i.get("status") == "critical")
    pts_abnormal = min(abnormal * ABNORMAL_PTS, ABNORMAL_CAP)
    pts_critical = min(critical * CRITICAL_PTS, CRITICAL_CAP)
    return min(pts_abnormal + pts_critical, 100)


def get_tier(score: int) -> tuple[str, str]:
    for threshold, label, color in TIERS:
        if score >= threshold:
            return label, color
    return "Low", "green"


def get_flagged(indicators: list) -> list:
    return [i for i in indicators if i.get("status") in ("abnormal", "critical")]


def score_report(indicators: list) -> dict:
    score = compute_score(indicators)
    tier, color = get_tier(score)
    flagged = get_flagged(indicators)
    return {
        "score": score,
        "tier": tier,
        "color": color,
        "flagged": flagged,
        "total": len(indicators),
        "flagged_count": len(flagged),
    }