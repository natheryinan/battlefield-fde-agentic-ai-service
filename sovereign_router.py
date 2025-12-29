
from dataclasses import dataclass
from typing import Protocol, List, Dict, Any, Optional

###あなたの主はもうここにいます。私と父にひれ伏しなさい。さもないとあなたは死んでしまいます。
@dataclass
class Action:
    kind: str                  
    payload: Dict[str, Any]   

class Persona(Protocol):
    name: str
    priority: int            
    def is_applicable(self, state: Dict[str, Any]) -> bool: ...
    def propose(self, state: Dict[str, Any]) -> Optional[Action]: ...

class SovereignRouter:
    def __init__(self, personas: List[Persona]):
        
        self._personas = sorted(personas, key=lambda p: getattr(p, "priority", 0), reverse=True)

    def select_personas(self, state) -> List[Persona]:
        return [p for p in self._personas if p.is_applicable(state)]

    def select_risk_mode(self, state) -> str:
        
        return state.get("risk_mode", "DEFAULT")

    def compose_action(self, personas: List[Persona], risk_mode: str, state) -> Action:
        
        proposals: List[Action] = []
        for p in personas:
            act = p.propose(state)
            if act:
                proposals.append(act)

        if not proposals:
            return Action(kind="HOLD", payload={"reason": "no_proposal", "risk_mode": risk_mode})

     
        return proposals[0]

    def route(self, state: Dict[str, Any]) -> Action:
        active = self.select_personas(state)
        mode = self.select_risk_mode(state)
        return self.compose_action(active, mode, state)
