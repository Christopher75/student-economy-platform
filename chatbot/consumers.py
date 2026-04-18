import json
import anthropic
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from .knowledge import build_system_prompt


class ChatbotConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope.get('user')
        self.history = []
        self.session = await self.create_session()
        self.ticket_flow = None  # tracks if we're mid ticket-creation
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        user_message = data.get('message', '').strip()
        if not user_message:
            return

        await self.save_message('user', user_message)
        self.history.append({'role': 'user', 'content': user_message})

        # Check if we should create a ticket
        if self.ticket_flow and self.ticket_flow.get('stage') == 'confirm':
            if any(w in user_message.lower() for w in ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'create', 'go ahead']):
                ticket = await self.create_ticket(self.ticket_flow)
                reply = f"✅ Done! Your support ticket **#{ticket.pk}** has been created under the **{self.ticket_flow['category_display']}** category. Our team will respond within 24–48 hours. You can track it at /contact/ticket/{ticket.pk}/"
                self.ticket_flow = None
                await self.send(json.dumps({'type': 'stream', 'chunk': reply}))
                await self.send(json.dumps({'type': 'end'}))
                await self.save_message('assistant', reply)
                self.history.append({'role': 'assistant', 'content': reply})
                return
            elif any(w in user_message.lower() for w in ['no', 'nope', 'cancel', 'nevermind', "don't"]):
                self.ticket_flow = None

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        system_prompt = build_system_prompt(self.user)

        full_response = ''
        try:
            with client.messages.stream(
                model='claude-sonnet-4-20250514',
                max_tokens=1024,
                system=system_prompt,
                messages=self.history,
            ) as stream:
                for chunk in stream.text_stream:
                    full_response += chunk
                    await self.send(json.dumps({'type': 'stream', 'chunk': chunk}))
        except Exception as e:
            full_response = "Sorry, I'm having trouble connecting right now. Please try again in a moment."
            await self.send(json.dumps({'type': 'stream', 'chunk': full_response}))

        await self.send(json.dumps({'type': 'end'}))
        await self.save_message('assistant', full_response)
        self.history.append({'role': 'assistant', 'content': full_response})

        # Detect if bot suggested creating a ticket and set up the flow
        lower = full_response.lower()
        if 'create a support ticket' in lower or 'raise a ticket' in lower or 'open a ticket' in lower:
            category, category_display = self.detect_category(user_message)
            self.ticket_flow = {
                'stage': 'confirm',
                'subject': user_message[:100],
                'message': user_message,
                'category': category,
                'category_display': category_display,
            }

    def detect_category(self, message):
        message = message.lower()
        if any(w in message for w in ['pay', 'momo', 'mtn', 'airtel', 'pro', 'subscription', 'upgrade', 'transaction']):
            return 'payment', 'Payment Issue'
        if any(w in message for w in ['login', 'password', 'account', 'verify', 'email', 'otp', 'profile']):
            return 'account', 'Account Problem'
        if any(w in message for w in ['listing', 'skill', 'booking', 'sold', 'post']):
            return 'listing', 'Listing / Skill Issue'
        if any(w in message for w in ['bug', 'error', 'crash', 'broken', 'not working']):
            return 'bug', 'Report a Bug'
        return 'other', 'Other'

    @database_sync_to_async
    def create_session(self):
        from .models import ChatSession
        user = self.user if self.user and self.user.is_authenticated else None
        return ChatSession.objects.create(user=user)

    @database_sync_to_async
    def save_message(self, role, content):
        from .models import ChatMessage
        return ChatMessage.objects.create(
            session=self.session,
            role=role,
            content=content
        )

    @database_sync_to_async
    def create_ticket(self, flow):
        from core.models import SupportTicket
        user = self.user if self.user and self.user.is_authenticated else None
        name = user.display_name if user else 'Anonymous'
        email = user.email if user else 'unknown@student.com'
        return SupportTicket.objects.create(
            user=user,
            name=name,
            email=email,
            category=flow['category'],
            subject=flow['subject'],
            message=flow['message'],
        )