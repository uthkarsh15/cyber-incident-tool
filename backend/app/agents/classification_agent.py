from app.agents.base_agent import BaseAgent

ATTACK_TYPE_KEYWORDS = {
    "ransomware": ["ransomware", "ransom", "encrypt files", "lockbit", "conti", "ryuk"],
    "phishing": ["phishing", "spear phishing", "credential harvest", "fake login"],
    "ddos": ["ddos", "denial of service", "traffic flood", "botnet attack"],
    "data_breach": ["data breach", "data leak", "records exposed", "personal data"],
    "apt_campaign": ["apt", "advanced persistent", "nation state", "espionage"],
    "defacement": ["defacement", "defaced", "website hacked"],
    "malware": ["malware", "trojan", "worm", "spyware", "backdoor", "rootkit"],
    "sql_injection": ["sql injection", "sqli"],
    "xss": ["cross-site scripting", "xss"],
    "supply_chain": ["supply chain", "solarwinds", "dependency confusion"],
    "zero_day": ["zero-day", "zero day", "0-day", "0day"],
}

SEVERITY_INDICATORS = {
    "critical": ["critical", "emergency", "immediate action", "actively exploited", "rce"],
    "high": ["high severity", "high risk", "significant", "major"],
    "medium": ["moderate", "medium", "potential risk"],
    "low": ["low risk", "minor", "informational"],
}

SECTOR_KEYWORDS = {
    "banking_finance": ["bank", "banking", "financial", "rbi", "upi", "npci", "sbi", "hdfc"],
    "healthcare": ["hospital", "healthcare", "aiims", "medical", "health"],
    "government": ["government", "gov.in", "nic", "ministry", "department"],
    "energy_power": ["power grid", "energy", "electricity", "oil", "gas"],
    "telecom": ["telecom", "bsnl", "airtel", "jio", "5g", "mobile network"],
    "defence": ["defence", "defense", "military", "army", "navy", "drdo"],
    "education": ["university", "college", "education", "school", "academic"],
    "it_ites": ["it company", "infosys", "tcs", "wipro", "software"],
}

class ClassificationAgent(BaseAgent):
    def __init__(self):
        super().__init__("classification")

    def _match_keywords(self, text: str, keyword_map: dict) -> tuple[str | None, float]:
        best_match = None
        best_score = 0.0
        for category, keywords in keyword_map.items():
            hits = sum(1 for kw in keywords if kw in text)
            if hits > 0:
                score = hits / len(keywords)
                if score > best_score:
                    best_score = score
                    best_match = category
        return best_match, min(best_score * 2, 1.0)

    async def process(self, data: dict) -> dict | None:
        text = f"{data.get('title', '')} {data.get('content', '')}".lower()

        attack_type, attack_confidence = self._match_keywords(text, ATTACK_TYPE_KEYWORDS)
        data["attack_type"] = attack_type or "unknown"

        severity, _ = self._match_keywords(text, SEVERITY_INDICATORS)
        data["severity"] = severity or "info"

        sector, _ = self._match_keywords(text, SECTOR_KEYWORDS)
        data["sector_code"] = sector

        data["confidence_score"] = attack_confidence
        return data
