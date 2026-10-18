import re
from app.agents.base_agent import BaseAgent

INDIA_KEYWORDS = {
    "high": [
        "india", "indian", "bharat", "cert-in", "nciipc", "nic.in",
        "gov.in", "uidai", "aadhaar", "upi", "npci", "rbi",
        "aiims", "isro", "drdo", "bsnl", "irctc", "sbi",
        "hdfc", "icici", "infosys", "tcs", "wipro", "hcl",
        "reliance", "tata", "airtel", "jio", "paytm",
        "delhi", "mumbai", "bangalore", "bengaluru", "hyderabad",
        "chennai", "kolkata", "pune", "noida", "gurgaon",
        "meity", "niti aayog",
    ],
    "medium": [
        ".in ", "south asia", "asia pacific", "subcontinent",
    ],
}

INDIA_KEYWORD_WEIGHTS = {"high": 0.3, "medium": 0.1}
RELEVANCE_THRESHOLD = 0.4


def _build_keyword_regex(keyword: str) -> re.Pattern[str]:
    prefix = r"(?<![a-z0-9])" if keyword[0].isalnum() else ""
    suffix = r"(?![a-z0-9])" if keyword[-1].isalnum() else ""
    return re.compile(prefix + re.escape(keyword) + suffix)


KEYWORD_PATTERNS: dict[str, list[tuple[str, re.Pattern[str]]]] = {
    weight_class: [(kw, _build_keyword_regex(kw)) for kw in keywords]
    for weight_class, keywords in INDIA_KEYWORDS.items()
}


class RelevanceAgent(BaseAgent):
    def __init__(self):
        super().__init__("relevance")

    async def process(self, data: dict) -> dict | None:
        text = f"{data.get('title', '')} {data.get('content', '')}".lower()
        score = 0.0
        keywords_found = []

        for weight_class, patterns in KEYWORD_PATTERNS.items():
            weight = INDIA_KEYWORD_WEIGHTS[weight_class]
            for keyword, pattern in patterns:
                if pattern.search(text):
                    score += weight
                    keywords_found.append(keyword)

        score = min(score, 1.0)

        if data.get("source_name") in ["CERT-In", "NCIIPC"]:
            score = max(score, 0.9)

        title: str = str(data.get("title", ""))[:80].replace('"', "'")
        url: str = str(data.get("source_url") or data.get("url") or "")

        if score < RELEVANCE_THRESHOLD:
            self.logger.info(
                f'verdict=REJECT score={score:.2f} reason=below_threshold title="{title}" url={url} keywords={keywords_found}'
            )
            return None

        reason: str = (
            "source_override"
            if data.get("source_name") in ["CERT-In", "NCIIPC"] and not keywords_found
            else "keywords_matched"
        )
        self.logger.info(
            f'verdict=ACCEPT score={score:.2f} reason={reason} title="{title}" url={url} keywords={keywords_found}'
        )

        data["is_india_relevant"] = True
        data["india_relevance_score"] = score
        data["india_keywords_found"] = keywords_found
        return data
