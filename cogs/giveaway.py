import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import time
import random

def parse_time(time_str: str) -> int:
    time_str = time_str.lower().strip()
    if time_str.endswith('d'): return int(time_str[:-1]) * 86400
    if time_str.endswith('h'): return int(time_str[:-1]) * 3600
    if time_str.endswith('m'): return int(time_str[:-1]) * 60
    if time_str.endswith('s'): return int(time_str[:-1])
    if time_str.isdigit(): return int(time_str) * 60 
    raise ValueError("Invalid format")


class GiveawayEntryView(discord.ui.View):
    def __init__(self, clan_bonus: int = 0, booster_bonus: int = 0):
        super().__init__(timeout=None)
        self.participants = set() 
        self.tickets = []         
        self.clan_bonus = clan_bonus
        self.booster_bonus = booster_bonus

    @discord.ui.button(label="Enter Giveaway (0)", style=discord.ButtonStyle.green, custom_id="claim_gaw_entry")
    async def enter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.participants:
            await interaction.response.send_message("❌ You have already entered this giveaway.", ephemeral=True)
            return
            
        entries = 1 
        user_role_ids = [role.id for role in interaction.user.roles]
        
        if 1504127544801366128 in user_role_ids: 
            entries += self.clan_bonus
        if 1474356762063667210 in user_role_ids: 
            entries += self.booster_bonus
                
        self.participants.add(interaction.user.id)
        
        for _ in range(entries):
            self.tickets.append(interaction.user.id)
            
        button.label = f"Enter Giveaway ({len(self.participants)})"
        await interaction.response.edit_message(view=self)
        
        await interaction.followup.send("✅ Successfully entered the giveaway!", ephemeral=True)


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
            return await interaction.response.send_message("❌ Invalid duration. Use formats like 10m, 2h, or 1d.", ephemeral=True)

        end_time = int(time.time()) + seconds
        
        desc = f"✨ *An item has been offered to the sect.* ✨\n\n"
        desc += f"**୨୧ Item ୨୧**\n{self.item_name.value}\n\n"
        desc += f"**୨୧ Description ୨୧**\n{self.description.value}\n"
        
        if self.clan_bonus > 0 or self.booster_bonus > 0:
            desc += f"\n**୨୧ Bonus Entries ୨୧**\n"
            if self.clan_bonus > 0:
                desc += f"✦ Clan Members: +{self.clan_bonus}\n"
            if self.booster_bonus > 0:
                desc += f"✦ Boosters: +{self.booster_bonus}\n"
                
        desc += f"\n⏰ **Ends:** <t:{end_time}:R>"
        
        embed = discord.Embed(title="✦ . HEAVENLY COURT GIVEAWAY . ✦", description=desc, color=0x2b2d31)
        embed.set_footer(text=f"Hosted by {interaction.user.display_name}")

        await interaction.response.send_message("Giveaway started successfully!", ephemeral=True)
        view = GiveawayEntryView(self.clan_bonus, self.booster_bonus)
        msg = await interaction.channel.send(embed=embed, view=view)

        task = asyncio.create_task(self.cog.manage_giveaway_timer(seconds, msg.id, interaction.channel.id, view, embed, self.item_name.value))
        self.cog.active_giveaways[msg.id] = {"task": task, "view": view, "embed": embed, "prize": self.item_name.value, "channel_id": interaction.channel.id}

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
            return await interaction.response.send_message("❌ Invalid duration. Use formats like 10m, 2h, or 1d.", ephemeral=True)

        await interaction.response.send_message(f"✅ Configuration saved! **{interaction.user.mention}, please run `kci <card_code>` in this channel now.**", ephemeral=False)
        await self.cog.wait_for_kci(interaction.channel, interaction.user, seconds, self.clan_bonus, self.booster_bonus)


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
            return await interaction.response.send_message("❌ This setup session belongs to someone else.", ephemeral=True)
        
        await interaction.response.send_modal(CardConfigModal(self.cog, self.clan_bonus, self.booster_bonus))
        self.stop()

    @discord.ui.button(label="Item", style=discord.ButtonStyle.secondary)
    async def item_choice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ This setup session belongs to someone else.", ephemeral=True)
        
        await interaction.response.send_modal(ItemSetupModal(self.cog, self.clan_bonus, self.booster_bonus))
        self.stop()


class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}
        
    giveaway_group = app_commands.Group(name="giveaway", description="Manage giveaways")

    async def manage_giveaway_timer(self, seconds, message_id, channel_id, view, embed, prize_name):
        await asyncio.sleep(seconds)
        await self.determine_winner(message_id, channel_id, view, embed, prize_name)

    async def determine_winner(self, message_id, channel_id, view, embed, prize_name):
        if message_id not in self.active_giveaways:
            return
            
        self.active_giveaways.pop(message_id, None)
        channel = self.bot.get_channel(channel_id)
        if not channel: return

        try:
            target_msg = await channel.fetch_message(message_id)
        except: return

        winners = view.tickets
        if not winners:
            embed.description = "✨ *The giveaway has concluded.* ✨\n\n**୨୧ Winner ୨୧**\nNone"
            await target_msg.edit(embed=embed, view=None)
            await channel.send(f"The pavilion closes. The giveaway for **{prize_name}** ended with no entries.")
            return

        winner_user = await self.bot.fetch_user(random.choice(winners))
        embed.description = f"✨ *The giveaway has concluded.* ✨\n\n**୨୧ Winner ୨୧**\n{winner_user.mention}"
        await target_msg.edit(embed=embed, view=None)
        
        await channel.send(f"🎊 The heavens have chosen! {winner_user.mention} has won **{prize_name}**! Open a ticket to claim in <#1509258805777666180>")

    # -------- KARUTA CARD CATCHER --------
    async def wait_for_kci(self, channel, author, seconds, clan_bonus, booster_bonus):
        def karuta_check(m):
            return (m.author.id == 646937666251915264 and 
                    m.channel.id == channel.id and 
                    len(m.embeds) > 0 and 
                    "Card Details" in (m.embeds[0].title or ""))

        try:
            karuta_msg = await self.bot.wait_for('message', timeout=120.0, check=karuta_check)
        except asyncio.TimeoutError:
            return await channel.send("❌ Setup timed out. You didn't run the `kci` command in time.")

        embed_data = karuta_msg.embeds[0]
        lines = [l.strip() for l in (embed_data.description or "").split("\n") if l.strip()]
        
        if not lines:
            return await channel.send("❌ Could not read card metadata.")

        stats_line = lines[0]
        for line in lines:
            if "·" in line and "#" in line: 
                stats_line = line
                break

        parts = stats_line.split("·")
        card_code = parts[0].strip().replace("`", "").replace("*", "")
        character_name = parts[-1].strip().replace("*", "")
        
        card_image_url = embed_data.thumbnail.url if embed_data.thumbnail else None
        end_time = int(time.time()) + seconds

        desc = f"✨ *A new treasure has entered the pavilion.* ✨\n\n"
        desc += f"**୨୧ Character ୨୧**\n{character_name}\n\n"
        desc += f"**୨୧ Details ୨୧**\n`{stats_line}`\n"
        
        if clan_bonus > 0 or booster_bonus > 0:
            desc += f"\n**୨୧ Bonus Entries ୨୧**\n"
            if clan_bonus > 0:
                desc += f"✦ Clan Members: +{clan_bonus}\n"
            if booster_bonus > 0:
                desc += f"✦ Boosters: +{booster_bonus}\n"
                
        desc += f"\n⏰ **Ends:** <t:{end_time}:R>"

        giveaway_embed = discord.Embed(title="✦ . HEAVENLY COURT GIVEAWAY . ✦", description=desc, color=0x2b2d31)
        giveaway_embed.set_footer(text=f"Hosted by {author.display_name}")
        
        if card_image_url:
            giveaway_embed.set_thumbnail(url=card_image_url)

        view = GiveawayEntryView(clan_bonus, booster_bonus)
        msg = await channel.send(embed=giveaway_embed, view=view)

        task = asyncio.create_task(self.manage_giveaway_timer(seconds, msg.id, channel.id, view, giveaway_embed, character_name))
        self.active_giveaways[msg.id] = {"task": task, "view": view, "embed": giveaway_embed, "prize": character_name, "channel_id": channel.id}

    @giveaway_group.command(name="start", description="Starts a giveaway")
    @app_commands.describe(
        clan_bonus="Extra entries for Clan Members (leave 0 if none)",
        booster_bonus="Extra entries for Boosters (leave 0 if none)"
    )
    async def start_wizard(self, interaction: discord.Interaction, clan_bonus: int = 0, booster_bonus: int = 0):
        EVENT_MANAGER_ROLE_ID = 1508333073668898996
        is_admin = interaction.user.guild_permissions.administrator
        is_event_manager = any(role.id == EVENT_MANAGER_ROLE_ID for role in interaction.user.roles)

        if not (is_admin or is_event_manager):
            return await interaction.response.send_message("❌ You do not have permission to run this command.", ephemeral=True)

        embed = discord.Embed(title="Giveaway Setup", description="Select the type of giveaway:", color=0x2b2d31)
        await interaction.response.send_message(embed=embed, view=GiveawayTypeSelect(self, interaction.user, clan_bonus, booster_bonus), ephemeral=True)

    @giveaway_group.command(name="cancel", description="Cancels an active giveaway")
    @app_commands.describe(message_id="The message ID of the giveaway to cancel")
    async def cancel_giveaway(self, interaction: discord.Interaction, message_id: str):
        EVENT_MANAGER_ROLE_ID = 1508333073668898996
        if not (interaction.user.guild_permissions.administrator or any(role.id == EVENT_MANAGER_ROLE_ID for role in interaction.user.roles)):
            return await interaction.response.send_message("❌ You do not have permission.", ephemeral=True)

        try:
            msg_id = int(message_id)
        except ValueError:
            return await interaction.response.send_message("❌ Invalid message ID formatting.", ephemeral=True)

        if msg_id not in self.active_giveaways:
            return await interaction.response.send_message("❌ Giveaway not found or already completed.", ephemeral=True)

        gaw_data = self.active_giveaways.pop(msg_id)
        gaw_data["task"].cancel()

        channel = self.bot.get_channel(gaw_data["channel_id"])
        if channel:
            try:
                target_msg = await channel.fetch_message(msg_id)
                embed = gaw_data["embed"]
                embed.description = "✨ *The giveaway was cancelled.* ✨"
                await target_msg.edit(embed=embed, view=None)
            except: pass

        await interaction.response.send_message("✅ Giveaway has been successfully cancelled.", ephemeral=True)

    @giveaway_group.command(name="end", description="Ends an active giveaway immediately")
    @app_commands.describe(message_id="The message ID of the giveaway to end early")
    async def end_giveaway_early(self, interaction: discord.Interaction, message_id: str):
        EVENT_MANAGER_ROLE_ID = 1508333073668898996
        if not (interaction.user.guild_permissions.administrator or any(role.id == EVENT_MANAGER_ROLE_ID for role in interaction.user.roles)):
            return await interaction.response.send_message("❌ You do not have permission.", ephemeral=True)

        try:
            msg_id = int(message_id)
        except ValueError:
            return await interaction.response.send_message("❌ Invalid message ID formatting.", ephemeral=True)

        if msg_id not in self.active_giveaways:
            return await interaction.response.send_message("❌ Giveaway not found or already completed.", ephemeral=True)

        gaw_data = self.active_giveaways[msg_id]
        gaw_data["task"].cancel()

        await interaction.response.send_message("Ending giveaway early...", ephemeral=True)
        await self.determine_winner(msg_id, gaw_data["channel_id"], gaw_data["view"], gaw_data["embed"], gaw_data["prize"])

async def setup(bot):
    await bot.add_cog(GiveawayCog(bot))