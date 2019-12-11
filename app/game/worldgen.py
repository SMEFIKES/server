import random
from enum import IntEnum, auto
from typing import Union

from ..utils.geometry import Vector, Rectangle


class Canvas:
    __slots__ = ('canvas', 'width', 'height')

    def __init__(self, width, height, default: Union[bool, 'Tile'] = False):
        self.width = width
        self.height = height
        if callable(default):
            self.canvas = [default() for _ in range(width * height)]
        else:
            self.canvas = [default] * (width * height)

    def __getitem__(self, item):
        return self.canvas[item[1] * self.width + item[0]]

    def __setitem__(self, key, value):
        self.canvas[key[1] * self.width + key[0]] = value

    def __contains__(self, vector):
        return 0 <= vector.x < self.width and 0 <= vector.y < self.height

    @classmethod
    def from_data(cls, data):
        width = len(data)
        height = len(data[0])
        instance = cls(width, height)
        for x in range(width):
            for y in range(height):
                instance.canvas[y * width + x] = data[x][y]
        return instance

    def to_string(self, symbol, empty_symbol=' '):
        return '\n'.join(
            ''.join(symbol if self.canvas[y * self.width + x] else empty_symbol for x in range(self.width))
            for y in range(self.height)
        )

    def to_string_tileset(self, tileset):
        return '\n'.join(
            ''.join(tileset[self.canvas[y * self.width + x]] for x in range(self.width))
            for y in range(self.height)
        )

    def combine(self, other, x, y):
        for cx in range(other.width):
            for cy in range(other.height):
                value = other[cx, cy]
                if value:
                    self.canvas[(y + cy) * self.width + x + cx] = value


def automata(width, height, start_prob=0.5, birth_threshold=3, survival_threshold=5, iterations=4):
    canvas = Canvas(width, height, lambda: random.random() < start_prob)

    for _ in range(iterations):
        for x in range(width):
            for y in range(height):
                count = 0
                for point in Vector(x, y).neighbours:
                    if point.x < 0 or point.y < 0 or point.x >= width or point.y >= height:
                        continue
                    if canvas[point.x][point.y]:
                        count += 1
                threshold = survival_threshold if canvas[x, y] else birth_threshold
                canvas[x, y] = count >= threshold

    return canvas


def plain(width, height, padding=0):
    if not padding:
        return Canvas(width, height, True)

    canvas = Canvas(width + padding * 2, height + padding * 2)
    for x in range(padding, padding + width):
        for y in range(padding, padding + height):
            canvas[x, y] = True

    return canvas


def walk(width, height, max_steps=None, walks=5, padding=0):
    canvas = Canvas(width + padding * 2, height + padding * 2)
    origin_x = width // 2 + padding
    origin_y = height // 2 + padding
    canvas[origin_x, origin_y] = True
    if max_steps is None:
        max_steps = max(origin_x, origin_y)

    for _ in range(walks):
        x = origin_x
        y = origin_y
        for _ in range(max_steps):
            dx = random.randint(-1, 1)
            if dx == 0:
                dy = -1 if random.random() < 0.5 else 1
            else:
                dy = 0
            x += dx
            y += dy
            if x < 0 or y < 0 or x >= width or y >= height:
                break
            canvas[x, y] = True

    return canvas


def fill(width, height, falloff=1, padding=0):
    canvas = Canvas(width + padding * 2, height + padding * 2)
    origin_x = width // 2 + padding
    origin_y = height // 2 + padding
    canvas[origin_x, origin_y] = True
    frontier = [(origin_x, origin_y, 0)]
    visited = {(origin_x, origin_y)}
    max_dist = origin_x * origin_x + origin_y * origin_y
    while frontier:
        x, y, dist = frontier.pop()
        canvas[x, y] = random.random() * falloff > dist / max_dist
        for neighbour in Vector(x, y).neighbours:
            if neighbour.x < 0 or neighbour.y < 0 or neighbour.x >= width or neighbour.y >= height:
                continue
            if (neighbour.x, neighbour.y) in visited:
                continue
            new_dist = (neighbour.x - origin_x) ** 2 + (neighbour.y - origin_y) ** 2
            frontier.append((neighbour.x, neighbour.y, new_dist))
            visited.add((neighbour.x, neighbour.y))

    return canvas


def ellipse(width, height, padding=0):
    canvas = Canvas(width + padding * 2, height + padding * 2)
    rx = width // 2
    ry = height // 2
    xc = rx + padding
    yc = ry + padding

    x = 0
    y = ry

    dx = 2 * ry * ry * x
    dy = 2 * rx * rx * y

    d1 = ((ry * ry) - (rx * rx * ry) + (0.25 * rx * rx))
    while dx < dy:
        for i in range(0, x + 1):
            canvas[i + xc, y + yc] = True
            canvas[-i + xc, y + yc] = True
            canvas[i + xc, -y + yc] = True
            canvas[-i + xc, -y + yc] = True

        if d1 < 0:
            x += 1
            dx = dx + (2 * ry * ry)
            d1 = d1 + dx + (ry * ry)
        else:
            x += 1
            y -= 1
            dx = dx + (2 * ry * ry)
            dy = dy - (2 * rx * rx)
            d1 = d1 + dx - dy + (ry * ry)

    d2 = (((ry * ry) * ((x + 0.5) * (x + 0.5))) + ((rx * rx) * ((y - 1) * (y - 1))) - (rx * rx * ry * ry))
    while y >= 0:
        for i in range(0, x + 1):
            canvas[i + xc, y + yc] = True
            canvas[-i + xc, y + yc] = True
            canvas[i + xc, -y + yc] = True
            canvas[-i + xc, -y + yc] = True

        if (d2 > 0):
            y -= 1
            dy = dy - (2 * rx * rx)
            d2 = d2 + (rx * rx) - dy
        else:
            y -= 1
            x += 1
            dx = dx + (2 * ry * ry)
            dy = dy - (2 * rx * rx)
            d2 = d2 + dx - dy + (rx * rx)

    return canvas


def circle(width, height, falloff=None, padding=0):
    canvas = Canvas(width + padding * 2, height + padding * 2)
    raw_canvas = canvas.canvas
    radius = min(width, height) // 2
    cx = width // 2 + padding
    cy = height // 2 + padding
    check = radius * radius
    if falloff:
        check += radius * falloff

    for y in range(-radius, radius + 1):
        for x in range(-radius, radius + 1):
            if x * x + y * y <= check:
                raw_canvas[(cy + y) * canvas.width + cx + x] = True

    return canvas


def noise(canvas: Canvas, threshold=3, probability=0.5):
    right_limit = canvas.width - 1
    bottom_limit = canvas.height - 1
    width = canvas.width
    raw_canvas = canvas.canvas

    for x in range(canvas.width):
        for y in range(canvas.height):
            if canvas[x, y]:
                continue

            count = 0
            left = x > 0
            top = y > 0
            right = x < right_limit
            bottom = y < bottom_limit

            if left and raw_canvas[y * width + x - 1]:
                count += 1
            if right and raw_canvas[y * width + x + 1]:
                count += 1
            if top and raw_canvas[(y - 1) * width + x]:
                count += 1
            if bottom and raw_canvas[(y + 1) * width + x]:
                count += 1
            if left and top and raw_canvas[(y - 1) * width + x - 1]:
                count += 1
            if right and top and raw_canvas[(y - 1) * width + x + 1]:
                count += 1
            if left and bottom and raw_canvas[(y + 1) * width + x - 1]:
                count += 1
            if right and bottom and raw_canvas[(y + 1) * width + x + 1]:
                count += 1

            if count >= threshold:
                raw_canvas[y * width + x] = random.random() < probability

    return canvas


def tree_generator(width, height):
    return noise(ellipse(width, height))


def house_generator(width, height):
    canvas = Canvas(width, height, Tile.GROUND)

    for x in range(2, width - 2):
        for y in range(2, height - 2):
            canvas[x, y] = Tile.FLOOR

    walls = Rectangle(1, 1, width - 2, height - 2)
    for point in walls:
        canvas[point.x, point.y] = Tile.WALL

    door = walls.random_point(1)
    canvas[door.x, door.y] = Tile.DOOR

    return canvas


class Tile(IntEnum):
    GRASS = auto()
    TREE = auto()
    ROCK = auto()
    WATER = auto()
    WALL = auto()
    DOOR = auto()
    FLOOR = auto()
    GROUND = auto()
    BUSH = auto()
    ROAD = auto()

    @property
    def passable(self):
        return self not in TileMeta.obstacles


class TileMeta:
    obstacles = {
        Tile.WALL, Tile.DOOR
    }


BASE_TILESET = {
    Tile.GRASS: '\'',
    Tile.TREE: '*',
    Tile.ROCK: '^',
    Tile.WATER: '~',
    Tile.WALL: '#',
    Tile.DOOR: '+',
    Tile.FLOOR: '.',
    Tile.GROUND: ' ',
    Tile.BUSH: '"',
    Tile.ROAD: '='
}

WIDE_TILESET = {key: f'{value} ' for key, value in BASE_TILESET.items()}

FEATURES = {
    'tree-large': {
        'size-odd': True,
        'size': (9, 13),
        'tile': Tile.TREE,
        'generator': tree_generator
    },
    'tree-medium': {
        'size-odd': True,
        'size': (5, 7),
        'tile': Tile.TREE,
        'generator': tree_generator
    },
    'tree-small': {
        'size-odd': True,
        'size': (3, 5),
        'tile': Tile.TREE,
        'generator': tree_generator
    },
    'bush': {
        'width': (1, 3),
        'height': (1, 3),
        'tile': Tile.BUSH,
        'generator': walk
    },
    'rock': {
        'width': (1, 3),
        'height': (1, 3),
        'tile': Tile.ROCK,
        'generator': walk

    },
    'rocks': {
        'width': (10, 30),
        'height': (10, 30),
        'include': [
            {
                'feature': 'rock',
                'amount': (3, 10)
            }
        ]
    },
    'grass': {
        'size': 1,
        'tile': Tile.GRASS,
        'generator': plain
    },
    'ground': {
        'size': 1,
        'tile': Tile.GROUND,
        'generator': plain
    },
    'house': {
        'width': (7, 22),
        'height': (7, 22),
        'generator': house_generator,
        'tile': None
    },
    'lake': {
        'size-odd': True,
        'width': (41, 61),
        'height': (41, 61),
        'generator': lambda width, height: noise(ellipse(width, height)),
        'tile': Tile.WATER
    }
}

BIOMES = {
    'forest': [{
        'grass': 10,
        'ground': 3,
        # 'rocks': 1,
        'rock': 3,
        'bush': 3,
        'tree-small': 3,
        'tree-medium': 1,
        'tree-large': 1
    }],
    'village': [{
        'house': 4,
        'ground': 10,
        'grass': 3,
        'bush': 3
    }],
    'lake': [
        {
            'grass': 5,
            'rock': 1
        },
        {
            'lake': 1
        }
    ],
    'field': [{
        'grass': 15,
        'ground': 2,
        'bush': 2,
        'rock': 1
    }]
}


class loop_control:
    class LoopControl(Exception):
        def __init__(self, ctx):
            self.ctx = ctx

    def __init__(self):
        self.braked = False
        self.continued = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return isinstance(exc_val, self.LoopControl) and exc_val.ctx is self

    def break_loop(self):
        self.braked = True
        self.continued = False
        raise self.LoopControl(self)


class BiomeGenerator:
    def __init__(self, biome, width, height):
        self.biome = biome
        self.pool = []
        for layer in BIOMES[biome]:
            layer_pool = []
            for feature, weight in layer.items():
                layer_pool.extend([feature] * weight)
            self.pool.append(layer_pool)
        self.canvas = Canvas(width, height, Tile.GROUND)
        self.width = width
        self.height = height

    def _get_number(self, number, is_odd=False, max_value=None):
        if isinstance(number, int):
            return number

        first, second = number
        result = random.randint(first, second)
        if is_odd and not result % 2:
            result += 1

        if max_value is not None and result > max_value:
            result = max_value
            if is_odd and not result % 2:
                result -= 1

        return result

    def get_size(self, definition):
        if (size := definition.get('size')) is not None:
            size = self._get_number(size, is_odd=definition.get('size-odd'), max_value=min(self.width, self.height))
            return size, size

        return (
            self._get_number(definition['width'], is_odd=definition.get('size-odd'), max_value=self.width),
            self._get_number(definition['height'], is_odd=definition.get('size-odd'), max_value=self.height)
        )

    def clear(self):
        for idx in range(self.width * self.height):
            self.canvas.canvas[idx] = Tile.GROUND

    def generate_layer(self, layer, features_tries=1000, placement_tries=10):
        rectangles = []

        for _ in range(features_tries):
            feature = random.choice(layer)
            definition = FEATURES[feature]
            tile = definition['tile']
            feature_width, feature_height = self.get_size(definition)

            for _ in range(placement_tries):
                if feature_width == self.width:
                    x1 = 0
                else:
                    x1 = random.randint(0, self.width - feature_width - 1)

                if feature_height == self.height:
                    y1 = 0
                else:
                    y1 = random.randint(0, self.height - feature_height - 1)
                bbox = Rectangle(x1, y1, x1 + feature_width - 1, y1 + feature_height - 1)

                for other in rectangles:
                    if bbox.overlaps(other):
                        break
                else:
                    rectangles.append(bbox)
                    geometry = definition.get('generator', automata)(feature_width, feature_height)
                    for tile_x in range(feature_width):
                        for tile_y in range(feature_height):
                            if value := geometry[tile_x, tile_y]:
                                self.canvas[x1 + tile_x, y1 + tile_y] = tile or value
                    break

    def generate(self):
        for layer in self.pool:
            self.generate_layer(layer)

    def to_string(self, tileset=BASE_TILESET):
        return '\n'.join(
            ''.join(tileset[self.canvas[x, y]] for x in range(self.width))
            for y in range(self.height)
        )
