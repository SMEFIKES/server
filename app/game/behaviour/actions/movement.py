import random

from app.game.actions import MoveAction
from app.game.behaviour.tree import Node, STATUS
from app.utils.constants import Directions
from app.game.pathfinding import a_star_search

from .constants import MOVE_DIRECTION, MOVEMENT_PATH, MOVEMENT_DESTINATION


class CalculateRandomDirection(Node):
    tag = 'calculate-random-direction'
    output_memory = [MOVE_DIRECTION]

    def update(self, actor, game):
        available_directions = [
            direction
            for direction in Directions.choices()
            if game.is_available_position(*(actor.position + Directions.delta(direction)))
        ]

        if not available_directions:
            actor.forget_knowledge(self.output_memory)
            return STATUS.FAILURE

        actor.remember_knowledge(self.output_memory, random.choice(available_directions))
        return STATUS.SUCCESS


class CalculatePreviousDirection(Node):
    tag = 'calculate-previous-direction'
    output_memory = [MOVE_DIRECTION]

    def update(self, actor, game):
        for action in reversed(actor.last_actions):
            if isinstance(action, MoveAction):
                actor.remember_knowledge(self.output_memory, action.direction)
                return STATUS.SUCCESS

        actor.forget_knowledge(self.output_memory)
        return STATUS.FAILURE


class CalculatePathDirection(Node):
    tag = 'calculate-path-direction'
    input_memory = [MOVEMENT_PATH]
    output_memory = [MOVE_DIRECTION]

    def update(self, actor, game):
        if not (path := actor.recall_knowledge(self.input_memory, self.input_in_blackboard)):
            actor.forget_knowledge(self.output_memory)
            return STATUS.FAILURE

        waypoint = path.pop()

        if actor.position == waypoint:
            actor.forget_knowledge(self.output_memory)
            return STATUS.SUCCESS

        if not (
            actor.position.is_orthogonal_neighbours(waypoint)
            and game.is_available_position(waypoint.x, waypoint.y)
        ):
            # actor.forget_knowledge(MOVEMENT_PATH)
            actor.forget_knowledge(self.output_memory)
            return STATUS.FAILURE

        actor.remember_knowledge(self.output_memory, Directions.from_vectors(actor.position, waypoint))


class CalculatePath(Node):
    tag = 'calculate-path'
    input_memory = [MOVEMENT_DESTINATION]
    output_memory = [MOVEMENT_PATH]

    def update(self, actor, game):
        if not (destination := actor.recall_knowledge(self.input_memory, self.input_in_blackboard)):
            actor.forget_knowledge(self.output_memory)
            return STATUS.FAILURE

        path = a_star_search(game, actor, destination)
        if not path:
            actor.forget_knowledge(self.output_memory)
            return STATUS.FAILURE

        actor.remember_knowledge(self.output_memory, path)
        return STATUS.SUCCESS


class CheckDirection(Node):
    tag = 'check-direction'
    input_memory = [MOVE_DIRECTION]

    def update(self, actor, game):
        if (direction := actor.recall_knowledge(self.input_memory, self.input_in_blackboard)) is None:
            return STATUS.FAILURE

        if game.is_available_position(*(actor.position + Directions.delta(direction))) is True:
            return STATUS.SUCCESS

        return STATUS.FAILURE


class Move(Node):
    tag = 'move'
    input_memory = [MOVE_DIRECTION]

    def update(self, actor, game):
        if (direction := actor.recall_knowledge(self.input_memory, self.input_in_blackboard)) is None:
            return STATUS.FAILURE

        game.move_actor(actor.id, direction)
        return STATUS.SUCCESS
