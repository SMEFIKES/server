from __future__ import annotations

import uuid
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .actions import BaseAction
from app.utils.geometry import Vector


class Creature:
    def __init__(self, name, kind):
        self.id = uuid.uuid4().hex
        self.name = name
        self.kind = kind
        self.group = 0
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
        self.blackboard = {}

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

        if isinstance(action.time_cost, tuple):
            time_to_next_action = random.randint(*action.time_cost)
        else:
            time_to_next_action = action.time_cost

        self.next_action_time = action.occurrence_time + time_to_next_action
        self.stamina -= 2 * self.actions_in_round * action.stamina_cost

        self.last_actions.append(action)
        if len(self.last_actions) > 5:
            self.last_actions.pop(0)

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

