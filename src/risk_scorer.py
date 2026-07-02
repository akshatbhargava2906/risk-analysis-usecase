from src.questionnaire import questionnaire_risk_points

ABNORMAL_PTS = 8
CRITICAL_PTS = 20
ABNORMAL_CAP = 40
CRITICAL_CAP = 60

TIERS = [
    (75, "Risk", "red"),
    (50, "High", "orange"),
    (0, "Normal", "green"),
]


def compute_indicator_score(indicators: list) -> int:
    abnormal = sum(1 for i in indicators if i.get("status") == "abnormal")
    critical = sum(1 for i in indicators if i.get("status") == "critical")
    pts_abnormal = min(abnormal * ABNORMAL_PTS, ABNORMAL_CAP)
    pts_critical = min(critical * CRITICAL_PTS, CRITICAL_CAP)
    return pts_abnormal + pts_critical


def get_tier(score: int) -> tuple[str, str]:
    for threshold, label, color in TIERS:
        if score >= threshold:
            return label, color
    return "Low", "green"


def get_flagged(indicators: list) -> list:
    return [i for i in indicators if i.get("status") in ("abnormal", "critical")]


def score_report(indicators: list, questionnaire: dict = None) -> dict:
    indicator_pts = compute_indicator_score(indicators)
    questionnaire_pts = questionnaire_risk_points(questionnaire or {})
    score = min(indicator_pts + questionnaire_pts, 100)
    tier, color = get_tier(score)
    flagged = get_flagged(indicators)

    return {
        "score": score,
        "indicator_pts": indicator_pts,
        "questionnaire_pts": questionnaire_pts,
        "tier": tier,
        "color": color,
        "flagged": flagged,
        "total": len(indicators),
        "flagged_count": len(flagged),
    }