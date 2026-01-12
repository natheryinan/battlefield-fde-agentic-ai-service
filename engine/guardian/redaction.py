def placeholder_packet():
    return {
        "status": "PLACEHOLDER",
        "content": "",
        "note": "Time-sealed by Guardian (EARLY 王炸)"
    }

def redacted_summary(text: str):
    return {
        "status": "REDACTED",
        "content": "[REDACTED SUMMARY]",
        "note": "Sensitive content removed under HARD redaction"
    }

def apply_silent_veto(action: dict):
    kind = action.get("kind")
    if kind in {"export", "publish", "submit"}:
        return placeholder_packet()
    return {"status": "DRAFT_SAVED_ONLY"}
