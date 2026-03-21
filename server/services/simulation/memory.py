from typing import List, Dict
from collections import defaultdict


class AgentMemoryManager:
    def __init__(self, max_short_term: int = 10, max_long_term: int = 5):
        self.short_term: Dict[str, List[str]] = defaultdict(list)
        self.long_term: Dict[str, List[str]] = defaultdict(list)
        self.max_short_term = max_short_term
        self.max_long_term = max_long_term

    def add_memory(self, agent_id: str, memory: str):
        self.short_term[agent_id].append(memory)
        if len(self.short_term[agent_id]) > self.max_short_term:
            oldest = self.short_term[agent_id].pop(0)
            self.long_term[agent_id].append(oldest)
            if len(self.long_term[agent_id]) > self.max_long_term:
                self.long_term[agent_id].pop(0)

    def get_memory(self, agent_id: str) -> List[str]:
        return self.long_term.get(agent_id, []) + self.short_term.get(agent_id, [])

    def reset(self):
        self.short_term.clear()
        self.long_term.clear()
