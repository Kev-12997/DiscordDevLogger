import discord
from discord.ext import commands

class Commands(commands.Cog):
    '''
    Cog containing bot commands
    '''
    def __init__(self, bot):
        self.bot = bot

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

async def setup(bot):
    '''
    Adds the Cog from this extension to the bot. 
    '''
    await bot.add_cog(Commands(bot))