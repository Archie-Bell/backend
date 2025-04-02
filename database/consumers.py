import json
from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync

class SubmissionConsumer(WebsocketConsumer):
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
                'type': 'new_submission',
                'message': message
            }
        )
        
    def new_submission(self, event):
        message = event['message']
        
        self.send(text_data=json.dumps({
            'type': 'update',
            'message': message
        }))
        
    def submission_update(self, event):
        message = event['message']
        
        self.send(text_data=json.dumps({
            'type': 'transaction',
            'message': message
        }))
        
class ActiveSearchConsumer(WebsocketConsumer):
    def connect(self):
        self.room_group_name = 'active_search'
        
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
                'type': 'active_search_message',
                'message': message
            }
        )
        
    def active_search_message(self, event):
        message = event['message']
        
        self.send(text_data=json.dumps({
            'type': 'active_search_update',
            'message': message
        }))