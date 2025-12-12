
# tiny_universe/toy_engine.py
from __future__ import annotations
from typing import Any, Dict
import pandas as pd

import time
import logging

log = logging.getLogger("tiny-engine")

class TinyEngine:
    # ... 你原来的代码 ...

    def run_forever(self, heartbeat_sec: int = 30):
        log.info("TinyEngine entering run_forever loop")
        while True:
            time.sleep(heartbeat_sec)
            log.info("tiny alive")
