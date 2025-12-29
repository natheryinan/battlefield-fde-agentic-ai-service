
# fde/kernel/hotswap.py

import threading
from fde.kernel.hard_constraints import HardConstraints
from fde.kernel.capability import OverlordCap, GuardianCap

class HardConstraintHotSwap:
    def __init__(self, initial: HardConstraints):
        self._lock = threading.RLock()
        self._hc = initial

    def get(self) -> HardConstraints:
        with self._lock:
            return self._hc

    def swap(self, cap, **kwargs) -> HardConstraints:
        if not isinstance(cap, (OverlordCap, GuardianCap)):
            raise PermissionError("HOTSWAP_LOCKED")

        with self._lock:
            self._hc = HardConstraints(**{
                **self._hc.__dict__, **kwargs
            })
            return self._hc
