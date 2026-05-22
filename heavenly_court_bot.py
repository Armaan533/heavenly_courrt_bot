from email.mime import message

import discord
from discord.ext import commands
import sqlite3
import re
import os
from dotenv import load_dotenv
load_dotenv()

TOKEN          = os.getenv("TOKEN")
KARUTA_BOT_ID  = 646937666251915264
ARCANE_BOT_ID  = 437808476106784770
LOG_CHANNEL_ID = 1504005514210578443

DROP_POINTS    = 2
WORK_POINTS    = 10
LEVELUP_POINTS = 10

RANK_MILESTONES = {
    5:  100,
    15: 200,
    30: 400,
    50: 800,
    75: 1600,
}

EMBED_COLOR = 0xc9a0dc

conn = sqlite3.connect("points.db")
cur  = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS points (
        user_id INTEGER PRIMARY KEY,
        points  INTEGER DEFAULT 0
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS whitelist (
        user_id INTEGER PRIMARY KEY
    )
""")
cur.execute("""
    CREATE TABLE IF NOT EXISTS rewarded (
        message_id INTEGER PRIMARY KEY
    )
""")
conn.commit()

def get_points(user_id: int) -> int:
    cur.execute("SELECT points FROM points WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    return row[0] if row else 0

def add_points(user_id: int, amount: int):
    cur.execute("""
        INSERT INTO points (user_id, points) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET points = points + ?
    """, (user_id, amount, amount))
    conn.commit()

def remove_points(user_id: int, amount: int) -> int:
    new_val = max(0, get_points(user_id) - amount)
    cur.execute("""
        INSERT INTO points (user_id, points) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET points = ?
    """, (user_id, new_val, new_val))
    conn.commit()
    return new_val

def set_points(user_id: int, amount: int):
    cur.execute("""
        INSERT INTO points (user_id, points) VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET points = ?
    """, (user_id, amount, amount))
    conn.commit()

def get_leaderboard(limit: int = 10):
    cur.execute("SELECT user_id, points FROM points ORDER BY points DESC LIMIT ?", (limit,))
    return cur.fetchall()

def is_whitelisted(user_id: int) -> bool:
    cur.execute("SELECT 1 FROM whitelist WHERE user_id = ?", (user_id,))
    return cur.fetchone() is not None

def add_to_whitelist(user_id: int):
    cur.execute("INSERT OR IGNORE INTO whitelist (user_id) VALUES (?)", (user_id,))
    conn.commit()

def remove_from_whitelist(user_id: int):
    cur.execute("DELETE FROM whitelist WHERE user_id = ?", (user_id,))
    conn.commit()

def is_rewarded(message_id: int) -> bool:
    cur.execute("SELECT 1 FROM rewarded WHERE message_id = ?", (message_id,))
    return cur.fetchone() is not None

def mark_rewarded(message_id: int):
    cur.execute("INSERT OR IGNORE INTO rewarded (message_id) VALUES (?)", (message_id,))
    conn.commit()

def is_weekend() -> bool:
    from datetime import datetime
    return datetime.utcnow().weekday() >= 5

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=",", intents=intents)

async def log(guild: discord.Guild, text: str):
    if not LOG_CHANNEL_ID:
        return
    ch = guild.get_channel(LOG_CHANNEL_ID)
    if ch:
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
):
        return
    
    if message.author.id == ARCANE_BOT_ID:
        match = re.search(r"<@!?(\d+)> has ascended to level \*\*(\d+)\*\*", message.content)
        if match:
            user_id = int(match.group(1))
            level   = int(match.group(2))
            pts     = RANK_MILESTONES.get(level, LEVELUP_POINTS)
            is_rank = level in RANK_MILESTONES
            add_points(user_id, pts)
            if is_rank:
                await message.channel.send(
                    f"<@{user_id}> ascended to a new rank and earned **{pts}** contribution points! ✦",
                    delete_after=15
                )
            else:
                await message.channel.send(
                    f"<@{user_id} leveled up and earned **{pts}** contribution points! ✦",
                    delete_after=10
                )
            label = "rank milestone" if is_rank else "level up"
            await log(message.guild, f"⬆️ `+{pts}` → <@{user_id}> | {label} (lv{level}) | {message.created_at.strftime('%Y-%m-%d %H:%M')}")
        return

    await handle_karuta_drop(message)

    await bot.process_commands(message)

@bot.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
    if payload.data.get("author", {}).get("id") != str(KARUTA_BOT_ID):
        return

    if is_rewarded(payload.message_id):
        return

    embeds = payload.data.get("embeds", [])
    if not embeds:
        return

    embed = embeds[0]
    description = embed.get("description", "")
    title = embed.get("title", "")

    if title == "Work" and "Your workers have finished their tasks." in description:
        try:
            channel = bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            if message.reference:
                ref  = await channel.fetch_message(message.reference.message_id)
                user = ref.author
                if is_whitelisted(user.id):
                    mark_rewarded(payload.message_id)
                    add_points(user.id, WORK_POINTS)
                    await channel.send(
                        f"<@{user.id}> earned **{WORK_POINTS}** contribution points for working! ✦",
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
    if is_rewarded(message.id):
        return
    if "is dropping" in message.content:
        try:
            match = re.search(r"<@!?(\d+)> is dropping", message.content)
            if match:
                user_id = int(match.group(1))
                user = await bot.fetch_user(user_id)
                if is_whitelisted(user_id):
                    pts = DROP_POINTS * 2 if is_weekend() else DROP_POINTS
                    mark_rewarded(message.id)
                    add_points(user_id, pts)
                    weekend_text = " (weekend 2x bonus)" if is_weekend() else ""
                    await message.channel.send(
                        f"<@{user.display_name}> earned **{pts}** contribution points for dropping{weekend_text}! ✦",
                        delete_after=10
                    )
                    await log(
                        message.guild,
                        f"🃏 `+{pts}` → <@{user_id}> | drop{weekend_text} | {message.created_at.strftime('%Y-%m-%d %H:%M')}"
                    )
        except Exception as e:
            print(f"drop error: {e}")

@bot.command(name="addclan")
@commands.has_permissions(manage_guild=True)
async def addclan_cmd(ctx, member: discord.Member):
    add_to_whitelist(member.id)
    await ctx.send(embed=discord.Embed(
        description=f"✦ {member.mention} added to clan whitelist.",
        color=EMBED_COLOR
    ))

@bot.command(name="removeclan")
@commands.has_permissions(manage_guild=True)
async def removeclan_cmd(ctx, member: discord.Member):
    remove_from_whitelist(member.id)
    await ctx.send(embed=discord.Embed(
        description=f"✦ {member.mention} removed from clan whitelist.",
        color=EMBED_COLOR
    ))

@bot.command(name="clanlist")
@commands.has_permissions(manage_guild=True)
async def clanlist_cmd(ctx):
    cur.execute("SELECT user_id FROM whitelist")
    rows = cur.fetchall()
    if not rows:
        return await ctx.send("No clan members in whitelist.")
    lines = [f"<@{uid}>" for (uid,) in rows]
    embed = discord.Embed(title="✦ Clan Whitelist", description="\n".join(lines), color=EMBED_COLOR)
    await ctx.send(embed=embed)

@bot.command(name="give")
@commands.has_permissions(manage_guild=True)
async def give_points(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send("Amount must be positive.")
    add_points(member.id, amount)
    total = get_points(member.id)
    await ctx.send(embed=discord.Embed(
        description=f"✦ Gave **{amount}** points to {member.mention}. Total: **{total}**",
        color=EMBED_COLOR
    ))
    await log(ctx.guild, f"➕ `+{amount}` → {member} | by {ctx.author} | total: {total}")

@bot.command(name="remove")
@commands.has_permissions(manage_guild=True)
async def remove_cmd(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.send("Amount must be positive.")
    new_total = remove_points(member.id, amount)
    await ctx.send(embed=discord.Embed(
        description=f"✦ Removed **{amount}** points from {member.mention}. Total: **{new_total}**",
        color=EMBED_COLOR
    ))
    await log(ctx.guild, f"➖ `-{amount}` → {member} | by {ctx.author} | total: {new_total}")

@bot.command(name="setpoints")
@commands.has_permissions(administrator=True)
async def setpoints_cmd(ctx, member: discord.Member, amount: int):
    set_points(member.id, amount)
    await ctx.send(embed=discord.Embed(
        description=f"✦ Set {member.mention}'s points to **{amount}**",
        color=EMBED_COLOR
    ))

@bot.command(name="bal", aliases=["balance", "points", "cp"])
async def balance_cmd(ctx, member: discord.Member = None):
    target = member or ctx.author
    pts = get_points(target.id)
    embed = discord.Embed(title="✦ Contribution Points", color=EMBED_COLOR)
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name=target.display_name, value=f"**{pts}** points")
    await ctx.send(embed=embed)

@bot.command(name="leaderboard", aliases=["lb", "top"])
async def leaderboard_cmd(ctx):
    rows = get_leaderboard(10)
    embed = discord.Embed(title="✦ Contribution Leaderboard", color=EMBED_COLOR)
    medals = {0: "🥇", 1: "🥈", 2: "🥉"}
    if not rows:
        embed.description = "No points recorded yet."
    else:
        lines = []
        for i, (user_id, points) in enumerate(rows):
            try:
                user = await bot.fetch_user(user_id)
                name = user.display_name
            except Exception:
                name = f"Unknown ({user_id})"
            prefix = medals.get(i, f"**{i+1}.**")
            lines.append(f"{prefix} {name} — **{points}** pts")
        embed.description = "\n".join(lines)
    await ctx.send(embed=embed)

@bot.command(name="resetpoints")
@commands.has_permissions(administrator=True)
async def reset_cmd(ctx, member: discord.Member):
    set_points(member.id, 0)
    await ctx.send(embed=discord.Embed(
        description=f"✦ Reset {member.mention}'s points to 0.",
        color=EMBED_COLOR
    ))

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

bot.run(TOKEN)