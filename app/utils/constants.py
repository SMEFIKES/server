from app.utils.common import Choices
from .geometry import Vector


class Directions(Choices):
    up = 'up'
    right = 'right'
    down = 'down'
    left = 'left'

    @classmethod
    def delta(cls, direction):
        delta = Vector(0, 0)
        if direction == cls.up:
            delta.set(0, -1)
        elif direction == cls.right:
            delta.set(1, 0)
        elif direction == cls.down:
            delta.set(0, 1)
        elif direction == cls.left:
            delta.set(-1, 0)
        return delta

    @classmethod
    def from_vectors(cls, origin, destination):
        if origin.y == destination.y:
            return cls.left if destination.x < origin.x else cls.right
        return cls.up  if destination.y < origin.y else cls.down
