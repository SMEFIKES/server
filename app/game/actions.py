from dataclasses import dataclass
from enum import IntEnum, auto
from typing import Optional, Union

from app.game.creatures import Creature
from app.game.worldgen import Tile
from app.server.serializers import MoveResponseSerializer, AttackResponseSerializer, PrepareToBattleResponseSerializer
from app.utils.geometry import Vector


@dataclass
class BlockedMovement:
    class REASONS(IntEnum):
        OBSTACLE = auto()
        CREATURE = auto()
        OUT = auto()

    reason: REASONS
    object: Union[Creature, Tile, None]


@dataclass
class BaseAction:
    time_cost = (1, 3)
    stamina_cost = 1

    occurrence_time: int
    actor: Creature

    serializer = None

    def __post_init__(self):
        self.actor.push_action(self)

    @property
    def serialized(self):
        return self.serializer().dump(self)


@dataclass
class MoveAction(BaseAction):
    success: bool
    previous_position: Optional[Vector]
    direction: str

    serializer = MoveResponseSerializer


@dataclass
class AttackAction(BaseAction):
    defender: Creature
    success: bool
    defender_alive: bool
    damage: int

    serializer = AttackResponseSerializer


@dataclass
class PrepareToBattleAction(BaseAction):
    type: str
    energy: int

    serializer = PrepareToBattleResponseSerializer
