from dataclasses import dataclass

@dataclass
class RiskVerdict:
    allowed: bool
    reason: str

    def __bool__(self):
        return self.allowed