import random
import operator

from .tree import Node, STATUS
from app.utils.geometry import Vector
from ..actions import MoveAction
from ...utils.constants import Directions


class InspectNeighbours(Node):
    tag = 'inspect-neighbours'

    def update(self, actor, game):
        neighbour_tiles = [
            Vector.copy(vec)
            for vec in actor.position.neighbours
            if actor.position.is_orthogonal_neighbours(vec) and vec in game.map
        ]
        neighbours = []
        for other in game.creatures.values():
            if other.position in neighbour_tiles:
                neighbours.append(other)
                if len(neighbours) == 4:
                    break

        if not neighbours:
            return STATUS.FAILURE

        actor.blackboard['neighbours'] = neighbours
        return STATUS.SUCCESS


class SelectNeighbour(Node):
    tag = 'select-neighbour'

    def __init__(self, kind='any'):
        super().__init__()
        self.kind = kind

    def update(self, actor, game):
        neighbours = actor.blackboard.get('neighbours')
        if neighbours is None:
            return STATUS.FAILURE

        if self.kind == 'enemy':
            neighbours = [neighbour for neighbour in neighbours if neighbour.group != actor.group]
        elif self.kind == 'friend':
            neighbours = [neighbour for neighbour in neighbours if neighbour.group == actor.group]

        if not neighbours:
            return STATUS.FAILURE

        actor.blackboard['selected_actor'] = random.choice(neighbours)
        return STATUS.SUCCESS


class SelectInspected(Node):
    tag = 'select-inspected'

    def update(self, actor, game):
        if (inspected_actor := actor.blackboard.get('inspected_actor')) is Node:
            return STATUS.FAILURE

        actor.blackboard['selected_actor'] = inspected_actor
        return STATUS.SUCCESS


class PrepareToBattle(Node):
    tag = 'prepare-to-battle'

    def __init__(self, kind):
        super().__init__()
        self.preparing_type = kind

    def update(self, actor, game):
        if actor.prepared_to_battle and actor.last_action.type == self.preparing_type:
            return STATUS.SUCCESS

        game.prepare_to_battle(
            actor.id, self.preparing_type, random.randint(1, max(1, actor.stamina))
        )
        return STATUS.SUCCESS


class CalculateAttackDirection(Node):
    tag = 'calculate-attack-direction'

    def update(self, actor, game):
        target = actor.blackboard.get('selected_actor')
        if target is None:
            return STATUS.FAILURE

        actor.blackboard['move_direction'] = Directions.from_vectors(actor.position, target.position)
        return STATUS.SUCCESS


class CalculateFleeDirection(Node):
    tag = 'calculate-flee-direction'

    def update(self, actor, game):
        threat = actor.blackboard.get('selected_actor')
        if threat is None:
            return STATUS.FAILURE

        direction_to_attacker = Directions.from_vectors(actor.position, threat.position)
        available_directions = [
            direction
            for direction in Directions.choices()
            if (
                direction != direction_to_attacker
                and game.is_available_position(*(actor.position + Directions.delta(direction))) is True
            )
        ]
        if not available_directions:
            return STATUS.FAILURE

        actor.blackboard['move_direction'] = random.choice(available_directions)
        return STATUS.SUCCESS


class CalculateRandomDirection(Node):
    tag = 'calculate-random-direction'

    def update(self, actor, game):
        available_directions = [
            direction
            for direction in Directions.choices()
            if game.is_available_position(*(actor.position + Directions.delta(direction)))
        ]

        if not available_directions:
            return STATUS.FAILURE

        actor.blackboard['move_direction'] = random.choice(available_directions)
        return STATUS.SUCCESS


class CalculatePreviousDirection(Node):
    tag = 'calculate-previous-direction'

    def update(self, actor, game):
        for action in reversed(actor.last_actions):
            if isinstance(action, MoveAction):
                actor.blackboard['move_direction'] = action.direction
                return STATUS.SUCCESS

        return STATUS.FAILURE


class CheckDirection(Node):
    tag = 'check-direction'

    def update(self, actor, game):
        direction = actor.blackboard.get('move_direction')
        if direction is None:
            return STATUS.FAILURE

        if game.is_available_position(*(actor.position + Directions.delta(direction))) is True:
            return STATUS.SUCCESS

        return STATUS.FAILURE


class Move(Node):
    tag = 'move'

    def update(self, actor, game):
        direction = actor.blackboard.get('move_direction')
        if direction is None:
            return STATUS.FAILURE

        game.move_creature(actor.id, direction)
        return STATUS.SUCCESS


class Wait(Node):
    tag = 'wait'

    def update(self, actor, game):
        return STATUS.SUCCESS


class Inspect(Node):
    tag = 'inspect'

    ATTRIBUTES_FOR_PERCENT = {'hp', 'stamina'}
    OPERATORS = {
        '<': operator.lt,
        '<=': operator.le,
        '==': operator.eq,
        'is': operator.eq,
        '!=': operator.ne,
        'not': operator.ne,
        '>=': operator.ge,
        '>': operator.gt
    }

    def __init__(self, target, attribute, operator, operand):
        if operator not in self.OPERATORS:
            raise ValueError(f'Invalid operator for inspect: {operator}')

        if '%' in operand and attribute not in self.ATTRIBUTES_FOR_PERCENT:
            raise ValueError(f'Invalid attribute for inspect: {attribute}')

        super().__init__()
        self.target = target
        self.attribute = attribute
        self.operator = operator
        self.operand = operand

    def calculate_operand(self, actor):
        if self.operand == 'true':
            return True

        if self.operand == 'false':
            return False

        if '%' not in self.operand:
            return float(self.operand)

        max_value = getattr(actor, f'max_{self.attribute}')
        return max_value * 0.01 * float(self.operand.rstrip('%'))

    def update(self, actor, game):
        succeed_on_any = True
        if self.target in ('any', 'all'):
            actors = actor.blackboard.get('neighbours')
            if self.target == 'all':
                succeed_on_any = False

        else:
            if self.target == 'self':
                actors = [actor]
            else:
                actors = [actor.blackboard.get(self.target)]

        if not actors:
            return STATUS.FAILURE

        if succeed_on_any:
            for checked_actor in actors:
                value = getattr(checked_actor, self.attribute)
                check_result = self.OPERATORS[self.operator](value, self.calculate_operand(checked_actor))
                if check_result:
                    actor.blackboard['inspected_actor'] = checked_actor
                    return STATUS.SUCCESS

                return STATUS.FAILURE

        for checked_actor in actors:
            value = getattr(checked_actor, self.attribute)
            if not self.OPERATORS[self.operator](value, self.calculate_operand(checked_actor)):
                return STATUS.FAILURE

            return STATUS.SUCCESS


class Include(Node):
    tag = 'include'

    def __init__(self, subtree_name):
        super().__init__()
        self.subtree_name = subtree_name

    def update(self, actor, game):
        from .loader import get_tree
        return get_tree(self.subtree_name).update(actor, game)


class Random(Node):
    tag = 'random'

    def __init__(self, probability):
        super().__init__()
        self.probability = float(probability)

    def update(self, actor, game):
        return STATUS.SUCCESS if random.random() < self.probability else STATUS.FAILURE
