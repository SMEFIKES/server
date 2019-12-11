import os
import re
from typing import Optional

from . import actions, tree

registry = {}
nodes_mapping = {}
LINE_PATTERN = re.compile(r'(?P<indentation>\s*)(?P<command>[^#]*)(#(?P<comment>.+))?\s*')


def get_tree(name):
    if not registry:
        load_trees()
    return registry[name]


def prepare_nodes_mapping():
    queue = [tree.Node]
    while queue:
        cls = queue.pop(0)
        queue.extend(cls.__subclasses__())
        if cls.tag:
            if cls.tag in nodes_mapping:
                raise ValueError(f'Tag "{cls.tab}" already used')

            nodes_mapping[cls.tag] = cls


def load_trees():
    if not nodes_mapping:
        prepare_nodes_mapping()

    trees_directory = os.path.join(os.path.dirname(__file__), 'trees')
    files = os.listdir(trees_directory)
    for path in files:
        tree = parse_tree(os.path.join(trees_directory, path))
        tree_name = os.path.splitext(os.path.basename(path))[0].lower()
        tree.name = tree_name
        registry[tree_name] = tree


def parse_tree(file_path):
    stack = []
    parent: Optional[tree.Node] = None

    with open(file_path, 'rt') as file:
        for line_no, raw_line in enumerate(file.readlines()):
            match = LINE_PATTERN.match(raw_line).groupdict()
            if not match['command']:
                continue

            indentation = len(match['indentation'])
            if indentation % 4:
                raise SyntaxError(f'Invalid indentation on line {line_no + 1}:\n{raw_line}')

            level = indentation // 4
            if stack and level < stack[-1][0]:
                while level <= stack[-1][0]:
                    stack.pop(-1)[1]
                parent = stack[-1][1]

            elif stack and level > stack[-1][0]:
                parent = stack[-1][1]

            node = parse_node([
                stripped for part in match['command'].split() if (stripped := part.strip())
            ])
            node.line_number = line_no + 1
            stack.append((level, node))
            if parent is not None:
                parent.add_child(node)

            if isinstance(node, tree.Decorator):
                parent = node

    if not stack:
        raise ValueError(f'Invalid behaviour tree definition in {file_path}')

    return tree.Tree(stack[0][1])


def parse_node(line):
    node = nodes_mapping[line[0]](*line[1:])
    node.parsed_arguments = line[1:]
    return node
