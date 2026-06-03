import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import time
import random

# --- 1. THE GIVEAWAY BUTTON & TICKETS ---
class GiveawayEntryView(discord.ui.View):
    def __init__(self, allow_bonus=False):
        super().__init__(timeout=None)
        self.participants = set() # Tracks unique users for the counter
        self.tickets = []         # Tracks total entries for the drawing
        self.allow_bonus = allow_bonus

    @discord.ui.button(label="Enter Giveaway (0)", style=discord.ButtonStyle.green, custom_id="claim_gaw_entry")
    async def enter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.participants:
            await interaction.response.send_message("❌ You have already entered this giveaway.", ephemeral=True)
            return
            
        entries = 1
        if self.allow_bonus:
            user_role_ids = [role.id for role in interaction.user.roles]
            if 1504127544801366128 in user_role_ids: # Clan Member
                entries += 1
            if 1474356762063667210 in user_role_ids: # Booster
                entries += 1
                
        self.participants.add(interaction.user.id)
        for _ in range(entries):
            self.tickets.append(interaction.user.id)
            
        # Update the live counter on the button!
        button.label = f"Enter Giveaway ({len(self.participants)})"
        await interaction.response.edit_message(view=self)
        
        await interaction.followup.send(f"✅ You have entered the giveaway with **{entries}** ticket(s)!", ephemeral=True)


# --- 2. THE MODALS (NO MORE CHAT TIMEOUTS) ---
class ItemSetupModal(discord.ui.Modal, title="Setup Item Giveaway"):
    item_name = discord.ui.TextInput(label="Item Name")
    description = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph)
    duration = discord.ui.TextInput(label="Duration (in minutes)", placeholder="e.g. 10")
    bonus = discord.ui.TextInput(label="Enable Clan/Booster Bonus? (yes/no)", default="yes")

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        try:
            mins = int(self.duration.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ Invalid duration.", ephemeral=True)

        allow_bonus = "yes" in self.bonus.value.lower()
        end_time = int(time.time()) + (mins * 60)
        
        desc = f"**Item:** {self.item_name.value}\n**Description:** {self.description.value}\n"
        if allow_bonus:
            desc += "\n🎁 *Clan Members & Boosters receive +1 bonus entry!*"
        desc += f"\n\nEnds: <t:{end_time}:R>"
        
        embed = discord.Embed(title="🎁 Item Giveaway", description=desc, color=0x2f3136)
        embed.set_footer(text=f"Hosted by {interaction.user.display_name}")

        await interaction.response.send_message("Giveaway started successfully!", ephemeral=True)
        view = GiveawayEntryView(allow_bonus=allow_bonus)
        msg = await interaction.channel.send(embed=embed, view=view)

        # Start background timer
        task = asyncio.create_task(self.cog.manage_giveaway_timer(mins * 60, msg.id, interaction.channel.id, view, embed, self.item_name.value))
        self.cog.active_giveaways[msg.id] = {"task": task, "view": view, "embed": embed, "prize": self.item_name.value, "channel_id": interaction.channel.id}

class CardConfigModal(discord.ui.Modal, title="Configure Card Giveaway"):
    duration = discord.ui.TextInput(label="Duration (in minutes)", placeholder="e.g. 10")
    bonus = discord.ui.TextInput(label="Enable Clan/Booster Bonus? (yes/no)", default="yes")

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        try:
            mins = int(self.duration.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ Invalid duration.", ephemeral=True)

        allow_bonus = "yes" in self.bonus.value.lower()
        
        await interaction.response.send_message(f"✅ Configuration saved! **{interaction.user.mention}, please run `kci <card_code>` in this channel now.**", ephemeral=False)
        
        # Now we watch for Karuta!
        await self.cog.wait_for_kci(interaction.channel, interaction.user, mins, allow_bonus)


# --- 3. THE SETUP WIZARD MENU ---
class GiveawayTypeSelect(discord.ui.View):
    def __init__(self, cog, author):
        super().__init__(timeout=60)
        self.cog = cog
        self.author = author

    @discord.ui.button(label="Karuta Card", style=discord.ButtonStyle.primary)
    async def card_choice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ This setup session belongs to someone else.", ephemeral=True)
        
        # Launch Card Modal immediately!
        await interaction.response.send_modal(CardConfigModal(self.cog))
        self.stop()

    @discord.ui.button(label="Item", style=discord.ButtonStyle.secondary)
    async def item_choice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ This setup session belongs to someone else.", ephemeral=True)
        
        # Launch Item Modal immediately!
        await interaction.response.send_modal(ItemSetupModal(self.cog))
        self.stop()


# --- 4. THE MAIN COG ---
class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}
        
    giveaway_group = app_commands.Group(name="giveaway", description="Manage giveaways")

    # -------- GIVEAWAY ENDING LOGIC --------
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
            embed.description = "Giveaway ended.\nWinner: None"
            await target_msg.edit(embed=embed, view=None)
            await channel.send(f"Giveaway for **{prize_name}** ended with no entries.")
            return

        winner_user = await self.bot.fetch_user(random.choice(winners))
        embed.description = f"Giveaway ended.\nWinner: {winner_user.mention}"
        await target_msg.edit(embed=embed, view=None)
        await channel.send(f"🎉 Congratulations {winner_user.mention}, you won **{prize_name}**!")

    # -------- KARUTA CARD CATCHER --------
    async def wait_for_kci(self, channel, author, mins, allow_bonus):
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

        # Line 0 usually contains the code and print.
        code_line = lines[0]
        card_code = code_line.split("·")[0].strip().replace("`", "")

        # Line 1 is almost always the bolded character name.
        character_name = lines[1].replace("*", "").strip() if len(lines) > 1 else "Unknown"
        card_image_url = embed_data.thumbnail.url if embed_data.thumbnail else None

        end_time = int(time.time()) + (mins * 60)

        giveaway_embed = discord.Embed(title="🎁 Card Giveaway", description=f"Click the button below to enter.", color=0x2f3136)
        giveaway_embed.add_field(name="Character", value=character_name, inline=True)
        giveaway_embed.add_field(name="Details", value=code_line, inline=False)
        
        if allow_bonus:
            giveaway_embed.add_field(name="Bonus Perks", value="🎁 Clan Members & Boosters receive +1 extra entry!", inline=False)
            
        giveaway_embed.add_field(name="Ends", value=f"<t:{end_time}:R>", inline=True)
        giveaway_embed.add_field(name="Hosted by", value=author.mention, inline=True)
        
        if card_image_url:
            giveaway_embed.set_thumbnail(url=card_image_url)

        view = GiveawayEntryView(allow_bonus=allow_bonus)
        msg = await channel.send(embed=giveaway_embed, view=view)

        task = asyncio.create_task(self.manage_giveaway_timer(mins * 60, msg.id, channel.id, view, giveaway_embed, character_name))
        self.active_giveaways[msg.id] = {"task": task, "view": view, "embed": giveaway_embed, "prize": character_name, "channel_id": channel.id}

    # -------- SLASH COMMANDS --------
    @giveaway_group.command(name="start", description="Starts a giveaway")
    async def start_wizard(self, interaction: discord.Interaction):
        EVENT_MANAGER_ROLE_ID = 1508333073668898996
        is_admin = interaction.user.guild_permissions.administrator
        is_event_manager = any(role.id == EVENT_MANAGER_ROLE_ID for role in interaction.user.roles)

        if not (is_admin or is_event_manager):
            return await interaction.response.send_message("❌ You do not have permission to run this command.", ephemeral=True)

        embed = discord.Embed(title="Giveaway Setup", description="Select the type of giveaway:", color=0x2f3136)
        await interaction.response.send_message(embed=embed, view=GiveawayTypeSelect(self, interaction.user), ephemeral=True)

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
                embed.description = "Giveaway cancelled."
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