import discord, asyncio, re, os
from discord import message
from discord.ext import commands
from dotenv import load_dotenv
from utils.database import (
    init_db,
    add_points, 
    is_whitelisted,
    try_claim_reward, try_claim_pog_reward
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
        self.tree.interaction_check = self.restrict_slash_commands

    async def restrict_slash_commands(self, interaction: discord.Interaction) -> bool:
        if interaction.type == discord.InteractionType.application_command:
            EVENT_MANAGER_ROLE_ID = 1508333073668898996
            
            is_admin = interaction.user.guild_permissions.administrator
            is_event_manager = any(role.id == EVENT_MANAGER_ROLE_ID for role in interaction.user.roles)
            
            if not (is_admin or is_event_manager):
                await interaction.response.send_message(
                    "❌ You do not have permission to use Heavenly Court commands.",
                    ephemeral=True
                )
                return False
                
        return True
            
    async def setup_hook(self):
        await init_db()
        await self.load_extension("cogs.points")
        await self.load_extension("cogs.clan")
        await self.load_extension("cogs.auction")
        await self.load_extension("cogs.colors")
        await self.load_extension("cogs.kgiveaway")
        
        from cogs.colors import ColorView
        self.add_view(ColorView())

        await self.tree.sync()

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

    if message.author.id == CARD_COMPANION_ID and message.reference and message.guild is not None:
        try:
            wl_matches = re.findall(r"♡\s+(\d+)", message.content)
            if not wl_matches:
                return
            
            max_wl = max(int(w) for w in wl_matches)


            jump_message_link: list[str] = message.components[0].children[0].url.split("/") # type: ignore
            guild: discord.Guild = message.guild
            drop_channel_id: int = int(jump_message_link[5])
            drop_message_id: int = int(jump_message_link[6])

            drop_channel = guild.get_channel(drop_channel_id)
            if drop_channel is None or drop_channel.type != discord.ChannelType.text:
                return
            drop_message: discord.Message = await drop_channel.fetch_message(drop_message_id)

            await handle_karuta_drop(drop_message, pog=True, max_wl=max_wl)

            
            # for component in message.components:
            #     for child in getattr(component, 'children', [component]):
            #         url = getattr(child, 'url', None)
            #         if url and 'discord.com/channels' in url:
            #             jump_message_id = int(url.split('/'[-1]))


        #     max_wl = max(int(w) for w in wl_matches)
            
        #     user_match = re.search(r"<@!?(\d+)> is dropping", ref_msg.content)
        #     if not user_match:
        #         return
            
        #     user_id = int(user_match.group(1))
        #     if not await is_whitelisted(user_id):
        #         return


            # await add_points(user_id, pts)
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
        isRW = await try_claim_reward(payload.message_id)
        guild = bot.get_guild(payload.guild_id)
        await log(guild, f"Message edited: {payload.message_id} | already rewarded: {isRW}")
        if not isRW:
            return
        try:
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
                    await add_points(user.id, WORK_POINTS)
                    await channel.send(
                        f"{user.display_name} earned **{WORK_POINTS}** contribution points for working! ✦",
                        delete_after=10
                    )
                    await log(channel.guild, f"⚒️ `+{WORK_POINTS}` → {user} | kwork | {message.created_at.strftime('%Y-%m-%d %H:%M')}")
        except Exception as e:
            print(f"kwork error: {e}")
            
async def handle_karuta_drop(message: discord.Message, pog: bool = False, max_wl: int = 0): 
    if message.author.id != KARUTA_BOT_ID or message.guild is None:
        return
    if message.channel.id != 1473256666894962712:
        return
    if "is dropping" in message.content:
        print(f"Karuta drop detected in message {message.id}")
        if not await try_claim_reward(message.id) and not pog:
            await log(message.guild, f"Drop already rewarded for message {message.id}")
            print("Drop already rewarded, skipping...")
            return
        if pog and not await try_claim_pog_reward(message.id):
            return
        try:
            match = re.search(r"<@!?(\d+)> is dropping", message.content)
            print(f"Drop user match: {match}")
            if match:
                user_id = int(match.group(1))
                user = await bot.fetch_user(user_id)
                isWL = await is_whitelisted(user_id)
                if isWL:
                    if pog:
                        if max_wl < 200:
                            pts = 5
                        elif max_wl < 500:
                            pts = 8
                        elif max_wl < 1000:
                            pts = 15
                        else:
                            pts = 25
                    else:
                        pts = DROP_POINTS
                    if is_weekend():
                        pts *= 2
                    await add_points(user_id, pts)
                    weekend_text = " (weekend 2x bonus)" if is_weekend() else ""
                    if not pog:
                        await message.channel.send(
                            f"{user.display_name} earned **{pts}** contribution points for dropping{weekend_text}! ✦",
                            delete_after=10
                        )
                        await log(
                            message.guild,
                            f"🃏 `+{pts}` → {user.display_name} | drop{weekend_text} | {message.created_at.strftime('%Y-%m-%d %H:%M')}"
                        )
                    else:
                        await message.channel.send(
                            f"{user.display_name} earned **{pts}** contribution points for pog drop (max WL: {max_wl})! ✦",
                            delete_after=10
                        )
                        await log(
                            message.guild, 
                            f"🌟 `+{pts}` → {user.display_name} | pog drop (max WL: {max_wl}) | {message.created_at.strftime('%Y-%m-%d %H:%M')}"
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
        value="`，points` — check your points\n`，points @user` — check someone's points\n`，leaderboard` — top 10 members",
        inline=False
    )
    embed.add_field(
        name="⚙️ Staff",
        value="`，points add @user amount` — give points\n`，points remove @user amount` — remove points\n`，points set @user amount` — set exact points\n`，points reset @user` — wipe to zero\n`，clan add @user` — add to kwork whitelist\n`，clan remove @user` — remove from whitelist\n`，clan list` — view whitelist",
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