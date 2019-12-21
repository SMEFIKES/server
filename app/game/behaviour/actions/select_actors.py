import random

from app.game.behaviour.tree import Node, STATUS
from app.utils.geometry import Vector
from .constants import FOUND_ACTORS, SELECTED_ACTOR, INSPECTED_ACTOR


class FindNeighbours(Node):
    tag = 'find-neighbours'
    output_memory = [FOUND_ACTORS]

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
            actor.forget_knowledge(self.output_memory)
            return STATUS.FAILURE

        actor.remember_knowledge(self.output_memory, neighbours)
        return STATUS.SUCCESS


class FindAround(Node):
    tag = 'find-around'
    output_memory = [FOUND_ACTORS]

    def __init__(self, horizontal_radius, vertical_radius=None):
        super().__init__()
        self.horizontal_radius = horizontal_radius
        self.vertical_radius = vertical_radius or horizontal_radius

    def update(self, actor, game):
        found_actors = []
        pos = Vector(0, 0)

        for x in range(actor.position.x - self.horizontal_radius, actor.position.y + self.horizontal_radius):
            for y in range(actor.position.y - self.vertical_radius, actor.position.y + self.vertical_radius):
                pos.x = x
                pos.y = y
                if found := game.get_actor_at(pos):
                    found_actors.append(found)

        if not found_actors:
            actor.forget_knowledge(self.output_memory)
            return STATUS.FAILURE

        actor.remember_knowledge(self.output_memory, found_actors)
        return STATUS.SUCCESS


class SortActors(Node):
    tag = 'sort-actors'
    input_memory = [FOUND_ACTORS]

    def __init__(self, sorting_key: str):
        super().__init__()
        self.sorting_key = sorting_key

    def update(self, actor, game):
        if not (actors := actor.recall_knowledge(self.input_memory, self.input_in_blackboard)):
            return STATUS.FAILURE

        reverse = False
        sorting_key = self.sorting_key
        if self.sorting_key.startswith('-'):
            sorting_key = self.sorting_key[1:]
            reverse = True

        if sorting_key == 'distance':
            def sorting_function(current):
                return (current.position - actor.position).magnitude_squared

        else:
            def sorting_function(current):
                return getattr(current, sorting_key)

        actors.sort(key=sorting_function, reverse=reverse)
        return STATUS.SUCCESS


class FilterActors(Node):
    tag = 'filter-actors'
    input_memory = [FOUND_ACTORS]
    output_memory = [FOUND_ACTORS]

    def __init__(self, kind='any'):
        super().__init__()
        self.kind = kind

    def update(self, actor, game):
        if not (actors := actor.recall_knowledge(self.input_memory, self.input_in_blackboard)):
            return STATUS.FAILURE

        if self.kind == 'enemy':
            actors = [candidate for candidate in actors if candidate.faction != actor.faction]
        elif self.kind == 'friend':
            actors = [candidate for candidate in actors if candidate.faction == actor.faction]

        if not actors:
            actor.forget_knowledge(self.output_memory)
            return STATUS.FAILURE

        actor.remember_knowledge(self.output_memory, actors)
        return STATUS.SUCCESS


class SelectFirst(Node):
    tag = 'select-first'
    input_memory = [FOUND_ACTORS]
    output_memory = [SELECTED_ACTOR]

    def update(self, actor, game):
        if not (candidates := actor.recall_knowledge(self.input_memory, self.input_in_blackboard)):
            return STATUS.FAILURE

        actor.remember_knowledge(self.output_memory, candidates[0])
        return STATUS.SUCCESS


class SelectAny(Node):
    tag = 'select-any'
    input_memory = [FOUND_ACTORS]
    output_memory = [SELECTED_ACTOR]

    def update(self, actor, game):
        if not (candidates := actor.recall_knowledge(self.input_memory, self.input_in_blackboard)):
            return STATUS.FAILURE

        actor.remember_knowledge(self.output_memory, random.choice(candidates))
        return STATUS.SUCCESS


class SelectInspected(Node):
    tag = 'select-inspected'
    input_memory = [INSPECTED_ACTOR]
    output_memory = [SELECTED_ACTOR]

    def update(self, actor, game):
        if (inspected_actor := actor.recall_knowledge(self.input_memory, self.input_in_blackboard)) is Node:
            actor.forget_knowledge(self.output_memory)
            return STATUS.FAILURE

        actor.remember_knowledge(self.output_memory, inspected_actor)
        return STATUS.SUCCESS
