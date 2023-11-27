import discord
from discord.ext import commands
import os

intents = discord.Intents.default()
intents.members=True

bot = commands.Bot(command_prefix="-", intents=intents)


async def ready_message():
    channel = bot.get_channel(824272924512485376)
    walkysea = bot.get_user(487969419650400297)
    suscat = bot.get_user(618291088121397249)
    allowed_mentions = discord.AllowedMentions(everyone=False, users=False)
    await channel.send(f"{bot.user.mention} is ready\n------------------------\nCreated by {walkysea.mention} and {suscat.mention}", allowed_mentions=allowed_mentions, delete_after=5)

@bot.event
async def on_ready():
    # bot.loop.create_task(ready_message())
    print("Bot is online")






@bot.command()
async def server(ctx, name, template=None):
    guild = await bot.create_guild(name=name, code=template)
    general = bot.utils.get(guild.channels, name="general")
    if general is None:
        general = await guild.create_text_channel(name="general")
    invite = await general.create_invite(max_age=0)
    await ctx.send(f"Server {name} has been created\nInvite: {invite.code}")
    






@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, reason=None):
    if ctx.author.id != member.id:
        await member.ban(reason=reason, delete_message_days=7)
        await ctx.send(f"Banned {member.mention} by {ctx.author.mention} \U0001f44d")
        user = bot.get_user(member.id)
        if reason is None:
            await user.send(f"You were banned by {ctx.author.mention}")
        else:
            await user.send(f"You were banned by {ctx.author.mention} for {reason}")
    else:
        await ctx.send("You cant ban yourself silly")

@bot.command()
async def category(ctx, category: str):
    await ctx.guild.create_category(name=category)

@bot.command()
@commands.has_permissions(manage_channels=True)
async def create(ctx, channel: str, position: int=1):
    channel = await ctx.guild.create_text_channel(name=channel)
    await channel.edit(position=position)

@create.error
async def on_create_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You must have manage channels permission to use this command")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("I need a channel name")
    else:
        raise error
"""
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You must have manage channels permission to use this command")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing a required arguement")
    else:
        raise error
"""

@bot.command()
@commands.has_permissions(manage_roles=True)
async def role(ctx, *, role):
    await ctx.guild.create_role(name=role)
    await ctx.send("Role {role} was created")



async def cogs():
    for i in os.listdir("./testbot"):
        print(i)

bot.loop.create_task(cogs())
bot.run("ODU1MTkwNDM0Mjc5MTk0NjM1.YMu4KA.OnNRqiY7irzeHO1VYxgOT4PqVIQ")