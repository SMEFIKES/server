from concurrent.futures import ProcessPoolExecutor
import asyncio
import random
from typing import Dict

from .actions import MoveAction, BlockedMovement, AttackAction, PrepareToBattleAction
from .creatures import Creature
from ..utils.geometry import Vector
from ..utils.constants import Directions
from .worldgen import Tile, Canvas, BiomeGenerator, WIDE_TILESET


class GameHandler:
    def __init__(self):
        self.initialized = False
        self.players: Dict[str, Creature] = {}
        self.creatures: Dict[str, Creature] = {}
        self.time = 0
        self.world_size = Vector(1, 1)
        self.region_size = Vector(30, 15)
        self.map = Canvas(
            self.region_size.x * self.world_size.x,
            self.region_size.y * self.world_size.y,
            Tile.GROUND
        )
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
            goblin = Creature('<Goblin>', 'goblin')
            goblin.position = self.get_free_position()
            goblin.group = 1
            self.creatures[goblin.id] = goblin

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

        for creature in self.creatures.values():
            creature.actions_in_round = 0

            if creature.stamina < creature.max_stamina:
                creature.stamina = min(creature.max_stamina, creature.stamina + creature.energy_regeneration)
                creature.handle_exhausting(self.time)

            if creature.stamina <= 0 or creature.hp <= 0:
                continue

            if creature.kind == 'player':
                continue

            if self.time < creature.next_action_time:
                continue

            behaviour_tree = get_tree(creature.kind)
            behaviour_tree.update(creature, self)
            if creature.acted:
                actions.append(creature.last_action)

        if self._to_kill:
            for creature_id in self._to_kill:
                del self.creatures[creature_id]
                self._to_kill.clear()

        return actions

    def is_available_position(self, x, y):
        if x < 0 or y < 0 or x >= self.map.width or y >= self.map.height:
            return BlockedMovement(BlockedMovement.REASONS.OUT, None)

        if not (tile := self.map[x, y]).passable:
            return BlockedMovement(BlockedMovement.REASONS.OBSTACLE, tile)

        for creature in self.creatures.values():
            if creature.position.equals(x, y):
                return BlockedMovement(BlockedMovement.REASONS.CREATURE, creature)

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
                player.position.set(x, y)
                return

    def add_player(self, name):
        creature = Creature(name, 'player')
        self.players[name] = creature
        self.creatures[creature.id] = creature
        if self.initialized:
            self.set_initial_player_position(name)

    def move_creature(self, creature_id, direction):
        creature = self.creatures[creature_id]
        delta = Directions.delta(direction)
        new_position = creature.position + delta

        if creature.stamina <= 0 or creature.next_action_time > self.time:
            return MoveAction(self.time, creature, False, None, direction)

        destination_available = self.is_available_position(new_position.x, new_position.y)
        if isinstance(destination_available, BlockedMovement):
            if destination_available.reason == BlockedMovement.REASONS.CREATURE:
                return self.attack_creature(creature_id, destination_available.object.id)

            return MoveAction(self.time, creature, False, None, direction)

        tile = self.map[new_position.x, new_position.y]
        if tile == Tile.BUSH:
            creature.stamina -= 5
        elif tile == Tile.ROCK:
            creature.stamina -= 20
        creature.handle_exhausting(self.time)
        creature.attack_energy = creature.defence_energy = 0

        previous, creature.position = creature.position, new_position
        return MoveAction(self.time, creature, True, previous, direction)

    def kill(self, creature):
        self._to_kill.append(creature.id)

    def attack_creature(self, attacker_id, defender_id):
        attacker = self.creatures[attacker_id]
        defender = self.creatures[defender_id]

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
        actor = self.creatures[actor_id]
        if action_type == 'attack':
            actor.attack_energy = energy
            actor.defence_energy = 0
        else:
            actor.attack_energy = 0
            actor.defence_energy = energy
        return PrepareToBattleAction(self.time, actor, action_type, energy)
