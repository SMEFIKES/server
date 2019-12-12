from marshmallow import Schema, fields, validate, post_load, INCLUDE

from app.utils.common import Choices
from app.utils.constants import Directions


class Actions(Choices):
    connect = 'connect'
    disconnect = 'disconnect'
    move = 'move'
    prepare_to_battle = 'prepare_to_battle'


class BaseRequestSerializer(Schema):
    id = fields.String()
    action = fields.String(required=True, validate=validate.OneOf(Actions.choices()))


class BaseActionSerializer(BaseRequestSerializer):
    @post_load
    def process_action(self, data, **kwargs):
        return lambda: self.process(data), self.get_response(data)

    async def send_to_redis(self, data):
        await self.context['app']['redis_publisher'].publish_json('requests', data)

    async def process(self, data):
        await self.send_to_redis(data)

    def get_response(self, data):
        return {'id': self.context['id']}


class ConnectSerializer(BaseActionSerializer):
    username = fields.String(required=True)


class DisconnectSerializer(BaseActionSerializer):
    async def process(self, data):
        app = self.context['app']
        session = app['websockets'].get(self.context['id'])
        if session:
            await session['ws'].close()
            app['websockets'].pop(self.context['id'], None)

    def get_response(self, data):
        return


class MoveSerializer(BaseActionSerializer):
    direction = fields.String(required=True, validate=validate.OneOf(Directions.choices()))


class PrepareToBattleSerializer(BaseActionSerializer):
    type = fields.String(required=True, validate=validate.OneOf(['attack', 'defence']))
    energy = fields.Integer(required=True)


class RequestSerializer(BaseRequestSerializer):
    ACTION_MAPPING = {
        Actions.connect: ConnectSerializer,
        Actions.disconnect: DisconnectSerializer,
        Actions.move: MoveSerializer,
        Actions.prepare_to_battle: PrepareToBattleSerializer
    }

    class Meta:
        unknown = INCLUDE

    @post_load
    def load_action(self, data, **kwargs):
        serializer = self.ACTION_MAPPING[data['action']]
        data['id'] = self.context['id']
        return serializer(context=self.context).load(data)


class VectorSerializer(Schema):
    x = fields.Integer()
    y = fields.Integer()


class ActorSerializer(Schema):
    id = fields.String()
    name = fields.String()
    kind = fields.String()
    position = fields.Nested(VectorSerializer)
    stamina = fields.Integer()
    exhausted = fields.Boolean()
    prepared_to_battle = fields.Boolean()


class MapSerializer(Schema):
    width = fields.Integer()
    height = fields.Integer()
    canvas = fields.List(fields.Integer, data_key='tiles')


class ConnectResponseSerializer(Schema):
    type = fields.Constant('connect', dump_only=True)


class OtherPlayerConnectedResponseSerializer(Schema):
    type = fields.Constant('player_connected', dump_only=True)
    player = fields.Nested(ActorSerializer)


class GameInitializedResponseSerializer(Schema):
    type = fields.Constant('game_initialized', dump_only=True)
    players = fields.Nested(ActorSerializer, many=True)
    actors = fields.Nested(ActorSerializer, many=True)
    map = fields.Nested(MapSerializer)


class MoveResponseSerializer(Schema):
    type = fields.Constant('move', dump_only=True)
    success = fields.Boolean()
    previous_position = fields.Nested(VectorSerializer)
    actor = fields.Nested(ActorSerializer)


class AttackResponseSerializer(Schema):
    type = fields.Constant('attack', dump_only=True)
    success = fields.Boolean()
    actor = fields.Nested(ActorSerializer)
    defender = fields.Nested(ActorSerializer)
    defender_alive = fields.Boolean()
    damage = fields.Integer()


class PrepareToBattleResponseSerializer(Schema):
    type = fields.Constant('prepare_to_battle', dump_only=True)
    actor = fields.Nested(ActorSerializer)
    subtype = fields.String(attribute='type')
    energy = fields.Method('get_energy')

    def get_energy(self, action):
        return int(action.energy / (action.actor.max_stamina * 0.01))


class GameUpdateResponseSerializer(Schema):
    type = fields.Constant('update', dump_only=True)
    time = fields.Integer(attribute='game.time')
    actions = fields.Method('get_actions')
    players = fields.Nested(ActorSerializer, many=True)

    def get_actions(self, data):
        if actions := data['actions']:
            return [action.serialized for action in actions]
        return []
