from fde.kernel.hard_constraints import HardConstraints
from fde.kernel.hotswap import HardConstraintHotSwap
from fde.kernel.overlord import StrategicOverlord, LordGuardian
from fde.kernel.sovereign_router import SovereignRouter

from fde.personas.firelayer import FireLayerPersona
from fde.personas.firefighter import FirefighterPersona
from fde.personas.kid import KidPersona

def boot_kernel():
    hc0 = HardConstraints(
        psych_forbidden_zone=(0.70, 1.00),
        runway_floor=0.05,
        time_floor=0.05,
        forbid_leverage=True,
        forbid_irreversible=True,
        forbid_new_dependencies=True,
    )

    hotswap = HardConstraintHotSwap(hc0)

    overlord = StrategicOverlord()
    guardian = LordGuardian()

    personas = [
        FireLayerPersona(),
        FirefighterPersona(),  
        KidPersona(),
        
    ]

    router = SovereignRouter(
        personas=personas,
        overlord=overlord,
        guardian=guardian,
        hc_hotswap=hotswap
    )
    return router, overlord, guardian, hotswap
