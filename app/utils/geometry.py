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

    @property
    def orthogonal_neighbours(self):
        result = Vector(self.x, self.y - 1)
        yield result
        result.x = self.x + 1
        result.y = self.y
        yield result
        result.x = self.x
        result.y = self.y + 1
        yield result
        result.x = self.x - 1
        result.y = self.y
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


def ellipse_iterator(center_x, center_y, horizontal_radius, vertical_radius):
    x = 0
    y = vertical_radius

    dx = 2 * vertical_radius * vertical_radius * x
    dy = 2 * horizontal_radius * horizontal_radius * y

    output = Vector(0, 0)

    d1 = (
        (vertical_radius * vertical_radius)
        - (horizontal_radius * horizontal_radius * vertical_radius)
        + (0.25 * horizontal_radius * horizontal_radius)
    )
    while dx < dy:
        for i in range(0, x + 1):
            output.x = i + center_x
            output.y = y + center_y
            yield output

            output.x = -i + center_x
            output.y = y + center_y
            yield output

            output.x = i + center_x
            output.y = -y + center_y
            yield output

            output.x = -i + center_x
            output.y = -y + center_y
            yield output

        if d1 < 0:
            x += 1
            dx = dx + (2 * vertical_radius * vertical_radius)
            d1 = d1 + dx + (vertical_radius * vertical_radius)
        else:
            x += 1
            y -= 1
            dx = dx + (2 * vertical_radius * vertical_radius)
            dy = dy - (2 * horizontal_radius * horizontal_radius)
            d1 = d1 + dx - dy + (vertical_radius * vertical_radius)

    d2 = (
        ((vertical_radius * vertical_radius) * ((x + 0.5) * (x + 0.5)))
        + ((horizontal_radius * horizontal_radius) * ((y - 1) * (y - 1)))
        - (horizontal_radius * horizontal_radius * vertical_radius * vertical_radius)
    )
    while y >= 0:
        for i in range(0, x + 1):
            output.x = i + center_x
            output.y = y + center_y
            yield output

            output.x = -i + center_x
            output.y = y + center_y
            yield output

            output.x = i + center_x
            output.y = -y + center_y
            yield output

            output.x = -i + center_x
            output.y = -y + center_y
            yield output

        if (d2 > 0):
            y -= 1
            dy = dy - (2 * horizontal_radius * horizontal_radius)
            d2 = d2 + (horizontal_radius * horizontal_radius) - dy
        else:
            y -= 1
            x += 1
            dx = dx + (2 * vertical_radius * vertical_radius)
            dy = dy - (2 * horizontal_radius * horizontal_radius)
            d2 = d2 + dx - dy + (horizontal_radius * horizontal_radius)
