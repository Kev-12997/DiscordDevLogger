import discord
from discord.ext import commands
from database import Database

class Commands(commands.Cog):
    '''
    Cog containing bot commands
    '''
    def __init__(self, bot):
        self.bot = bot
        try:
            self.db = Database()
            print("✅ Database connection initialized successfully!")
        except Exception as e:
            print(f"❌ Failed to initialize database: {e}")
            self.db = None

    @commands.command(name='hello')
    async def hello(self, context):
        '''
        Says hello to whoever called the 'hello' command.
        '''
        await context.send(f'Hello {context.author.mention}!')

    @commands.command(name='ping')
    async def ping(self, context):
        '''
        Check bot latency
        '''
        latency = round(self.bot.latency * 1000)
        await context.send(f'Pong! Latency: {latency}ms')

    @commands.command(name='info')
    async def info(self, context):
        '''
        Creates an embeded message with bot information
        '''
        embed = discord.Embed(
            title="Bot Information",
            description="A simple Discord bot running in Docker",
            color=0x00ff00
        )
        embed.add_field(name="Guilds", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Users", value=len(self.bot.users), inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        await context.send(embed=embed)
        
    @commands.command(name='subscribe')
    async def subscribe(self, context):
        '''
        Subscribe user to the logging API and generate their API key
        '''
        user_id = context.author.id
        
        try:
            # Check if user already exists
            existing_user = await self.db.get_user_by_discord_id(user_id)
            
            if existing_user:
                if existing_user.get('is_active', False):
                    # User already subscribed and active
                    embed = discord.Embed(
                        title="Already Subscribed! 🔑",
                        description="You're already subscribed to the logging API.",
                        color=0xffa500
                    )
                    embed.add_field(
                        name="Your API Key", 
                        value=f"```{existing_user['api_key']}```", 
                        inline=False
                    )
                    embed.add_field(
                        name="Usage", 
                        value="Use this key in your applications to send logs to Discord!", 
                        inline=False
                    )
                else:
                    # User exists but is inactive - reactivate them
                    await self.db.activate_user(user_id)
                    
                    embed = discord.Embed(
                        title="Welcome Back! 🎉",
                        description="Your subscription has been reactivated!",
                        color=0x00ff00
                    )
                    embed.add_field(
                        name="Your API Key", 
                        value=f"```{existing_user['api_key']}```", 
                        inline=False
                    )
            else:
                # Create new user
                user_data = await self.db.add_user(user_id)
                
                embed = discord.Embed(
                    title="Successfully Subscribed! 🎉",
                    description=f"Welcome to the logging API, {context.author.mention}!",
                    color=0x00ff00
                )
                embed.add_field(
                    name="Your API Key", 
                    value=f"```{user_data['api_key']}```", 
                    inline=False
                )
                embed.add_field(
                    name="Important", 
                    value="⚠️ Keep this key secure! Don't share it publicly.", 
                    inline=False
                )
                embed.add_field(
                    name="How to Use", 
                    value="Use this key in your applications to send logs that will appear in this Discord server!", 
                    inline=False
                )
            
            try:
                await context.author.send(embed=embed)
                await context.send("📩 I've sent your API key to your DMs!")
            except discord.Forbidden:
                # If DMs are disabled, send in channel with warning
                embed.add_field(
                    name="⚠️ Warning", 
                    value="Your DMs are disabled, so I'm showing your key here. Consider deleting this message after copying your key!", 
                    inline=False
                )
                await context.send(embed=embed)
                
            
        except Exception as e:
            error_embed = discord.Embed(
                title="Subscription Failed ❌",
                description=str(e),
                color=0xff0000
            )
            await context.send(embed=error_embed)
            
    @commands.command(name='unsubscribe')
    async def unsubscribe(self, context):
        '''
        Unsubscribe user from the logging API (deactivate their key)
        '''
        user_id = context.author.id
        
        try:
            # Check if user exists and is active
            existing_user = await self.db.get_user_by_discord_id(user_id)
            
            if not existing_user:
                embed = discord.Embed(
                    title="Not Subscribed ❌",
                    description="You're not currently subscribed to the logging API.",
                    color=0xff0000
                )
                await context.send(embed=embed)
                return
            
            if not existing_user.get('is_active', False):
                embed = discord.Embed(
                    title="Already Unsubscribed ❌",
                    description="Your subscription is already inactive.",
                    color=0xffa500
                )
                await context.send(embed=embed)
                return
            
            # Deactivate user
            success = await self.db.deactivate_user(user_id)
            
            if success:
                embed = discord.Embed(
                    title="Successfully Unsubscribed ✅",
                    description="Your API key has been deactivated. You can resubscribe anytime with `!subscribe`.",
                    color=0x00ff00
                )
            else:
                embed = discord.Embed(
                    title="Unsubscribe Failed ❌",
                    description="There was an error deactivating your subscription.",
                    color=0xff0000
                )
            
            await context.send(embed=embed)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="Unsubscribe Failed ❌",
                description=f"An error occurred: {str(e)}",
                color=0xff0000
            )
            await context.send(embed=error_embed)   
    
    @commands.command(name='mykey')
    async def mykey(self, context):
        '''
        Show user their current API key (sent as DM for security)
        '''
        user_id = context.author.id
        
        try:
            user_data = await self.db.get_user_by_discord_id(user_id)
            
            if not user_data or not user_data.get('is_active', False):
                embed = discord.Embed(
                    title="No Active Subscription ❌",
                    description="You don't have an active API subscription. Use `!subscribe` to get started!",
                    color=0xff0000
                )
                await context.send(embed=embed)
                return
            
            # Send API key as DM for security
            embed = discord.Embed(
                title="Your API Key 🔑",
                description="Here's your current API key:",
                color=0x0099ff
            )
            embed.add_field(
                name="API Key", 
                value=f"```{user_data['api_key']}```", 
                inline=False
            )
            embed.add_field(
                name="Security Notice", 
                value="🔒 This key is sent privately. Keep it secure!", 
                inline=False
            )
            
            try:
                await context.author.send(embed=embed)
                await context.send("📩 I've sent your API key to your DMs!")
            except discord.Forbidden:
                # If DMs are disabled, send in channel with warning
                embed.add_field(
                    name="⚠️ Warning", 
                    value="Your DMs are disabled, so I'm showing your key here. Consider deleting this message after copying your key!", 
                    inline=False
                )
                await context.send(embed=embed)
            
        except Exception as e:
            error_embed = discord.Embed(
                title="Error ❌",
                description=f"An error occurred: {str(e)}",
                color=0xff0000
            )
            await context.send(embed=error_embed)

async def setup(bot):
    '''
    Adds the Cog from this extension to the bot. 
    '''
    await bot.add_cog(Commands(bot))