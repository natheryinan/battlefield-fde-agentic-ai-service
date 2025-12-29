
# WELCOME TO YOUR DESTINY FATE 

from fde.kernel.hard_constraints import HardConstraints

class HardGate:
    @staticmethod
    def veto(state, hc: HardConstraints) -> bool:
        ψ = state["psych_load"]
        τ = state["time_pressure"]
        r = state["runway"].survival_index()

        if hc.psych_forbidden_zone[0] <= ψ <= hc.psych_forbidden_zone[1]:
            return True
        if r <= hc.runway_floor:
            return True
        if τ <= hc.time_floor:
            return True

        return False
