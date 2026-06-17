import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import time
import random
from utils.database import get_all_giveaways, save_giveaways_data

E_SPARKLE = "<:eight_side_sparkle:1516681364806570105>"    
E_ITEM    = "<:red_lotus:1516679367743377448>"   
E_CHAR    = "<:red_lotus:1516679367743377448>"   
E_SERIES  = "<:book_ig:1516683126066253844>"    
E_CARD    = "<:two_flowers:1516684386546880614>"    
E_TIME    = "<:celestial_hourglass:1516684938509029396>"   
E_SUCCESS = "✅"    
E_ERROR   = "❌"    


def parse_time(time_str: str) -> int:
    time_str = time_str.lower().strip()
    if time_str.endswith('d'): return int(time_str[:-1]) * 86400
    if time_str.endswith('h'): return int(time_str[:-1]) * 3600
    if time_str.endswith('m'): return int(time_str[:-1]) * 60
    if time_str.endswith('s'): return int(time_str[:-1])
    if time_str.isdigit(): return int(time_str) * 60 
    raise ValueError("Invalid format")

class GiveawayEntryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enter Giveaway", style=discord.ButtonStyle.green, custom_id="claim_gaw_entry")
    async def enter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg_id = str(interaction.message.id)
        data = await get_all_giveaways() 
        
        if msg_id not in data["active"]:
            return await interaction.response.send_message(f"{E_ERROR} This giveaway is no longer active or the artifact has dispersed.", ephemeral=True)
            
        gaw = data["active"][msg_id]
        user_id = interaction.user.id
        
        if user_id in gaw["participants"]:
            return await interaction.response.send_message(f"{E_ERROR} You have already entered this giveaway.", ephemeral=True)
            
        entries = 1 
        user_role_ids = [role.id for role in interaction.user.roles]
        
        if 1504127544801366128 in user_role_ids:
            entries += gaw.get("clan_bonus", 0)
        if 1474356762063667210 in user_role_ids:
            entries += gaw.get("booster_bonus", 0)
                
        gaw["participants"].append(user_id)
        for _ in range(entries):
            gaw["tickets"].append(user_id)
            
        await save_giveaways_data(data)
        
        button.label = f"Enter Giveaway ({len(gaw['participants'])})"
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(f"{E_SUCCESS} Successfully entered the giveaway!", ephemeral=True)

class ItemSetupModal(discord.ui.Modal, title="Setup Item Giveaway"):
    item_name = discord.ui.TextInput(label="Item Name")
    description = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph)
    duration = discord.ui.TextInput(label="Duration (e.g., 10m, 2h, 1d)", placeholder="10m, 2h, 1d")

    def __init__(self, cog, clan_bonus: int, booster_bonus: int):
        super().__init__()
        self.cog = cog
        self.clan_bonus = clan_bonus
        self.booster_bonus = booster_bonus

    async def on_submit(self, interaction: discord.Interaction):
        try:
            seconds = parse_time(self.duration.value)
        except ValueError:
            return await interaction.response.send_message(f"{E_ERROR} Invalid duration.", ephemeral=True)

        end_time = int(time.time()) + seconds
        
        desc = f"{E_SPARKLE} *An artifact has been offered to the sect.*\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        desc += f"{E_ITEM} **Item:** {self.item_name.value}\n"
        desc += f"📜 **Description:** {self.description.value}\n\n"
        
        if self.clan_bonus > 0 or self.booster_bonus > 0:
            desc += f"{E_SPARKLE} **Bonus Entries:**\n"
            if self.clan_bonus > 0: desc += f"✦ Clan Members: `+{self.clan_bonus}`\n"
            if self.booster_bonus > 0: desc += f"✦ Boosters: `+{self.booster_bonus}`\n"
            desc += "\n"
            
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        desc += f"{E_TIME} **Ends:** <t:{end_time}:R>"
        
        embed = discord.Embed(title="✦ . __HEAVENLY COURT GIVEAWAY__ . ✦", description=desc, color=0x6b1614)
        embed.set_footer(text=f"Hosted by {interaction.user.display_name}")

        view = GiveawayEntryView()
        await interaction.response.send_message(f"{E_SUCCESS} Giveaway started!", ephemeral=True)
        msg = await interaction.channel.send(embed=embed, view=view)

        data = await get_all_giveaways()
        data["active"][str(msg.id)] = {
            "channel_id": interaction.channel.id,
            "prize": self.item_name.value,
            "end_time": end_time,
            "tickets": [],
            "participants": [],
            "clan_bonus": self.clan_bonus,
            "booster_bonus": self.booster_bonus
        }
        await save_giveaways_data(data)

        task = asyncio.create_task(self.cog.manage_giveaway_timer(seconds, msg.id, interaction.channel.id, self.item_name.value))
        self.cog.active_tasks[msg.id] = task

class CardConfigModal(discord.ui.Modal, title="Configure Card Giveaway"):
    duration = discord.ui.TextInput(label="Duration (e.g., 10m, 2h, 1d)", placeholder="10m, 2h, 1d")

    def __init__(self, cog, clan_bonus: int, booster_bonus: int):
        super().__init__()
        self.cog = cog
        self.clan_bonus = clan_bonus
        self.booster_bonus = booster_bonus

    async def on_submit(self, interaction: discord.Interaction):
        try:
            seconds = parse_time(self.duration.value)
        except ValueError:
            return await interaction.response.send_message(f"{E_ERROR} Invalid duration.", ephemeral=True)

        await interaction.response.send_message(f"{E_SUCCESS} Configuration saved! **{interaction.user.mention}, please run `kci <card_code>` in this channel now.**", ephemeral=False)
        await self.cog.wait_for_kci(interaction, seconds, self.clan_bonus, self.booster_bonus)

class GiveawayTypeSelect(discord.ui.View):
    def __init__(self, cog, author, clan_bonus, booster_bonus):
        super().__init__(timeout=60)
        self.cog = cog
        self.author = author
        self.clan_bonus = clan_bonus
        self.booster_bonus = booster_bonus

    @discord.ui.button(label="Karuta Card", style=discord.ButtonStyle.primary)
    async def card_choice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(f"{E_ERROR} This belongs to someone else.", ephemeral=True)
        await interaction.response.send_modal(CardConfigModal(self.cog, self.clan_bonus, self.booster_bonus))
        self.stop()

    @discord.ui.button(label="Item", style=discord.ButtonStyle.secondary)
    async def item_choice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message(f"{E_ERROR} This belongs to someone else.", ephemeral=True)
        await interaction.response.send_modal(ItemSetupModal(self.cog, self.clan_bonus, self.booster_bonus))
        self.stop()

class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(GiveawayEntryView()) 
        self.active_tasks = {}
        self.bot.loop.create_task(self.resume_giveaways())
        
    giveaway_group = app_commands.Group(name="giveaway", description="Manage giveaways")

    async def resume_giveaways(self):
        data = await get_all_giveaways()
        current_time = int(time.time())
        
        for msg_id_str, gaw in list(data["active"].items()):
            msg_id = int(msg_id_str)
            seconds_left = gaw["end_time"] - current_time
            
            if seconds_left <= 0:
                task = asyncio.create_task(self.determine_winner(msg_id, gaw["channel_id"], gaw["prize"]))
            else:
                task = asyncio.create_task(self.manage_giveaway_timer(seconds_left, msg_id, gaw["channel_id"], gaw["prize"]))
            self.active_tasks[msg_id] = task

    async def manage_giveaway_timer(self, seconds, message_id, channel_id, prize_name):
        await asyncio.sleep(seconds)
        await self.determine_winner(message_id, channel_id, prize_name)

    async def determine_winner(self, message_id, channel_id, prize_name):
        data = await get_all_giveaways()
        msg_id_str = str(message_id)
        
        if msg_id_str not in data["active"]:
            return
            
        gaw_data = data["active"].pop(msg_id_str)
        tickets = gaw_data["tickets"]
        
        data["ended"][msg_id_str] = {"tickets": tickets, "prize": prize_name}
        await save_giveaways_data(data)
        
        self.active_tasks.pop(message_id, None)

        channel = self.bot.get_channel(channel_id)
        if not channel: return

        try:
            target_msg = await channel.fetch_message(message_id)
            embed = target_msg.embeds[0]
        except: return

        if not tickets:
            embed.description = f"{E_SPARKLE} *The giveaway has concluded.* {E_SPARKLE}\n━━━━━━━━━━━━━━━━━━━━━━\n{E_CHAR} **Winner:** None"
            await target_msg.edit(embed=embed, view=None)
            await channel.send(f"The pavilion closes. The giveaway for **{prize_name}** ended with no entries.")
            return

        winner_user = await self.bot.fetch_user(random.choice(tickets))
        embed.description = f"{E_SPARKLE} *The giveaway has concluded.* {E_SPARKLE}\n━━━━━━━━━━━━━━━━━━━━━━\n{E_CHAR} **Winner:** {winner_user.mention}"
        await target_msg.edit(embed=embed, view=None)
        
        await channel.send(f"🎊 The heavens have chosen! {winner_user.mention} has won **{prize_name}**! Open a ticket to claim in <#1509258805777666180>")

    async def wait_for_kci(self, interaction, seconds, clan_bonus, booster_bonus):
        channel = interaction.channel
        author = interaction.user

        def karuta_check(m):
            return (m.author.id == 646937666251915264 and m.channel.id == channel.id and len(m.embeds) > 0 and "Card Details" in (m.embeds[0].title or ""))

        try:
            karuta_msg = await self.bot.wait_for('message', timeout=120.0, check=karuta_check)
            # ⏳ Delay to allow Discord to fully load and proxy the image URL
            await asyncio.sleep(1.5)
            karuta_msg = await channel.fetch_message(karuta_msg.id)
        except asyncio.TimeoutError:
            return await channel.send(f"{E_ERROR} Setup timed out.")
        except discord.NotFound:
            pass 

        embed_data = karuta_msg.embeds[0]
        lines = [l.strip() for l in (embed_data.description or "").split("\n") if l.strip()]
        if not lines: return await channel.send(f"{E_ERROR} Could not read card metadata.")

        stats_line = lines[0]
        for line in lines:
            if "·" in line and "#" in line: 
                stats_line = line
                break

        parts = [p.strip().replace("*", "").replace("`", "") for p in stats_line.split("·") if "★" not in p and "☆" not in p]
        
        code = parts[0] if len(parts) > 0 else "Unknown"
        print_num = parts[1] if len(parts) > 1 else "Unknown"
        edition = parts[2] if len(parts) > 2 else "Unknown"
        series = parts[3] if len(parts) > 3 else "Unknown"
        character_name = parts[-1] if len(parts) > 0 else "Unknown"
        
        # Safely extract image whether Karuta formats it as a thumbnail or a full image
        card_image_url = None
        if embed_data.thumbnail and embed_data.thumbnail.url:
            card_image_url = embed_data.thumbnail.url
        elif embed_data.image and embed_data.image.url:
            card_image_url = embed_data.image.url

        end_time = int(time.time()) + seconds

        desc = f"{E_SPARKLE} *A new treasure has entered the pavilion.*\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        desc += f"{E_CHAR} **Character:** {character_name}\n"
        if series != "Unknown" and series != character_name:
            desc += f"{E_SERIES} **Series:** {series}\n\n"
        else:
            desc += "\n"
        
        desc += f"{E_CARD} **Card Details:**\n"
        desc += f"> **Code:** `{code}`  |  **Print:** `{print_num}`  |  **Edition:** `{edition}`\n\n"
        
        if clan_bonus > 0 or booster_bonus > 0:
            desc += f"{E_SPARKLE} **Bonus Entries:**\n"
            if clan_bonus > 0: desc += f"✦ Clan Members: `+{clan_bonus}`\n"
            if booster_bonus > 0: desc += f"✦ Boosters: `+{booster_bonus}`\n"
            desc += "\n"
            
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        desc += f"{E_TIME} **Ends:** <t:{end_time}:R>"

        giveaway_embed = discord.Embed(title="✦ . HEAVENLY COURT GIVEAWAY . ✦", description=desc, color=0x6b1614)
        giveaway_embed.set_footer(text=f"Hosted by {author.display_name}")
        if card_image_url: giveaway_embed.set_thumbnail(url=card_image_url)

        try:
            setup_msg = await interaction.original_response()
            await setup_msg.delete()
        except: pass

        try:
            await karuta_msg.delete()
        except: pass

        try:
            async for hist_msg in channel.history(limit=10):
                if hist_msg.author.id == author.id and hist_msg.content.lower().startswith("kci"):
                    await hist_msg.delete()
                    break
        except: pass

        msg = await channel.send(embed=giveaway_embed, view=GiveawayEntryView())

        data = await get_all_giveaways()
        data["active"][str(msg.id)] = {
            "channel_id": channel.id,
            "prize": character_name,
            "end_time": end_time,
            "tickets": [],
            "participants": [],
            "clan_bonus": clan_bonus,
            "booster_bonus": booster_bonus
        }
        await save_giveaways_data(data)

        task = asyncio.create_task(self.manage_giveaway_timer(seconds, msg.id, channel.id, character_name))
        self.active_tasks[msg.id] = task

    @giveaway_group.command(name="start", description="Starts a giveaway")
    async def start_wizard(self, interaction: discord.Interaction, clan_bonus: int = 0, booster_bonus: int = 0):
        EVENT_MANAGER_ROLE_ID = 1508333073668898996
        if not (interaction.user.guild_permissions.administrator or any(role.id == EVENT_MANAGER_ROLE_ID for role in interaction.user.roles)):
            return await interaction.response.send_message(f"{E_ERROR} You do not have permission.", ephemeral=True)
        await interaction.response.send_message(embed=discord.Embed(title="Giveaway Setup", description="Select the type:", color=0x6b1614), view=GiveawayTypeSelect(self, interaction.user, clan_bonus, booster_bonus), ephemeral=True)

    @giveaway_group.command(name="cancel", description="Cancels an active giveaway")
    async def cancel_giveaway(self, interaction: discord.Interaction, message_id: str):
        EVENT_MANAGER_ROLE_ID = 1508333073668898996
        if not (interaction.user.guild_permissions.administrator or any(role.id == EVENT_MANAGER_ROLE_ID for role in interaction.user.roles)):
            return await interaction.response.send_message(f"{E_ERROR} You do not have permission.", ephemeral=True)

        data = await get_all_giveaways()
        if message_id not in data["active"]:
            return await interaction.response.send_message(f"{E_ERROR} Giveaway not found.", ephemeral=True)

        gaw = data["active"].pop(message_id)
        await save_giveaways_data(data)
        
        if int(message_id) in self.active_tasks:
            self.active_tasks[int(message_id)].cancel()

        channel = self.bot.get_channel(gaw["channel_id"])
        if channel:
            try:
                msg = await channel.fetch_message(int(message_id))
                embed = msg.embeds[0]
                embed.description = f"{E_SPARKLE} *The giveaway was cancelled.* {E_SPARKLE}"
                await msg.edit(embed=embed, view=None)
            except: pass

        await interaction.response.send_message(f"{E_SUCCESS} Cancelled.", ephemeral=True)

    @giveaway_group.command(name="end", description="Ends an active giveaway immediately")
    async def end_giveaway_early(self, interaction: discord.Interaction, message_id: str):
        EVENT_MANAGER_ROLE_ID = 1508333073668898996
        if not (interaction.user.guild_permissions.administrator or any(role.id == EVENT_MANAGER_ROLE_ID for role in interaction.user.roles)):
            return await interaction.response.send_message(f"{E_ERROR} You do not have permission.", ephemeral=True)

        data = await get_all_giveaways()
        if message_id not in data["active"]:
            return await interaction.response.send_message(f"{E_ERROR} Giveaway not found.", ephemeral=True)

        gaw = data["active"][message_id]
        if int(message_id) in self.active_tasks:
            self.active_tasks[int(message_id)].cancel()

        await interaction.response.send_message("Ending early...", ephemeral=True)
        await self.determine_winner(int(message_id), gaw["channel_id"], gaw["prize"])

    @giveaway_group.command(name="reroll", description="Rerolls a completed giveaway")
    async def reroll_giveaway(self, interaction: discord.Interaction, message_id: str):
        EVENT_MANAGER_ROLE_ID = 1508333073668898996
        if not (interaction.user.guild_permissions.administrator or any(role.id == EVENT_MANAGER_ROLE_ID for role in interaction.user.roles)):
            return await interaction.response.send_message(f"{E_ERROR} You do not have permission.", ephemeral=True)

        data = await get_all_giveaways()
        if message_id not in data["ended"]:
            return await interaction.response.send_message(f"{E_ERROR} History not found.", ephemeral=True)

        tickets = data["ended"][message_id]["tickets"]
        prize = data["ended"][message_id]["prize"]

        if not tickets:
            return await interaction.response.send_message(f"{E_ERROR} No entries.", ephemeral=True)

        winner = await self.bot.fetch_user(random.choice(tickets))
        await interaction.response.send_message(f"{E_SUCCESS} Rerolling...", ephemeral=True)
        await interaction.channel.send(f"🎊 **REROLL!** The heavens chose {winner.mention} for **{prize}**! Claim in <#1509258805777666180>")

async def setup(bot):
    await bot.add_cog(GiveawayCog(bot))