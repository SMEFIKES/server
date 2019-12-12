import random

from app.game.behaviour.tree import Node, STATUS
from app.utils.geometry import Vector, ellipse_iterator
from .constants import FOUND_ACTORS, SELECTED_ACTOR, INSPECTED_ACTOR


class FindNeighbours(Node):
    tag = 'find-neighbours'

    def update(self, actor, game):
        neighbour_tiles = [
            Vector.copy(vec)
            for vec in actor.position.orthogonal_neighbours
            if vec in game.map
        ]
        neighbours = [
            neighbour
            for tile in neighbour_tiles
            if (neighbour := game.get_actor_at(tile)) is not None
        ]

        if not neighbours:
            actor.forget_knowledge(FOUND_ACTORS)
            return STATUS.FAILURE

        actor.remember_knowledge(FOUND_ACTORS, neighbours)
        return STATUS.SUCCESS


class FindAround(Node):
    tag = 'find-around'

    def __init__(self, horizontal_radius, vertical_radius=None):
        super().__init__()
        self.horizontal_radius = horizontal_radius
        self.vertical_radius = vertical_radius or horizontal_radius

    def update(self, actor, game):
        found_actors = [
            found
            for position in ellipse_iterator(
                actor.position.x, actor.position.y, self.horizontal_radius, self.vertical_radius
            )
            if (found := game.get_actor_at(position))
        ]

        if not found_actors:
            actor.forget_knowledge(FOUND_ACTORS)
            return STATUS.FAILURE

        actor.remember_knowledge(FOUND_ACTORS, found_actors)
        return STATUS.SUCCESS


class SelectOne(Node):
    tag = 'select-one'

    def __init__(self, kind='any'):
        super().__init__()
        self.kind = kind

    def update(self, actor, game):
        if not (candidates := actor.recall_knowledge(FOUND_ACTORS)):
            return STATUS.FAILURE

        if self.kind == 'enemy':
            candidates = [neighbour for neighbour in candidates if neighbour.faction != actor.faction]
        elif self.kind == 'friend':
            candidates = [neighbour for neighbour in candidates if neighbour.faction == actor.faction]

        if not candidates:
            actor.forget_knowledge(SELECTED_ACTOR)
            return STATUS.FAILURE

        actor.remember_knowledge(SELECTED_ACTOR, random.choice(candidates))
        return STATUS.SUCCESS


class SelectInspected(Node):
    tag = 'select-inspected'

    def update(self, actor, game):
        if (inspected_actor := actor.recall_knowledge(INSPECTED_ACTOR)) is Node:
            actor.forget_knowledge(SELECTED_ACTOR)
            return STATUS.FAILURE

        actor.remember_knowledge(SELECTED_ACTOR, inspected_actor)
        return STATUS.SUCCESS
