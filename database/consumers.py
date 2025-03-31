import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync

class NotificationConsumer(WebsocketConsumer):
    def connect(self):
        self.room_group_name = 'updates'
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        
        self.accept()
        
        self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'WebSocket connected'
        }))
        
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', None)
        
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': 'submission_update',
                'message': message
            }
        )
        
    def submission_update(self, event):
        message = event['message']
        
        self.send(text_data=json.dumps({
            'type': 'update',
            'message': message
        }))