import math
import random


class Vector:
    __slots__ = ('x', 'y')

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return f'Vector({self.x}, {self.y})'

    def __repr__(self):
        return str(self)

    def __add__(self, other):
        return Vector(self.x + other.x, self.y + other.y)

    def __iadd__(self, other):
        self.x += other.x
        self.y += other.y
        return self

    def __sub__(self, other):
        return Vector(self.x - other.x, self.y - other.y)

    def __isub__(self, other):
        self.x -= other.x
        self.y -= other.y
        return self

    def __mul__(self, other):
        return Vector(self.x * other, self.y * other)

    def __imul__(self, other):
        self.x *= other
        self.y *= other
        return self

    def __truediv__(self, other):
        return Vector(self.x / other, self.y / other)

    def __itruediv__(self, other):
        self.x /= other
        self.y /= other
        return self

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __iter__(self):
        return iter((self.x, self.y))

    @property
    def magnitude(self):
        return math.sqrt(self.x * self.x + self.y * self.y)

    @property
    def magnitude_squared(self):
        return self.x * self.x + self.y * self.y

    @property
    def normalized(self):
        m = self.magnitude
        return Vector(self.x / m, self.y / m)

    @classmethod
    def copy(cls, other):
        return cls(other.x, other.y)

    @property
    def neighbours(self):
        result = Vector(self.x, self.y - 1)
        yield result
        result.x = self.x + 1
        yield result
        result.y = self.y
        yield result
        result.y = self.y + 1
        yield result
        result.x = self.x
        yield result
        result.x = self.x - 1
        yield result
        result.y = self.y
        yield result
        result.y = self.y - 1
        yield result

    def equals(self, x, y):
        return self.x == x and self.y == y

    def set(self, x, y):
        self.x = x
        self.y = y

    def is_orthogonal_neighbours(self, other):
        return abs(other.x - self.x) + abs(other.y - self.y) == 1


class Rectangle:
    __slots__ = ('x1', 'y1', 'x2', 'y2')

    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def __str__(self):
        return f'Rectangle({self.x1}, {self.y1}, {self.x2}, {self.y2})'

    def __repr__(self):
        return str(self)

    @property
    def width(self):
        return self.x2 - self.x1

    @property
    def height(self):
        return self.y2 - self.y1

    def __iter__(self):
        result = Vector(0, self.y1)
        for coord in range(self.x1, self.x2):
            result.x = coord
            yield result

        result.x = self.x2
        for coord in range(self.y1, self.y2):
            result.y = coord
            yield result

        result.y = self.y2
        for coord in range(self.x2, self.x1, -1):
            result.x = coord
            yield result

        result.x = self.x1
        for coord in range(self.y2, self.y1, -1):
            result.y = coord
            yield result

    def overlaps(self, other):
        left = max(self.x1, other.x1)
        right = min(self.x2, other.x2)
        top = max(self.y1, other.y1)
        bottom = min(self.y2, other.y2)
        return left <= right and top <= bottom

    def intersection(self, other):
        left = max(self.x1, other.x1)
        right = min(self.x2, other.x2)
        top = max(self.y1, other.y1)
        bottom = min(self.y2, other.y2)
        if left <= right and top <= bottom:
            return Rectangle(left, top, right, bottom)

    def random_point(self, padding=0):
        side = random.randint(1, 4)
        if side == 1:
            x1, y1, x2, y2 = self.x1, self.y1, self.x2, self.y1
        elif side == 2:
            x1, y1, x2, y2 = self.x2, self.y1, self.x2, self.y2
        elif side == 3:
            x1, y1, x2, y2 = self.x1, self.y2, self.x2, self.y2
        else:
            x1, y1, x2, y2 = self.x1, self.y1, self.x1, self.y2

        begin = Vector(x1, y1)
        end = Vector(x2, y2)
        normal = (end - begin).normalized

        result = begin + normal * padding + normal * random.randint(0, (end - begin).magnitude - padding * 2)
        result.x = int(result.x)
        result.y = int(result.y)
        return result
