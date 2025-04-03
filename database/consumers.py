import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer

class SubmissionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'updates'
        
        # Add the channel to the group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept the WebSocket connection
        await self.accept()
        
        # Send a connection established message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'WebSocket connected'
        }))
        
        # Start a periodic ping to keep the connection alive
        self.ping_task = asyncio.create_task(self.send_heartbeat())

    async def receive(self, text_data):
        # Parse the incoming message
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', None)
        
        # Send the received message to the group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'new_submission',
                'message': message
            }
        )
        
    async def new_submission(self, event):
        # Extract message from the event
        message = event['message']
        
        # Send a message to the WebSocket
        await self.send(text_data=json.dumps({
            'type': 'update',
            'message': message
        }))
        
    async def submission_update(self, event):
        # Extract message from the event
        message = event['message']
        
        # Send a message to the WebSocket
        await self.send(text_data=json.dumps({
            'type': 'transaction',
            'message': message
        }))
    
    async def send_heartbeat(self):
        while True:
            await asyncio.sleep(30)  # Send a heartbeat every 30 seconds
            try:
                await self.send(text_data=json.dumps({
                    'type': 'ping'
                }))
            except Exception:
                break  # Break if the connection is closed

    async def disconnect(self, close_code):
        # Clean up the ping task when the WebSocket is closed
        if hasattr(self, 'ping_task'):
            self.ping_task.cancel()
        # Remove the channel from the group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )


class ActiveSearchConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = 'active_search'
        
        # Add the channel to the group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept the WebSocket connection
        await self.accept()
        
        # Send a connection established message
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'WebSocket connected'
        }))
        
        # Start a periodic ping to keep the connection alive
        self.ping_task = asyncio.create_task(self.send_heartbeat())

    async def receive(self, text_data):
        # Parse the incoming message
        text_data_json = json.loads(text_data)
        message = text_data_json.get('message', None)
        
        # Send the received message to the group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'active_search_message',
                'message': message
            }
        )
        
    async def active_search_message(self, event):
        # Extract message from the event
        message = event['message']
        
        # Send a message to the WebSocket
        await self.send(text_data=json.dumps({
            'type': 'active_search_update',
            'message': message
        }))
    
    async def send_heartbeat(self):
        while True:
            await asyncio.sleep(30)  # Send a heartbeat every 30 seconds
            try:
                await self.send(text_data=json.dumps({
                    'type': 'ping'
                }))
            except Exception:
                break  # Break if the connection is closed

    async def disconnect(self, close_code):
        # Clean up the ping task when the WebSocket is closed
        if hasattr(self, 'ping_task'):
            self.ping_task.cancel()
        # Remove the channel from the group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
