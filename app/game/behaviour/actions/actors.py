import random
import operator

from app.utils.constants import Directions
from ..tree import Node, STATUS

from .constants import MOVE_DIRECTION, SELECTED_ACTOR, INSPECTED_ACTOR, FOUND_ACTORS


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
    input_memory = [SELECTED_ACTOR]
    output_memory = [MOVE_DIRECTION]

    def update(self, actor, game):
        target = actor.recall_knowledge(self.input_memory, self.input_in_blackboard)
        if target is None:
            return STATUS.FAILURE

        actor.remember_knowledge(
            self.output_memory, Directions.from_vectors(actor.position, target.position)
        )
        return STATUS.SUCCESS


class CalculateFleeDirection(Node):
    tag = 'calculate-flee-direction'
    input_memory = [SELECTED_ACTOR]
    output_memory = [MOVE_DIRECTION]

    def update(self, actor, game):
        if (threat := actor.recall_knowledge(self.input_memory, self.input_in_blackboard)) is None:
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

        actor.remember_knowledge(self.output_memory, random.choice(available_directions))
        return STATUS.SUCCESS


class Wait(Node):
    tag = 'wait'

    def update(self, actor, game):
        return STATUS.SUCCESS


class Inspect(Node):
    tag = 'inspect'
    input_memory = [FOUND_ACTORS]
    output_memory = [INSPECTED_ACTOR]

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

        if self.target == 'self':
            actors = [actor]

        else:
            actors = actor.recall_knowledge(self.input_memory, self.input_in_blackboard)
            if self.target == 'all':
                succeed_on_any = False

        if not actors:
            return STATUS.FAILURE

        if succeed_on_any:
            for checked_actor in actors:
                value = getattr(checked_actor, self.attribute)
                check_result = self.OPERATORS[self.operator](value, self.calculate_operand(checked_actor))
                if check_result:
                    actor.remember_knowledge(self.output_memory, checked_actor)
                    return STATUS.SUCCESS

                actor.forget_knowledge(self.output_memory)
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
        from ..loader import get_tree
        return get_tree(self.subtree_name).update(actor, game)


class Random(Node):
    tag = 'random'

    def __init__(self, probability):
        super().__init__()
        self.probability = float(probability)

    def update(self, actor, game):
        return STATUS.SUCCESS if random.random() < self.probability else STATUS.FAILURE
