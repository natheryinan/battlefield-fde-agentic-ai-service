from datetime import datetime
from dataclasses import dataclass

@dataclass
class LegalPacketContainer:
    packet_id: str
    time_seal_until: datetime
    early_wangzha: bool = True
    alpha_release_executed: bool = False
    redaction_mode: str = "HARD"   # NONE | SOFT | HARD

    def context(self, channel: str):
        return {
            "now": datetime.utcnow(),
            "time_seal_until": self.time_seal_until,
            "early_wangzha": self.early_wangzha,
            "alpha_release_executed": self.alpha_release_executed,
            "channel": channel,
            "redaction_mode": self.redaction_mode,
        }
