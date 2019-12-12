import asyncio
import json

import aioredis

from app.game.handler import GameHandler
from app.server.serializers import (
    ConnectResponseSerializer, GameInitializedResponseSerializer, MoveResponseSerializer,
    GameUpdateResponseSerializer, OtherPlayerConnectedResponseSerializer
)


class Worker:
    def __init__(self):
        self.main_publisher = None
        self.main_subscriber = None
        self.requests_channel = None
        self.players = {}
        self.reverse_players_mapping = {}
        self.game = GameHandler()

    def get_player(self, name):
        return self.game.players[name]

    async def send_response(self, username, data):
        if username is not None:
            websockets_ids = self.players.get(username)
            if not websockets_ids:
                return
            data['recipients'] = websockets_ids

        elif not self.players:
            return

        self.main_publisher.publish_json('responses', data)

    async def requests_processor(self):
        async for msg in self.requests_channel.iter(encoding='utf-8', decoder=json.loads):
            handler = getattr(self, f'handle_{msg["action"]}')
            await handler(msg)

    async def game_processor(self):
        serializer = GameUpdateResponseSerializer()
        while True:
            actions = self.game.update()
            await self.send_response(None, serializer.dump({
                'game': self.game, 'actions': actions, 'players': self.game.players.values()
            }))
            await asyncio.sleep(0.5)

    async def main(self):
        self.main_publisher = await aioredis.create_redis('redis://localhost:6379')
        self.main_subscriber = await aioredis.create_redis('redis://localhost:6379')
        self.requests_channel = (await self.main_subscriber.subscribe('requests'))[0]
        print('Connected')

        try:
            await asyncio.gather(self.requests_processor(), self.game_processor())
        except asyncio.CancelledError:
            print('Cancelled')
            pass
        finally:
            self.main_subscriber.unsubscribe(self.requests_channel.name)
            self.main_subscriber.close()
            self.main_publisher.close()
            await self.main_subscriber.wait_closed()
            await self.main_publisher.wait_closed()

    async def handle_connect(self, data):
        username = data['username']
        websocket_id = data['id']

        self.reverse_players_mapping[websocket_id] = username
        if username in self.players:
            self.players[username].append(websocket_id)
        else:
            self.game.add_player(username)
            self.players[username] = [websocket_id]

        await self.send_response(username, ConnectResponseSerializer().dump(None))

        if not self.game.initialized:
            await self.game.initialize()
            recipients = list(self.players.keys())
        else:
            recipients = [username]

        for recipient in recipients:
            await self.send_response(
                recipient,
                GameInitializedResponseSerializer().dump({
                    'players': self.game.players.values(),
                    'actors': self.game.actors.values(),
                    'map': self.game.map
                })
            )
            if recipient != username:
                await self.send_response(
                    recipient,
                    OtherPlayerConnectedResponseSerializer().dump({'player': self.get_player(username)})
                )

    async def handle_move(self, data):
        player_name = self.reverse_players_mapping[data['id']]
        player = self.game.players[player_name]
        movement_result = self.game.move_actor(player.id, data['direction'])
        await self.send_response(None, movement_result.serialized)

    async def handle_prepare_to_battle(self, data):
        player_name = self.reverse_players_mapping[data['id']]
        player = self.game.players[player_name]
        preparing_result = self.game.prepare_to_battle(player.id, data['type'], data['energy'])
        await self.send_response(None, preparing_result.serialized)


if __name__ == '__main__':
    worker = Worker()
    asyncio.run(worker.main())
