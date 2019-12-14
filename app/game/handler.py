from concurrent.futures import ProcessPoolExecutor
import asyncio
import random
from typing import Dict, Tuple, Optional

from .actions import MoveAction, BlockedMovement, AttackAction, PrepareToBattleAction
from .actors import Actor
from ..utils.geometry import Vector
from ..utils.constants import Directions
from .worldgen import Tile, Canvas, BiomeGenerator, WIDE_TILESET


class GameHandler:
    def __init__(self):
        self.initialized = False
        self.players: Dict[str, Actor] = {}
        self.actors: Dict[str, Actor] = {}
        self.time = 0
        self.world_size = Vector(1, 1)
        self.region_size = Vector(30, 15)
        self.map = Canvas(
            self.region_size.x * self.world_size.x,
            self.region_size.y * self.world_size.y,
            Tile.GROUND
        )
        self._actors_positions: Dict[Tuple[int, int], Optional[Actor]] = {}
        self._to_kill = []

    async def initialize(self):
        grid = self.generate_world_structure(self.world_size.x, self.world_size.y)
        loop = asyncio.get_running_loop()
        aws = []
        with ProcessPoolExecutor() as pool:
            for x in range(self.world_size.x):
                for y in range(self.world_size.y):
                    aws.append(loop.run_in_executor(pool, self.generate_world_region, x, y, grid[x][y]))
            regions = await asyncio.gather(*aws)

        for idx, region in enumerate(regions):
            y, x = divmod(idx, self.world_size.x)
            self.map.combine(region, self.region_size.x * x, self.region_size.y * y)

        with open('mapdump.txt', 'wt') as file:
            file.write(self.map.to_string_tileset(WIDE_TILESET))

        for player in self.players:
            self.set_initial_player_position(player)

        for _ in range(20):
            goblin = Actor('<Goblin>', 'goblin')
            self.place_actor(goblin, self.get_free_position())
            goblin.faction = 1
            self.actors[goblin.id] = goblin

        self.initialized = True

    def generate_world_structure(self, width, height):
        grid = [['field' for _ in range(height)] for _ in range(width)]
        return grid

    def generate_world_region(self, x, y, biome):
        gen = BiomeGenerator(biome, self.region_size.x, self.region_size.y)
        gen.generate()
        return gen.canvas

    def update(self):
        from .behaviour.loader import get_tree

        if not self.initialized:
            return

        self.time += 1

        actions = []

        for actor in self.actors.values():
            actor.actions_in_round = 0

            if actor.stamina < actor.max_stamina:
                actor.stamina = min(actor.max_stamina, actor.stamina + actor.energy_regeneration)
                actor.handle_exhausting(self.time)

            if actor.stamina <= 0 or actor.hp <= 0:
                continue

            if actor.kind == 'player':
                continue

            if self.time < actor.next_action_time:
                continue

            behaviour_tree = get_tree(actor.kind)
            behaviour_tree.update(actor, self)
            if actor.acted:
                actions.append(actor.last_action)

        player = next(iter(self.players.values()))
        from .behaviour.actions.select_actors import FindNeighbours
        n = FindNeighbours()
        print(n.update(player, self))
        print(self.time, player.recall_knowledge('found_actors'))

        if self._to_kill:
            for actor_id in self._to_kill:
                actor = self.actors.pop(actor_id)
                del self._actors_positions[actor.position.x, actor.position.y]
                self._to_kill.clear()

        return actions

    def is_available_position(self, x, y):
        if x < 0 or y < 0 or x >= self.map.width or y >= self.map.height:
            return BlockedMovement(BlockedMovement.REASONS.OUT, None)

        if not (tile := self.map[x, y]).passable:
            return BlockedMovement(BlockedMovement.REASONS.OBSTACLE, tile)

        if (actor := self.get_actor_at(Vector(x, y))) is not None:
            return BlockedMovement(BlockedMovement.REASONS.ACTOR, actor)

        return True

    def get_free_position(self):
        while True:
            x = random.randint(0, self.world_size.x * self.region_size.x - 1)
            y = random.randint(0, self.world_size.y * self.region_size.y - 1)
            if self.is_available_position(x, y) is True:
                return Vector(x, y)

    def set_initial_player_position(self, name):
        region_x = self.world_size.x // 2
        region_y = self.world_size.y // 2
        x_min = self.region_size.x * region_x
        x_max = x_min + self.region_size.x - 1
        y_min = self.region_size.y * region_y
        y_max = y_min + self.region_size.y - 1

        while True:
            x = random.randint(x_min, x_max)
            y = random.randint(y_min, y_max)

            if self.is_available_position(x, y) is True:
                player = self.players[name]
                self.place_actor(player, Vector(x, y))
                return

    def add_player(self, name):
        actor = Actor(name, 'player')
        self.players[name] = actor
        self.actors[actor.id] = actor
        if self.initialized:
            self.set_initial_player_position(name)

    def place_actor(self, actor: Actor, position: Vector):
        current_position = (actor.position.x, actor.position.y)
        if self._actors_positions.get(current_position) is actor:
            self._actors_positions[current_position] = None

        self._actors_positions[position.x, position.y] = actor
        actor.position = position

    def get_actor_at(self, position: Vector) -> Optional[Actor]:
        return self._actors_positions.get((position.x, position.y))

    def move_actor(self, actor_id, direction):
        actor = self.actors[actor_id]
        delta = Directions.delta(direction)
        new_position = actor.position + delta

        if actor.stamina <= 0 or actor.next_action_time > self.time:
            return MoveAction(self.time, actor, False, None, direction)

        destination_available = self.is_available_position(new_position.x, new_position.y)
        if isinstance(destination_available, BlockedMovement):
            if destination_available.reason == BlockedMovement.REASONS.ACTOR:
                return self.attack_actor(actor_id, destination_available.object.id)

            return MoveAction(self.time, actor, False, None, direction)

        tile = self.map[new_position.x, new_position.y]
        if tile == Tile.BUSH:
            actor.stamina -= 5
        elif tile == Tile.ROCK:
            actor.stamina -= 20
        actor.handle_exhausting(self.time)
        actor.attack_energy = actor.defence_energy = 0

        previous = actor.position
        self.place_actor(actor, new_position)
        return MoveAction(self.time, actor, True, previous, direction)

    def kill(self, actor):
        self._to_kill.append(actor.id)

    def attack_actor(self, attacker_id, defender_id):
        attacker = self.actors[attacker_id]
        defender = self.actors[defender_id]

        if attacker.stamina <= 0 or attacker.next_action_time > self.time:
            return AttackAction(self.time, attacker, defender, False, True, 0)

        if not attacker.position.is_orthogonal_neighbours(defender.position):
            return AttackAction(self.time, attacker, defender, False, True, 0)

        attack = attacker.get_attack()
        defence = defender.get_defence()

        attacker.stamina -= max(1, attacker.attack_energy)
        defender.stamina -= max(1, defender.defence_energy)
        attacker.handle_exhausting(self.time)
        attacker.attack_energy = attacker.defence_energy = 0
        defender.attack_energy = defender.defence_energy = 0

        damage = attack - defence
        defender.hp -= damage
        if defender.hp <= 0:
            self.kill(defender)
            return AttackAction(self.time, attacker, defender, True, False, damage)

        return AttackAction(self.time, attacker, defender, True, True, damage)

    def prepare_to_battle(self, actor_id, action_type, energy):
        actor = self.actors[actor_id]
        if action_type == 'attack':
            actor.attack_energy = energy
            actor.defence_energy = 0
        else:
            actor.attack_energy = 0
            actor.defence_energy = energy
        return PrepareToBattleAction(self.time, actor, action_type, energy)

    def get_tile_movement_cost(self, actor: Actor, current: Vector, candidate: Vector) -> int:
        pass
