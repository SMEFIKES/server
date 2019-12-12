from __future__ import annotations

from enum import IntEnum, auto
from typing import List

from app.game.handler import GameHandler
from ..actors import Actor


class STATUS(IntEnum):
    SUCCESS = auto()
    FAILURE = auto()
    RUNNING = auto()


class Tree:
    def __init__(self, root: Node):
        self.name = None
        self.root = root

    def update(self, actor: Actor, game: GameHandler) -> STATUS:
        return self.root.process_update(actor, game)

    def _print_node(self, level, node):
        rows = [f'{("  " * level)}{node!r}']
        if isinstance(node, Composite):
            for child in node.children:
                rows.extend(self._print_node(level + 1, child))

        elif isinstance(node, Decorator):
            rows.extend(self._print_node(level + 1, node.child))

        return rows

    def print(self):
        print('\n'.join(self._print_node(0, self.root)))

    def traverse(self):
        nodes = []
        node = self.root
        while node:
            nodes.append(node)
            if isinstance(node, Composite):
                node = node.last_child
            elif isinstance(node, Decorator):
                node = node.child
            else:
                node = None
        return nodes


class Node:
    tag = ''
    
    def __init__(self):
        self.line_number = 0
        self.parsed_arguments = None
        self.last_actor = None
        self.last_status = None

    def __repr__(self):
        return (
            f'[{self.line_number}] '
            f'{self.__class__.__name__}'
            f'({", ".join(self.parsed_arguments) if self.parsed_arguments else ""})'
        )

    @property
    def root(self):
        node = self
        while node.parent is not None:
            node = node.parent
        return node

    def process_update(self, actor: Actor, game: GameHandler) -> STATUS:
        status = self.update(actor, game)
        self.last_actor = actor
        self.last_status = status
        return status

    def update(self, actor: Actor, game: GameHandler) -> STATUS:
        return STATUS.SUCCESS

    def add_child(self, child: Node):
        raise ValueError('Leaf node can not have a children')


class Composite(Node):
    def __init__(self, children: List[Node] = None):
        super().__init__()
        self.children = children if children is not None else []
        self.last_child = None

    def add_child(self, child):
        self.children.append(child)


class Sequence(Composite):
    tag = '-->'

    def update(self, actor, game):
        for child in self.children:
            self.last_child = child
            if child.process_update(actor, game) == STATUS.FAILURE:
                return STATUS.FAILURE
        return STATUS.SUCCESS


class Selector(Composite):
    tag = '-?-'

    def update(self, actor, game):
        for child in self.children:
            self.last_child = child
            if child.process_update(actor, game) == STATUS.SUCCESS:
                return STATUS.SUCCESS
        return STATUS.FAILURE


class Decorator(Node):
    def __init__(self, child: Node = None):
        super().__init__()
        self.child = child

    def add_child(self, child):
        if self.child is not None:
            raise ValueError(f'{self.__class__.__name__} can have only one child')
        self.child = child


class Inverted(Decorator):
    tag = 'inverted'

    def update(self, actor, game):
        status = self.child.process_update(actor, game)
        if status == STATUS.SUCCESS:
            return STATUS.FAILURE

        if status == STATUS.FAILURE:
            return STATUS.SUCCESS

        return status


class Converted(Decorator):
    tag = 'converted'

    def __init__(self, input_status: STATUS, output_status: STATUS, child: Node = None):
        super().__init__(child)
        self.input_status = input_status
        self.output_status = output_status

    def update(self, actor, game):
        status = self.child.process_update(actor, game)

        if status == self.input_status:
            return self.output_status

        return status


class Anyway(Decorator):
    tag = 'anyway'

    def update(self, actor, game):
        self.child.process_update(actor, game)
        return STATUS.SUCCESS
