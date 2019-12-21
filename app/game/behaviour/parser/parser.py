import os

from lark import Lark, Transformer, Token
from lark.indenter import Indenter

from ..tree import Node, Composite, Decorator
from .. import actions


class TreeIndenter(Indenter):
    NL_type = '_NL'
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 4


class TreeTransformer(Transformer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.nodes_mapping = self.get_nodes_mapping()

    def get_nodes_mapping(self):
        mapping = {}
        queue = [Node]

        while queue:
            cls = queue.pop(0)
            queue.extend(cls.__subclasses__())
            if cls.tag:
                if cls.tag in mapping:
                    raise ValueError(f'Tag "{cls.tab}" already used')

                mapping[cls.tag] = cls

        return mapping

    def composite(self, children):
        node_token = children[0]
        cls = self.nodes_mapping[node_token.value]
        if not issubclass(cls, Composite):
            raise ValueError(f'{node_token.value} is not composite')

        instance = cls(children[1:])
        try:
            instance.line_number = node_token.line
        except AttributeError:
            pass
        return instance

    def decorator(self, children):
        node_token = children[0]
        cls = self.nodes_mapping[node_token.value]
        if not issubclass(cls, Decorator):
            raise ValueError(f'{node_token.value} is not decorator')

        instance = cls(children[1])
        try:
            instance.line_number = node_token.line
        except AttributeError:
            pass
        return instance

    def node(self, children):
        node_token = children[0]
        cls = self.nodes_mapping[node_token.value]
        arguments = None
        input_in_blackboard = True
        input_memory = None
        output_memory = None
        comment = None

        for child in children[1:]:
            if isinstance(child, Token):
                if child.type == 'COMMENT':
                    comment = child.value

            else:
                if child.data == 'arguments':
                    arguments = [token.value for token in child.children]

                elif child.data == 'input_memory':
                    if child.children[0].type == 'SELF':
                        input_in_blackboard = False
                        path = child.children[1:]
                    else:
                        path = child.children

                    input_memory = [token.value for token in path]

                elif child.data == 'output_memory':
                    output_memory = [token.value for token in child.children]

        if arguments:
            instance = cls(*arguments)
            instance.parsed_arguments = arguments
        else:
            instance = cls()

        instance.input_in_blackboard = input_in_blackboard

        if input_memory:
            instance.input_memory = input_memory

        if output_memory:
            instance.output_memory = output_memory

        if comment:
            instance.comment = comment

        try:
            instance.line_number = node_token.line
        except AttributeError:
            pass

        return instance


def get_parser():
    path_to_grammar = os.path.join(os.path.dirname(__file__), 'grammar.lark')
    with open(path_to_grammar, 'rt') as file:
        return Lark(
            file, parser='lalr', propagate_positions=True,
            postlex=TreeIndenter(), transformer=TreeTransformer()
        )
