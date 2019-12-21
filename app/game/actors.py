from __future__ import annotations

import uuid
import random
from typing import TYPE_CHECKING, Dict, List

if TYPE_CHECKING:
    from .actions import BaseAction
from app.utils.geometry import Vector


class Actor:
    def __init__(self, name, kind):
        self.id = uuid.uuid4().hex
        self.name = name
        self.kind = kind
        self.faction = 0
        self.position = Vector(0, 0)
        self.next_action_time = 0
        self.last_action_time = 0
        self.max_stamina = 12
        self.stamina = 12
        self.energy_regeneration = 1
        self.attack_energy = 0
        self.defence_energy = 0
        self.max_hp = 20
        self.hp = 20
        self.actions_in_round = 0
        self.exhausted = False
        self.last_actions = []
        self._blackboard = {}

    def get_attack(self):
        return max(1, self.attack_energy)

    def get_defence(self):
        return self.defence_energy

    def handle_exhausting(self, time):
        if self.stamina < 0:
            self.exhausted = True
            self.next_action_time = time - (self.stamina * 10)
        elif self.exhausted and self.next_action_time <= time:
            self.exhausted = False

    def push_action(self, action: BaseAction):
        self.actions_in_round += 1
        self.last_action_time = action.occurrence_time

        self.stamina -= 2 * self.actions_in_round * action.stamina_cost

        self.last_actions.append(action)
        if len(self.last_actions) > 5:
            self.last_actions.pop(0)

        if not self.is_fast:
            if isinstance(action.time_cost, tuple):
                time_to_next_action = random.randint(*action.time_cost)
            else:
                time_to_next_action = action.time_cost

            self.next_action_time = action.occurrence_time + time_to_next_action

    @property
    def is_fast(self):
        return self.kind == 'player'

    @property
    def last_action(self):
        if self.last_actions:
            return self.last_actions[-1]

    @property
    def prepared_to_battle(self):
        from .actions import PrepareToBattleAction
        return isinstance(self.last_action, PrepareToBattleAction) and max(self.defence_energy, self.attack_energy) > 0

    @property
    def prepared_to_attack(self):
        return self.prepared_to_battle and self.last_action.type == 'attack'

    @property
    def prepared_to_defence(self):
        return self.prepared_to_battle and self.last_action.type == 'defence'

    @property
    def acted(self):
        return self.actions_in_round > 0

    def recall_knowledge(self, path: List[str], in_blackboard):
        if in_blackboard:
            data = self._blackboard
            for part in path:
                data = data.get(part)
                if part is None:
                    return

            return data

        obj = self
        for part in path:
            obj = getattr(obj, part, None)
            if obj is None:
                return

        return obj

    def remember_knowledge(self, path: List[str], value):
        if len(path) == 1:
            self._blackboard[path[0]] = value
            return

        data = self._blackboard
        for part in path[:-1]:
            data = data.setdefault(part, {})

        data[path[-1]] = value

    def forget_knowledge(self, path: List[str]):
        if len(path) == 1:
            self._blackboard.pop(path[0], None)
            return

        data = self._blackboard
        for part in path[:-1]:
            data = data.get(part)
            if data is None:
                return

        data.pop(path[-1], None)


class Squad(Actor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.brawlers: Dict[str, Actor] = {}
