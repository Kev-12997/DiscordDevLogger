import discord
from discord.ext import commands
from database import Database
import json
import os
from datetime import datetime
from aiohttp import web
import asyncio

class DirectWebhookAlerts(commands.Cog):
    '''
    Cog for handling log alerts via direct webhooks (no database storage)
    '''
    def __init__(self, bot):
        self.bot = bot
        try:
            self.db = Database()
            print("✅ Direct Webhook Alerts: Database connection initialized successfully!")
        except Exception as e:
            print(f"❌ Direct Webhook Alerts: Failed to initialize database: {e}")
            self.db = None
        
        # Webhook server configuration
        self.webhook_port = int(os.getenv('WEBHOOK_PORT', 8080))
        self.webhook_secret = os.getenv('WEBHOOK_SECRET', 'your-secure-webhook-secret-here')
        
        # Initialize webhook server
        self.app = web.Application()
        self.setup_routes()
        self.runner = None
        self.site = None
        
        # Start webhook server
        self.bot.loop.create_task(self.start_webhook_server())
    
    def setup_routes(self):
        '''Setup webhook routes'''
        self.app.router.add_post('/webhook/log', self.handle_log_webhook)
        self.app.router.add_get('/webhook/health', self.health_check)
        self.app.router.add_get('/', self.root_handler)
    
    async def root_handler(self, request):
        '''Root endpoint for basic info'''
        return web.Response(
            status=200, 
            text='Discord Bot Log Webhook Server - Ready to receive logs!',
            content_type='text/plain'
        )
    
    async def health_check(self, request):
        '''Health check endpoint'''
        return web.json_response({
            'status': 'healthy',
            'service': 'discord-bot-log-webhook',
            'timestamp': datetime.utcnow().isoformat(),
            'users_table': 'connected' if self.db else 'disconnected'
        })
    
    async def handle_log_webhook(self, request):
        '''
        Handle incoming log webhook from applications
        
        Expected payload format:
        {
            "api_key": "user's API key",
            "level": "ERROR|WARNING|INFO|DEBUG",
            "message": "Log message",
            "application": "App Name (optional)",
            "metadata": { ... optional metadata ... }
        }
        '''
        try:
            # Parse the webhook payload
            try:
                data = await request.json()
            except json.JSONDecodeError:
                return web.json_response({'error': 'Invalid JSON payload'}, status=400)
            
            # Validate required fields
            required_fields = ['api_key', 'level', 'message']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return web.json_response({
                    'error': f'Missing required fields: {", ".join(missing_fields)}'
                }, status=400)
            
            # Validate log level
            valid_levels = ['ERROR', 'CRITICAL', 'WARNING', 'WARN', 'INFO', 'DEBUG']
            if data['level'].upper() not in valid_levels:
                return web.json_response({
                    'error': f'Invalid log level. Must be one of: {", ".join(valid_levels)}'
                }, status=400)
            
            print(f"📨 Received log: {data['level']} - {data['message'][:50]}...")
            
            # Get user by API key
            if not self.db:
                return web.json_response({'error': 'Database not available'}, status=503)
            
            user_data = await self.db.get_user_by_api_key(data['api_key'])
            if not user_data:
                print(f"❌ Invalid API key: {data['api_key'][:10]}...")
                return web.json_response({'error': 'Invalid API key'}, status=401)
            
            if not user_data.get('is_active', False):
                return web.json_response({'error': 'API key is inactive'}, status=401)
            
            # Create alert data
            alert_data = {
                'discord_user_id': user_data['discord_user_id'],
                'level': data['level'].upper(),
                'message': data['message'],
                'application': data.get('application', 'Unknown App'),
                'metadata': data.get('metadata', {}),
                'created_at': datetime.utcnow().isoformat(),
                'api_key': data['api_key'][:10] + '...'  # For logging purposes
            }
            
            # Process the alert immediately (no database storage)
            success = await self.process_alert_immediately(alert_data)
            
            if success:
                return web.json_response({
                    'status': 'success',
                    'message': 'Log alert sent to Discord user'
                }, status=200)
            else:
                return web.json_response({
                    'status': 'partial_success',
                    'message': 'Log received but user notification may have failed'
                }, status=202)
            
        except Exception as e:
            print(f"❌ Webhook error: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def start_webhook_server(self):
        '''Start the webhook server'''
        try:
            # Wait for bot to be ready
            await self.bot.wait_until_ready()
            
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, '0.0.0.0', self.webhook_port)
            await self.site.start()
            
            print(f"🌐 Direct Log Webhook Server started successfully!")
            print(f"   📍 Listening on: http://0.0.0.0:{self.webhook_port}")
            print(f"   🔗 Health check: http://0.0.0.0:{self.webhook_port}/webhook/health")
            print(f"   🪝 Log webhook: http://0.0.0.0:{self.webhook_port}/webhook/log")
            print(f"   📋 Expected payload: api_key, level, message, [application], [metadata]")
            
        except Exception as e:
            print(f"❌ Failed to start webhook server: {e}")
    
    def cog_unload(self):
        '''Cleanup when cog is unloaded'''
        if self.runner:
            asyncio.create_task(self.runner.cleanup())
        print("🛑 Webhook server stopped")
    
    async def process_alert_immediately(self, alert_data):
        '''
        Process a log alert immediately by notifying the user
        
        Args:
            alert_data: Dictionary containing alert information
            
        Returns:
            bool: True if notification was sent successfully
        '''
        try:
            discord_user_id = alert_data['discord_user_id']
            level = alert_data['level']
            message = alert_data['message']
            application = alert_data['application']
            metadata = alert_data['metadata']
            created_at = alert_data['created_at']
            
            print(f"🔄 Processing immediate alert for user {discord_user_id}")
            
            # Get the Discord user object
            user = self.bot.get_user(discord_user_id)
            if not user:
                print(f"❌ Could not find Discord user with ID {discord_user_id}")
                return False
            
            # Create embed
            embed = self.create_alert_embed(level, message, application, metadata, created_at)
            
            # Try to send the alert in guilds where both bot and user are present
            sent = False
            for guild in self.bot.guilds:
                member = guild.get_member(discord_user_id)
                if member:
                    channel = await self.find_alert_channel(guild)
                    if channel:
                        try:
                            await channel.send(f"{member.mention}", embed=embed)
                            print(f"✅ Alert sent to {guild.name} #{channel.name}")
                            sent = True
                            break  # Send only once across all guilds
                        except discord.Forbidden:
                            print(f"❌ No permission to send message in {guild.name} #{channel.name}")
                        except Exception as e:
                            print(f"❌ Error sending alert in {guild.name}: {e}")
            
            # Fallback to DM if no guild channel worked
            if not sent:
                try:
                    await user.send(embed=embed)
                    print(f"✅ Alert sent via DM to {user.name}")
                    sent = True
                except discord.Forbidden:
                    print(f"❌ Could not send DM to user {discord_user_id} - DMs disabled")
                except Exception as e:
                    print(f"❌ Error sending DM to user {discord_user_id}: {e}")
            
            return sent
                
        except Exception as e:
            print(f"❌ Error processing immediate alert: {e}")
            return False
    
    def create_alert_embed(self, level, message, application, metadata, created_at):
        '''
        Create a Discord embed for the alert based on log level
        '''
        # Color based on log level
        colors = {
            'ERROR': 0xff0000,      # Red
            'CRITICAL': 0x8b0000,   # Dark Red
            'WARNING': 0xffa500,    # Orange
            'WARN': 0xffa500,       # Orange
            'INFO': 0x0099ff,       # Blue
            'DEBUG': 0x808080       # Gray
        }
        
        # Emoji based on log level
        emojis = {
            'ERROR': '🚨',
            'CRITICAL': '💥',
            'WARNING': '⚠️',
            'WARN': '⚠️',
            'INFO': 'ℹ️',
            'DEBUG': '🐛'
        }
        
        color = colors.get(level.upper(), 0x0099ff)
        emoji = emojis.get(level.upper(), '📝')
        
        embed = discord.Embed(
            title=f"{emoji} {level.upper()} Log",
            description=message,
            color=color
        )
        
        # Set timestamp
        try:
            if isinstance(created_at, str):
                embed.timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        except Exception:
            embed.timestamp = datetime.utcnow()
        
        embed.add_field(name="Application", value=application, inline=True)
        embed.add_field(name="Level", value=level.upper(), inline=True)
        embed.add_field(name="Time", value=f"<t:{int(datetime.utcnow().timestamp())}:R>", inline=True)
        
        # Add metadata fields if available
        if metadata and isinstance(metadata, dict):
            for key, value in list(metadata.items())[:6]:  # Limit to 6 metadata fields
                if len(str(value)) <= 1024:  # Discord embed field value limit
                    embed.add_field(
                        name=key.replace('_', ' ').title(), 
                        value=f"```{str(value)}```" if len(str(value)) > 50 else str(value), 
                        inline=True
                    )
        
        embed.set_footer(text="🔄 Real-time Log Alert")
        
        return embed
    
    async def find_alert_channel(self, guild):
        '''
        Find a suitable channel to send alerts in a guild
        '''
        # Priority order for channel selection
        channel_names = ['logs', 'alerts', 'notifications', 'bot-logs', 'general']
        
        # First, try to find channels by name
        for name in channel_names:
            channel = discord.utils.get(guild.text_channels, name=name)
            if channel and channel.permissions_for(guild.me).send_messages:
                return channel
        
        # If no named channel found, use the first channel where bot can send messages
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                return channel
        
        return None
    
    @commands.command(name='test_log')
    @commands.has_permissions(administrator=True)
    async def test_log(self, context, level: str = "INFO"):
        '''Test direct log processing'''
        if not self.db:
            await context.send("❌ Database not initialized!")
            return
            
        # Get user's API key
        user_data = await self.db.get_user_by_discord_id(context.author.id)
        if not user_data or not user_data.get('is_active', False):
            await context.send("❌ You need an active API subscription! Use `!subscribe` first.")
            return
        
        test_alert = {
            'discord_user_id': context.author.id,
            'level': level.upper(),
            'message': f'This is a test {level.lower()} log message from the direct webhook system!',
            'application': 'Direct Test',
            'metadata': {
                'test': True, 
                'triggered_by': str(context.author),
                'channel': str(context.channel),
                'timestamp': datetime.utcnow().isoformat()
            },
            'created_at': datetime.utcnow().isoformat()
        }
        
        await context.send(f"🧪 Sending test {level.upper()} log...")
        success = await self.process_alert_immediately(test_alert)
        
        if success:
            await context.send("✅ Test log sent successfully!")
        else:
            await context.send("❌ Failed to send test log!")
    
    @commands.command(name='webhook_info')
    async def webhook_info(self, context):
        '''Show webhook information and usage'''
        embed = discord.Embed(
            title="🌐 Log Webhook Information",
            description="Send logs directly to Discord without database storage!",
            color=0x0099ff
        )
        
        if self.site:
            embed.add_field(name="Status", value="✅ Running", inline=True)
            embed.add_field(name="Endpoint", value=f"`POST /webhook/log`", inline=True)
            embed.add_field(name="Port", value=str(self.webhook_port), inline=True)
            
            embed.add_field(
                name="Required Payload",
                value="```json\n{\n  \"api_key\": \"your_api_key\",\n  \"level\": \"ERROR\",\n  \"message\": \"Error message\",\n  \"application\": \"My App\",\n  \"metadata\": {...}\n}```",
                inline=False
            )
            
            embed.add_field(
                name="Supported Levels",
                value="`ERROR`, `CRITICAL`, `WARNING`, `WARN`, `INFO`, `DEBUG`",
                inline=False
            )
            
            embed.set_footer(text="Get your API key with !mykey command")
        else:
            embed.add_field(name="Status", value="❌ Not Running", inline=True)
            embed.color = 0xff0000
        
        await context.send(embed=embed)

async def setup(bot):
    '''Add the DirectWebhookAlerts cog to the bot'''
    await bot.add_cog(DirectWebhookAlerts(bot))