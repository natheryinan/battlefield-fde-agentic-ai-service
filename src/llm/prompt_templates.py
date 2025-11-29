from typing import List

def planning_prompt(task: str) -> str:
    return (
        "You are a forward-deployed agent on the battlefield of applied AI. "
        "Break the following mission into 3-7 concise execution steps. "
        "Respond as a numbered list.\n\n"
        f"Mission: {task}"
    )

def execution_prompt(step: str, context: str | None = None) -> str:
    base = f"Execute the following step in a concrete, useful way:\n- {step}"
    if context:
        base += f"\n\nContext:\n{context}"
    return base
