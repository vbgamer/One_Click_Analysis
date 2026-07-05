"""Universal analysis modules. Each returns {available, findings: [...], ...}.

A finding is a dict:
{
  "id": str,               # stable id for dedup
  "category": str,         # quality | trend | segment | driver | anomaly | relationship | descriptive
  "title": str,            # short headline
  "severity": str,         # info | notice | warning | critical
  "impact": float,         # 0-10 how much this matters
  "confidence": float,     # 0-1 statistical confidence
  "metric": dict,          # the exact computed numbers backing the finding
  "plain_english": str,    # analyst-style sentence(s), template generated
  "chart": dict | None,    # optional chart spec for the frontend
}
"""


def make_finding(
    fid: str,
    category: str,
    title: str,
    plain_english: str,
    severity: str = "info",
    impact: float = 5.0,
    confidence: float = 0.9,
    metric: dict | None = None,
    chart: dict | None = None,
) -> dict:
    return {
        "id": fid,
        "category": category,
        "title": title,
        "severity": severity,
        "impact": round(float(impact), 2),
        "confidence": round(float(confidence), 3),
        "metric": metric or {},
        "plain_english": plain_english,
        "chart": chart,
    }
