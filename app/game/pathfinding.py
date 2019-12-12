# Sample code from https://www.redblobgames.com/pathfinding/a-star/
# Copyright 2014 Red Blob Games <redblobgames@gmail.com>
#
# Feel free to use this code in your own projects, including commercial projects
# License: Apache v2.0 <http://www.apache.org/licenses/LICENSE-2.0.html>

from __future__ import annotations

import heapq
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .handler import GameHandler
    from .actors import Actor
from ..utils.geometry import Vector


class PriorityQueue:
    def __init__(self):
        self.elements = []

    def empty(self):
        return len(self.elements) == 0

    def put(self, item, priority):
        heapq.heappush(self.elements, (priority, item))

    def get(self):
        return heapq.heappop(self.elements)[1]


def heuristic(a, b):
    return abs(a.x - b.x) + abs(a.y - b.y)


def a_star_search(game: GameHandler, actor: Actor, goal: Vector):
    start = actor.position
    frontier = PriorityQueue()
    frontier.put(start, 0)
    came_from = {start: None}
    cost_so_far = {start: 0}

    while not frontier.empty():
        current = frontier.get()

        if current == goal:
            break

        for candidate in current.orthogonal_neighbours:
            if candidate not in game.map:
                continue
            new_cost = cost_so_far[current] + game.get_tile_movement_cost(actor, current, candidate)
            if candidate not in cost_so_far or new_cost < cost_so_far[candidate]:
                cost_so_far[candidate] = new_cost
                priority = new_cost + heuristic(goal, candidate)
                frontier.put(Vector.copy(candidate), priority)
                came_from[candidate] = current

    reconstructed_path = []
    tile = goal
    while tile != start:
        reconstructed_path.append(tile)
        tile = came_from[tile]
    return reconstructed_path
