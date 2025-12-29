# fde/kernel/boot.py

from fde.kernel.hard_constraints import HardConstraints
from fde.kernel.hotswap import HardConstraintHotSwap
from fde.kernel.sovereign_router import SovereignRouter
from fde.kernel.overlord import StrategicOverlord, LordGuardian

from fde.kernel.params import GuardianParams  # 你之前建的参数容器（若还没建就先建）
from fde.personas.firelayer import FireLayerPersona
from fde.personas.firefighter import FirefighterPersona
from fde.personas.kid import KidPersona
from fde.personas.guardian_trading import GuardianTradingPersona

from fde.personas.alpha_silent import AlphaSilentPersona
from fde.personas.alpha_probe import AlphaProbePersona
from fde.personas.alpha_strike import AlphaStrikePersona


def boot_kernel(parse_control: str = "SAFE"):
    # 1) Hard constraints + hotswap（Router 这一版不调用 hardgate，但保留 wiring 不冲突）
    hc0 = HardConstraints(
        psych_forbidden_zone=(0.70, 1.00),
        runway_floor=0.05,
        time_floor=0.05,
        forbid_leverage=True,
        forbid_irreversible=True,
        forbid_new_dependencies=True,
    )
    hotswap = HardConstraintHotSwap(hc0)

    # 2) Overlord / Guardian（Router 需要这俩对象）
    overlord = StrategicOverlord()
    guardian = LordGuardian()

    # 3) Params（宏大值 / 变量都放 params 文件里，不散落）
    guardian_params = GuardianParams(
        notional_max=1e12,  # 你要更大就改这里
        base_size=1.0,
    )

    # 4) Personas 注册（Alpha 多形态：多个 persona 实例）
    personas = [
        FireLayerPersona(),
        FirefighterPersona(),  # stays invisible (router decides FIREFIGHT)
        KidPersona(),
        GuardianTradingPersona(guardian_params),

        AlphaSilentPersona(),
        AlphaProbePersona(),
        AlphaStrikePersona(),
    ]

    # 5) Router（对齐你最新 SovereignRouter.py 的签名）
    router = SovereignRouter(
        personas=personas,
        overlord=overlord,
        guardian=guardian,
        hc_hotswap=hotswap,
        parse_control=parse_control,
    )

    return router
