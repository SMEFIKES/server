import logging
import uuid
import asyncio
import json

from aiohttp import web, WSMsgType
from aiohttp import WSCloseCode
import aioredis
from marshmallow import ValidationError

from app.server.serializers import RequestSerializer

logger = logging.getLogger('aiohttp.web')


class WSServer(web.Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.basicConfig(level=logging.DEBUG)
        self['websockets'] = {}
        self.on_startup.append(self.on_startup_handler)
        self.on_shutdown.append(self.on_shutdown_handler)
        self.add_routes([web.get('/ws', self.websocket_handler)])

    @staticmethod
    async def websocket_handler(request):
        ws = web.WebSocketResponse()
        ws_id = uuid.uuid4().hex
        await ws.prepare(request)
        print(f'Added websocket {ws_id}')

        request.app['websockets'][ws_id] = {'ws': ws}
        serializer = RequestSerializer(context={'id': ws_id, 'app': request.app})

        try:
            async for msg in ws:
                print(msg)
                if msg.type == WSMsgType.TEXT:
                    try:
                        processor, response = serializer.loads(msg.data)

                    except json.JSONDecodeError:
                        await ws.send_json({'error': 'JSON decode error'})
                        continue

                    except ValidationError as error:
                        await ws.send_json(error.messages)
                        continue

                    await processor()

                    if response:
                        await ws.send_json(response)

        finally:
            request.app['websockets'].pop(ws_id, None)

        return ws

    @staticmethod
    async def listen_to_redis(app):
        try:
            redis = await aioredis.create_redis_pool('redis://localhost:6379')
            print('Connected to redis')
        except FileNotFoundError:
            print('Cannot connect to redis')
            return

        try:
            ch, *_ = await redis.subscribe('responses')
            async for msg in ch.iter(encoding='utf-8', decoder=json.loads):
                recipients = msg.pop('recipients', None)
                if recipients:
                    for ws_id in recipients:
                        session = app['websockets'].get(ws_id)
                        if session:
                            print(f'Message sent: {msg}')
                            await session['ws'].send_json(msg)

                else:
                    for session in app['websockets'].values():
                        print(f'Message sent: {msg}')
                        await session['ws'].send_json(msg)

        except asyncio.CancelledError:
            pass
        finally:
            try:
                await redis.unsubscribe(ch.name)
                await redis.quit()
            except UnboundLocalError:
                pass

    @staticmethod
    async def on_startup_handler(app):
        print('Startup')
        app['redis_publisher'] = await aioredis.create_redis('redis://localhost:6379')
        app['redis_listener'] = asyncio.create_task(app.listen_to_redis(app))

    @staticmethod
    async def on_shutdown_handler(app):
        app['redis_listener'].cancel()
        await app['redis_listener']

        app['redis_publisher'].close()
        await app['redis_publisher'].wait_closed()

        for ws in {session['ws'] for session in app['websockets']}:
            await ws.close(code=WSCloseCode.GOING_AWAY, message='Server shutdown')


if __name__ == '__main__':
    web.run_app(WSServer())
