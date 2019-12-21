import os

from .parser.parser import get_parser
from .tree import Tree

registry = {}


def get_tree(name):
    if not registry:
        load_trees()
    return registry[name]


def load_trees():
    trees_directory = os.path.join(os.path.dirname(__file__), 'trees')
    files = os.listdir(trees_directory)
    parser = get_parser()

    for path in files:
        with open(os.path.join(trees_directory, path), 'rt') as file:
            tree_root = parser.parse(file.read())

        tree = Tree(tree_root)
        tree_name = os.path.splitext(os.path.basename(path))[0].lower()
        tree.name = tree_name
        registry[tree_name] = tree
