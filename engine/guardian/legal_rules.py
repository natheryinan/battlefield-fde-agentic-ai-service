from .types import Decision, Channel

HIGH_IMPACT_KINDS = {
    "export", "finalize", "publish", "submit", "public_reference"
}

EXTERNAL_CHANNELS = {
    Channel.EMAIL.value,
    Channel.CLOUD.value,
    Channel.PUBLIC.value,
}

def evaluate_legal_rules(action: dict, ctx: dict) -> Decision:
    now = ctx["now"]

    # Alpha override: one-shot, irreversible
    if ctx.get("alpha_release_executed") is True:
        return Decision.ALLOW_EXECUTE_ONCE

    # EARLY 王炸（时间未到，一律拦大招）
    if ctx.get("early_wangzha") is True and now < ctx["time_seal_until"]:
        if action.get("high_impact") or ctx.get("channel") in EXTERNAL_CHANNELS:
            return Decision.DENY_SILENT
        return Decision.ALLOW_INTERNAL_ONLY

    # Hard veto（明确否决）
    if action.get("hard_veto") is True:
        return Decision.DENY_SILENT

    return Decision.ALLOW_INTERNAL_ONLY
