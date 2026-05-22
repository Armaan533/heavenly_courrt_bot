import discord, asyncio, re, os
from discord.ext import commands
from dotenv import load_dotenv
from utils.database import (
    add_points, 
    is_whitelisted, add_to_whitelist, remove_from_whitelist, get_whitelist,
    is_rewarded, mark_as_rewarded
)
from utils.helpers import is_weekend
from constants import *
load_dotenv()

TOKEN = os.getenv("TOKEN")


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=",", intents=intents)
    
    async def setup_hook(self):
        await self.load_extension("cogs.points")
        await self.load_extension("cogs.clan")

bot = Bot()


async def log(guild: discord.Guild | None, text: str):
    if not LOG_CHANNEL_ID or guild is None:
        return
    ch = guild.get_channel(LOG_CHANNEL_ID)
    if ch and ch.type == discord.ChannelType.text:
        await ch.send(text)


@bot.event
async def on_ready():
    print(f"✦ Heavenly Court bot online as {bot.user}")

@bot.event
async def on_message(message: discord.Message):
    if (
    message.author.bot
    and message.author.id != ARCANE_BOT_ID
    and message.author.id != KARUTA_BOT_ID
    and message.author.id != CARD_COMPANION_ID
):
        return
    
    if message.author.id == ARCANE_BOT_ID and message.guild is not None:
        match = re.search(r"<@!?(\d+)> has ascended to level \*\*(\d+)\*\*", message.content)
        if match:
            user_id = int(match.group(1))
            user_obj = await bot.fetch_user(user_id)
            level   = int(match.group(2))
            pts     = RANK_MILESTONES.get(level, LEVELUP_POINTS)
            is_rank = level in RANK_MILESTONES
            await add_points(user_id, pts)
            if is_rank:
                await message.channel.send(
                    f"<@{user_id}> ascended to a new rank and earned **{pts}** contribution points! ✦",
                    delete_after=15
                )
            else:
                await message.channel.send(
                    f"{user_obj.display_name} leveled up and earned **{pts}** contribution points! ✦",
                    delete_after=10
                )
            label = "rank milestone" if is_rank else "level up"
            await log(message.guild, f"⬆️ `+{pts}` → <@{user_id}> | {label} (lv{level}) | {message.created_at.strftime('%Y-%m-%d %H:%M')}")
        return

    await handle_karuta_drop(message)

    if message.author.id == CARD_COMPANION_ID and message.channel.id == POG_DROPS_CHANNEL and message.guild is not None:
        try:
            match_user = re.search(r"<@!?(\d+)> is dropping", message.content)
            match_wl   = re.search(r"♡\s+(\d+)", message.content)
            if match_user and match_wl:
                user_id = int(match_user.group(1))
                wl      = int(match_wl.group(1))
                if wl < 200:
                    pts = 5
                elif wl < 500:
                    pts = 8
                elif wl < 1000:
                    pts = 15
                else:
                    pts = 25
            if await is_whitelisted(user_id):
                await add_points(user_id, pts)
                await log(message.guild, f"🌟 `+{pts}` → <@{user_id}> | pog drop (WL: {wl}) | {message.created_at.strftime('%Y-%m-%d %H:%M')}")
        except Exception as e:
            print(f"pog drop error: {e}")

    await bot.process_commands(message)

@bot.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
    if payload.data.get("author", {}).get("id") != str(KARUTA_BOT_ID):
        return

    embeds = payload.data.get("embeds", [])
    if not embeds:
        return

    embed = embeds[0]
    description = embed.get("description", "")
    title = embed.get("title", "")

    if title == "Work" and "Your workers have finished their tasks." in description and payload.guild_id is not None:
        isRW = await is_rewarded(payload.message_id)
        print(f"Message edited: {payload.message_id} | already rewarded: {isRW}")
        if isRW:
            return
        try:
            guild = bot.get_guild(payload.guild_id)
            if guild is None:
                return
            channel = guild.get_channel(payload.channel_id)
            if channel is None or channel.type != discord.ChannelType.text:
                return
            message = await channel.fetch_message(payload.message_id)
            if message.reference and message.reference.message_id:
                ref  = await channel.fetch_message(message.reference.message_id)
                user = ref.author
                isWL = await is_whitelisted(user.id)
                if isWL:
                    await mark_as_rewarded(payload.message_id)
                    await add_points(user.id, WORK_POINTS)
                    await channel.send(
                        f"{user.display_name} earned **{WORK_POINTS}** contribution points for working! ✦",
                        delete_after=10
                    )
                    await log(channel.guild, f"⚒️ `+{WORK_POINTS}` → {user} | kwork | {message.created_at.strftime('%Y-%m-%d %H:%M')}")
        except Exception as e:
            print(f"kwork error: {e}")
            
async def handle_karuta_drop(message: discord.Message):
    if message.author.id != KARUTA_BOT_ID or message.guild is None:
        return
    if message.channel.id != 1473256666894962712:
        return
    if await is_rewarded(message.id):
        return
    if "is dropping" in message.content:
        try:
            match = re.search(r"<@!?(\d+)> is dropping", message.content)
            if match:
                user_id = int(match.group(1))
                user = await bot.fetch_user(user_id)
                if await is_whitelisted(user_id):
                    pts = DROP_POINTS * 2 if is_weekend() else DROP_POINTS
                    await mark_as_rewarded(message.id)
                    await add_points(user_id, pts)
                    weekend_text = " (weekend 2x bonus)" if is_weekend() else ""
                    await message.channel.send(
                        f"{user.display_name} earned **{pts}** contribution points for dropping{weekend_text}! ✦",
                        delete_after=10
                    )
                    await log(
                        message.guild,
                        f"🃏 `+{pts}` → <@{user_id}> | drop{weekend_text} | {message.created_at.strftime('%Y-%m-%d %H:%M')}"
                    )
        except Exception as e:
            print(f"drop error: {e}")


# @bot.command(name="clanlist")
# @commands.has_permissions(manage_guild=True)
# async def clanlist_cmd(ctx):
#     # cur.execute("SELECT user_id FROM whitelist")
#     # rows = cur.fetchall()
    
#     rows = await get_whitelist()
#     if len(rows) == 0:
#         return await ctx.send("No clan members in whitelist.")
#     lines = [f"<@{uid}>" for uid in rows]
#     embed = discord.Embed(title="✦ Clan Whitelist", description="\n".join(lines), color=EMBED_COLOR)
#     await ctx.send(embed=embed)



@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use that.", delete_after=5)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("Member not found.", delete_after=5)
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Invalid argument.", delete_after=5)

bot.remove_command("help")

@bot.command(name="help")
async def help_cmd(ctx):
    embed = discord.Embed(title="✦ Heavenly Court", description="Contribution system commands", color=EMBED_COLOR)
    embed.add_field(
        name="👤 Members",
        value="`，bal` — check your points\n`，bal @user` — check someone's points\n`，leaderboard` — top 10 members",
        inline=False
    )
    embed.add_field(
        name="⚙️ Staff",
        value="`，give @user amount` — give points\n`，remove @user amount` — remove points\n`，setpoints @user amount` — set exact points\n`，resetpoints @user` — wipe to zero\n`，addclan @user` — add to kwork whitelist\n`，removeclan @user` — remove from whitelist\n`，clanlist` — view whitelist",
        inline=False
    )
    embed.set_footer(text="Heavenly Court ✦ contribution system")
    await ctx.send(embed=embed)

async def bot_start():
    if TOKEN is None:
        print("Error: TOKEN not found in environment variables.")
        return
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(bot_start())