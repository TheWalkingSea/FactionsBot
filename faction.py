import discord
from discord.enums import NotificationLevel
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
import aiosqlite as sql

bot = commands.Bot(command_prefix="-", intents=discord.Intents.all())

class HelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Help", color=discord.Color.blue())
        for cog, commands in mapping.items():
            filter = await self.filter_commands(commands, sort=True)
            signatures = [self.get_command_signature(i) for i in filter]
            if signatures:
                cog = getattr(cog, "qualified_name", "No Category")
                embed.add_field(name=f"__{cog.capitalize()}__", value="\n".join(signatures), inline=False)
        destination = self.get_destination()
        await destination.send(embed=embed)
    
    async def send_command_help(self, command):
        embed = discord.Embed(title=f"{command.qualified_name.capitalize()} Help")
        embed.add_field(name=command.help, value=self.get_command_signature(command))
        aliases = command.aliases
        if aliases:
            embed.add_field(name=aliases, value=", ".join(aliases))
        destination = self.get_destination()
        await destination.send(embed=embed)
        
    async def send_group_help(self, group):
        embed = discord.Embed(title=f"{group.qualified_name.capitalize()} Help")
        for command in group.commands:
            embed.add_field(name=command.help, value=self.get_command_signature(command), inline=False)
        destination = self.get_destination()
        await destination.send(embed=embed)

bot.help_command = HelpCommand()


@bot.event
async def on_ready():
    print("Up and Running")

@bot.group(invoke_without_command=True)
async def faction(ctx):
    await ctx.send("```Commands:\n color  \n create \n invite \n join   \n kick   \n leave \n list \n rename ```")

async def full(faction):
    async with sql.connect("bot.db") as db:
        cursor = await db.execute("SELECT id FROM members WHERE role=?", (faction,))
        fetch = await cursor.fetchall()
    return len(fetch) >= 6



async def original_owner(ctx, id):
    async with sql.connect("bot.db") as db:
        cursor = await db.execute("SELECT role FROM owners WHERE owner=?", (id,))
        fetch = await cursor.fetchone()
        if fetch is not None:
            await ctx.send("You already own a faction")
            return False

        cursor = await db.execute("SELECT id FROM members WHERE id=?", (id,))
        fetch = await cursor.fetchone()
        if fetch is not None:
            await ctx.send("Your already in a faction")
            return False
        return True

async def original_user(ctx, id):
    async with sql.connect("bot.db") as db:
        cursor = await db.execute("SELECT id FROM members WHERE id=?", (id,))
        fetch = await cursor.fetchone()
        if fetch is not None:
            await ctx.send("Your already in a faction")
            return False
        return True

@faction.command(aliases=['list'])
async def lista(ctx, *, clan=None):
    async with sql.connect("bot.db") as db:
        if clan:
            cursor = await db.execute("SELECT role FROM owners WHERE role=?", (clan,))
            fetch = await cursor.fetchone()
            if not fetch:
                await ctx.send(embed=discord.Embed(title=f"Faction {clan} doesn't exist", colour=discord.Colour.red()))
                return
        else:
            cursor = await db.execute("SELECT role FROM members WHERE id=?", (ctx.author.id,))
            fetch = await cursor.fetchone()
            if not fetch:
                await ctx.send(embed=discord.Embed(title=f"You are not in a clan", colour=discord.Colour.red()))
                return
            clan = fetch[0]
        cursor = await db.execute("SELECT owner FROM owners WHERE role=?", (clan,))
        fetch = await cursor.fetchone()
        owner = bot.get_user(int(fetch[0]))
        cursor = await db.execute("SELECT id FROM members WHERE role=?", (clan,))
        fetch = await cursor.fetchall()
        members = ", ".join(list(map(lambda id: bot.get_user(int(id[0])).name, fetch)))
        # print(list(map(lambda id: bot.get_user(int(id[0])).name, members)))
        await ctx.send(f"```{clan}: \n Owner: {owner.name}\n  {members}```")

    """       
@bot.command()
async def test(ctx):
    category = await ctx.guild.create_category(name="nam")
    await category.create_channel(name="e")
    """
@faction.command()
#@commands.cooldown(1, (24*60*60), BucketType.user)
async def create(ctx, *, name: str):
    if await original_owner(ctx, ctx.author.id) is False:
        return
    else:
        role = discord.utils.get(ctx.guild.roles, name=name)
        if role is None:
            faction = await ctx.guild.create_role(name=name, hoist=True)
            await faction.edit(position=2)
            await ctx.author.add_roles(faction, reason=f"Faction Created By {ctx.author.name}")
            await ctx.send(embed=discord.Embed(title=f"Faction {name} has been created"))
            async with sql.connect("bot.db") as db:
                await db.execute("INSERT INTO Owners(role, owner) VALUES(?, ?)", (name, ctx.author.id))
                await db.execute("INSERT INTO Members(role, id) VALUES(?, ?)", (name, ctx.author.id))
                await db.commit()
            category = await ctx.guild.create_category(name=name)
            role = discord.utils.get(ctx.guild.roles, name=name)
            overwrites = {
                role: discord.PermissionOverwrite(
                    send_messages=True,
                    read_messages=True,
                    mention_everyone=True,
                    read_message_history=True,
                    attach_files=True,
                    view_channel=True
                ),
                ctx.guild.default_role: discord.PermissionOverwrite(
                    send_messages=False,
                    read_messages=False,
                    mention_everyone=False,
                    read_message_history=False,
                    attach_files=False,
                    view_channel=False
                )
            }
            for i in [f"{name}-announcements", f"{name}-general"]:
                channel = await category.create_text_channel(name=i)
                await channel.edit(overwrites=overwrites)
            overwrites = {
                role: discord.PermissionOverwrite(
                    view_channel=True,
                    speak=True,
                    connect=True
                ),
                ctx.guild.default_role: discord.PermissionOverwrite(
                    view_channel=False,
                    speak=False,
                    connect=False
                )
            }
            channel = await category.create_voice_channel(name=f"{name} vc")
            await channel.edit(overwrites=overwrites)
        else:
            await ctx.send(embed=discord.Embed(title=f"Faction {name} already exist", colour=discord.Colour.red()))

@faction.command()
async def invite(ctx, user: discord.User=None):
    if user.id == ctx.author.id or await original_user(ctx, user.id) is False:
        return
    else:
        if user is None:
            await ctx.send("Please specify a member to invite")
        else:
            async with sql.connect("bot.db") as db:
                cursor = await db.execute("SELECT role FROM members WHERE id=?", (ctx.author.id,))
                fetch = await cursor.fetchone()
                if fetch is None:
                    await ctx.send(embed=discord.Embed(title="You are not part of a faction", colour=discord.Colour.red()))
                    return
                else:
                    rolename = fetch[0]
                    if await full(rolename):
                        await ctx.send("Faction is full")
                        return
            member = ctx.guild.get_member(user.id)
            
            message = await user.send(f"{ctx.author.name} has invite you to join {rolename}")
            await ctx.send("Invited")
            await message.add_reaction("\U00002705")
            await message.add_reaction("\U0000274c")
            def checkto(reaction, user):
                return str(reaction.emoji) == "\U00002705" and user != bot.user
            def check(reaction, user):
                return str(reaction.emoji) in ["\U0000274c", "\U00002705"] and user != bot.user
            reaction, subuser = await bot.wait_for('reaction_add', check=check)
            async with sql.connect("bot.db") as db:
                cursor = await db.execute("SELECT owner FROM Owners WHERE role=?", (rolename,))
                fetch = await cursor.fetchone()
                id = fetch[0]
            owner = bot.get_user(int(id))
            if checkto(reaction, user):
                if await full(rolename) is False:
                    role = discord.utils.get(ctx.guild.roles, name=rolename)
                    await member.add_roles(role)
                    await user.send(f"You have been added to faction {rolename}")
                    await owner.send(f"{user.name} has accepted your request into {rolename}")
                    async with sql.connect("bot.db") as db:
                        await db.execute("INSERT INTO members(role, id) VALUES(?, ?)", (rolename, user.id))
                        await db.commit()
                else:
                    await user.send(f"Sorry, the faction {rolename} is currently full")
            else:
                await owner.send(f"{user.name} has declined your request into {rolename}")

@faction.command()
async def join(ctx, name: str):
    if await full(name):
        await ctx.send("Faction is full")
    else:
        async with sql.connect("bot.db") as db:
            cursor = await db.execute("SELECT id FROM members WHERE id=?", (ctx.author.id,))
            fetch = await cursor.fetchone()
            if fetch is None:
                cursor = await db.execute("SELECT owner FROM Owners WHERE role=?", (name,))
                fetch = await cursor.fetchone()
                if fetch is None:
                    await ctx.send(embed=discord.Embed(title="That faction does not exist", colour=discord.Colour.red()))
                else:
                    role = fetch[0]
                    user = bot.get_user(int(role))
                    await ctx.send(f"Asked {user.name} for entry to {name}")
                    message = await user.send(f"{ctx.author.name} has asked to join your faction")
                    await message.add_reaction("\U00002705")
                    await message.add_reaction("\U0000274c")
                    def checkto(reaction, user):
                        return str(reaction.emoji) == "\U00002705"
                    def check(reaction, user):
                        return str(reaction.emoji) in ["\U0000274c", '\U00002705'] and user != bot.user
                    reaction, user = await bot.wait_for('reaction_add', check=check)
                    if checkto(reaction, user):
                        if await full(name) is False:
                            role = discord.utils.get(ctx.guild.roles, name=name)
                            await ctx.author.add_roles(role)
                            await ctx.author.send(f"You have been accepted to join {name}")
                            await db.execute("INSERT INTO members(role, id) VALUES(?, ?)", (name, ctx.author.id))
                            await db.commit()
                        else:
                            await ctx.author.send(f"Sorry, the faction {name} is currently full")
                    else:
                        await ctx.author.send(f"You have been declined to join {name}")
            else:
                await ctx.send("You already are in a faction")


@faction.command()
async def leave(ctx):
    def check_mark(reaction, user):
        return reaction.emoji == "\U00002705" and user == ctx.author
    def check(reaction, user):
        return reaction.emoji in ["\U0000274c", '\U00002705'] and user == ctx.author
    async with sql.connect("bot.db") as db:
        cursor = await db.execute("SELECT role FROM members WHERE id=?", (ctx.author.id,))
        fetch = await cursor.fetchone()
        if fetch is None:
            await ctx.send("You are not in a faction")
        else:
            cursor = await db.execute("SELECT owner FROM owners WHERE owner=?", (ctx.author.id,))
            fetch = await cursor.fetchone()
            if fetch is None:
                cursor = await db.execute("SELECT role FROM members WHERE id=?", (ctx.author.id,))
                fetch = await cursor.fetchone()
                role = discord.utils.get(ctx.guild.roles, name=fetch[0])
                await ctx.author.remove_roles(role)
                cursor = await db.execute("SELECT owner FROM owners WHERE role=?", (fetch[0],))
                fetch = await cursor.fetchone()
                user = bot.get_user(int(fetch[0]))
                await ctx.send("Left Faction")
                await user.send(f"{ctx.author.mention} has left your faction")
                await db.execute("DELETE FROM members WHERE id=?", (ctx.author.id,))
                await db.commit()
            else:
                message = await ctx.send("WARNING: This will delete your faction entirely. Select a reaction to approve!")
                await message.add_reaction("\U00002705")
                await message.add_reaction("\U0000274c")
                reaction, user = await bot.wait_for('reaction_add', check=check)
                if check_mark(reaction, user):
                    cursor = await db.execute("SELECT role FROM owners WHERE owner=?", (ctx.author.id,))
                    fetch = await cursor.fetchone()
                    await db.execute("DELETE FROM members WHERE role=?", (fetch[0],))
                    await db.execute("DELETE FROM owners WHERE role=?", (fetch[0],))
                    await db.commit()
                    await ctx.send("Left faction")
                    for channel in ctx.guild.channels:
                        if str(channel).lower().__contains__(fetch[0].lower()):
                            await channel.delete()
                    role = discord.utils.get(ctx.guild.roles, name=fetch[0])
                    await role.delete()
                    await ctx.send("Faction Deleted")
                else:
                    await ctx.send("Deletion Aborted")

@faction.command()
async def kick(ctx, member: discord.Member):
    if ctx.author.id == member.id:
        return
    else:
        user = bot.get_user(member.id)
        async with sql.connect("bot.db") as db:
            cursor = await db.execute("SELECT role FROM Owners WHERE owner=?", (ctx.author.id,))
            fetch = await cursor.fetchone()
            if fetch is None:
                await ctx.send("Permission Denied: You do not own this faction")
                return
            else:
                faction = fetch[0]
                cursor = await db.execute("SELECT role FROM members WHERE id=?", (member.id,))
                fetch = await cursor.fetchone()
                if fetch is None:
                    await ctx.send("You are not in a faction")
                else:
                    if faction == fetch[0]:
                        await user.send(f"You have been kicked from {faction}")
                        role = discord.utils.get(ctx.guild.roles, name=faction)
                        await member.remove_roles(role)
                        await ctx.send(f"Member has been kicked from {faction}")
                        await db.execute("DELETE FROM members WHERE id=?", (member.id,))
                        await db.commit()
                    else:
                        await ctx.send(f"That member is part of the {fetch[0]} faction")

@faction.command(aliases=["colour"])
async def color(ctx, hash: discord.Colour):
    async with sql.connect("bot.db") as db:
        cursor = await db.execute("SELECT role FROM Owners WHERE owner=?", (ctx.author.id,))
        fetch = await cursor.fetchone()
    if fetch[0] is None:
        await ctx.send("Permission Denied: You do not own this faction")
    else:
        role = discord.utils.get(ctx.guild.roles, name=fetch[0])
        try:
            await role.edit(colour=hash)
            await ctx.send("Done")
        except:
            await ctx.send("Wrong Hash or Colour")

@faction.command()
async def rename(ctx, name: str):
    async with sql.connect("bot.db") as db:
        cursor = await db.execute("SELECT role FROM Owners WHERE owner=?", (ctx.author.id,))
        fetch = await cursor.fetchone()
        faction = fetch[0]
        await db.execute("UPDATE members SET role=? WHERE role=?", (name, faction))
        await db.execute("UPDATE owners SET role=? WHERE role=?", (name, faction))
        await db.commit()
    if faction is None:
        await ctx.send("Permission Denied: You do not own this faction")
    else:
        await ctx.send(f"Updated to {name}")
        role = discord.utils.get(ctx.guild.roles, name=faction)
        await role.edit(name=name)
        for channel in ctx.guild.channels:
            channellow = str(channel).lower()
            if channellow.__contains__(faction.lower()):
                if channellow.__contains__("announcements"):
                    await channel.edit(name=f"{name}-announcements")
                elif channellow.__contains__("general"):
                    await channel.edit(name=f"{name}-general")
                elif channellow.__contains__("vc"):
                    await channel.edit(name=f"{name} vc")
                else:
                    await channel.edit(name=name)
                    
"""@bot.command()
async def delete(ctx):
    await ctx.channel.delete()"""

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(error)
    raise error

bot.run("ODUyMjY4OTY5MDkyMTg2MTEy.G5ZdP-.IsFZH5JjTWLXVgzt-I0xecnP-f3oe9CtIiRyIQ")