import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import time
import random

class GiveawayEntryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.entrants = set()

    @discord.ui.button(label="Enter Giveaway", style=discord.ButtonStyle.green, custom_id="claim_giveaway_entry")
    async def enter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.entrants:
            await interaction.response.send_message("❌ You have already entered this giveaway.", ephemeral=True)
            return
            
        self.entrants.add(interaction.user.id)
        await interaction.response.send_message("✅ You have entered the giveaway.", ephemeral=True)

class GiveawayTypeSelect(discord.ui.View):
    def __init__(self, cog, author):
        super().__init__(timeout=60)
        self.cog = cog
        self.author = author

    @discord.ui.button(label="Karuta Card", style=discord.ButtonStyle.primary)
    async def card_choice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ This setup session belongs to someone else.", ephemeral=True)
        
        await interaction.response.defer()
        await self.cog.handle_card_flow(interaction)
        self.stop()

    @discord.ui.button(label="Item", style=discord.ButtonStyle.secondary)
    async def item_choice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ This setup session belongs to someone else.", ephemeral=True)
        
        await interaction.response.send_modal(ItemSetupModal(self.cog))
        self.stop()

class ItemSetupModal(discord.ui.Modal, title="Setup Giveaway"):
    item_name = discord.ui.TextInput(label="Item Name")
    description = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph)
    duration = discord.ui.TextInput(label="Duration (in minutes)")

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        try:
            mins = int(self.duration.value)
        except ValueError:
            return await interaction.response.send_message("❌ Invalid duration time.", ephemeral=True)

        end_time = int(time.time()) + (mins * 60)
        
        embed = discord.Embed(
            title="🎁 Item Giveaway",
            description=f"**Item:** {self.item_name.value}\n**Description:** {self.description.value}\n\nEnds: <t:{end_time}:R>",
            color=0x2f3136
        )
        embed.set_footer(text=f"Hosted by {interaction.user.display_name}")

        await interaction.response.send_message("Giveaway started.", ephemeral=True)
        view = GiveawayEntryView()
        msg = await interaction.channel.send(embed=embed, view=view)

        task = asyncio.create_task(self.cog.manage_giveaway_timer(mins * 60, msg.id, interaction.channel.id, view, embed, self.item_name.value))
        self.cog.active_giveaways[msg.id] = {
            "task": task,
            "view": view,
            "embed": embed,
            "prize": self.item_name.value,
            "channel_id": interaction.channel.id
        }

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
        if not channel:
            return

        try:
            target_msg = await channel.fetch_message(message_id)
        except:
            return

        winners = list(view.entrants)
        if not winners:
            embed.description = "Giveaway ended.\nWinner: None"
            await target_msg.edit(embed=embed, view=None)
            await channel.send(f"Giveaway for **{prize_name}** ended with no entries.")
            return

        winner_user = await self.bot.fetch_user(random.choice(winners))
        embed.description = f"Giveaway ended.\nWinner: {winner_user.mention}"
        await target_msg.edit(embed=embed, view=None)
        await channel.send(f"🎉 Congratulations {winner_user.mention}, you won **{prize_name}**!")

    @giveaway_group.command(name="start", description="Starts a giveaway")
    async def start_wizard(self, interaction: discord.Interaction):
        EVENT_MANAGER_ROLE_ID = 1508333073668898996
        is_admin = interaction.user.guild_permissions.administrator
        is_event_manager = any(role.id == EVENT_MANAGER_ROLE_ID for role in interaction.user.roles)

        if not (is_admin or is_event_manager):
            return await interaction.response.send_message("❌ You do not have permission to run this command.", ephemeral=True)

        embed = discord.Embed(
            title="Giveaway Setup",
            description="Select the type of giveaway:",
            color=0x2f3136
        )
        view = GiveawayTypeSelect(self, interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @giveaway_group.command(name="cancel", description="Cancels an active giveaway")
    @app_commands.describe(message_id="The message ID of the giveaway to cancel")
    async def cancel_giveaway(self, interaction: discord.Interaction, message_id: str):
        EVENT_MANAGER_ROLE_ID = 1508333073668898996
        is_admin = interaction.user.guild_permissions.administrator
        is_event_manager = any(role.id == EVENT_MANAGER_ROLE_ID for role in interaction.user.roles)

        if not (is_admin or is_event_manager):
            return await interaction.response.send_message("❌ You do not have permission to run this command.", ephemeral=True)

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
            except:
                pass

        await interaction.response.send_message("✅ Giveaway has been successfully cancelled.", ephemeral=True)

    @giveaway_group.command(name="end", description="Ends an active giveaway immediately")
    @app_commands.describe(message_id="The message ID of the giveaway to end early")
    async def end_giveaway_early(self, interaction: discord.Interaction, message_id: str):
        EVENT_MANAGER_ROLE_ID = 1508333073668898996
        is_admin = interaction.user.guild_permissions.administrator
        is_event_manager = any(role.id == EVENT_MANAGER_ROLE_ID for role in interaction.user.roles)

        if not (is_admin or is_event_manager):
            return await interaction.response.send_message("❌ You do not have permission to run this command.", ephemeral=True)

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

    async def handle_card_flow(self, interaction: discord.Interaction):
        channel = interaction.channel
        author = interaction.user

        prompt = await channel.send(f"Please use `kci <card_code>` in this channel now.")

        def karuta_check(m):
            return (m.author.id == 646937666251915264 and 
                    m.channel.id == channel.id and 
                    len(m.embeds) > 0 and 
                    "Card Details" in (m.embeds[0].title or ""))

        try:
            karuta_msg = await self.bot.wait_for('message', timeout=120.0, check=karuta_check)
        except asyncio.TimeoutError:
            return await channel.send(f"❌ Setup timed out.")

        embed_data = karuta_msg.embeds[0]
        lines = [l.strip() for l in (embed_data.description or "").split("\n") if l.strip()]
        
        if not lines:
            return await channel.send("❌ Could not read card metadata.")

        card_code = "Unknown"
        for part in lines[0].split("·"):
            if "`" in part:
                card_code = part.replace("`", "").strip()
                break

        character_name = "Unknown"
        for line in lines:
            if "·" not in line and "Dropped" not in line and "Owned" not in line and "Grabbed" not in line:
                character_name = line.replace("*", "").strip()
                break
        
        card_image_url = embed_data.thumbnail.url if embed_data.thumbnail else None

        duration_prompt = await channel.send(f"Found **{character_name}** (`{card_code}`). Reply with the duration in minutes:")

        def duration_check(m):
            return m.author.id == author.id and m.channel.id == channel.id and m.content.isdigit()

        try:
            duration_msg = await self.bot.wait_for('message', timeout=60.0, check=duration_check)
            mins = int(duration_msg.content)
        except asyncio.TimeoutError:
            return await channel.send(f"❌ Setup timed out.")

        try:
            await prompt.delete()
            await duration_prompt.delete()
            await duration_msg.delete()
        except:
            pass

        end_time = int(time.time()) + (mins * 60)

        giveaway_embed = discord.Embed(
            title="🎁 Card Giveaway",
            description=f"Click the button below to enter.",
            color=0x2f3136
        )
        giveaway_embed.add_field(name="Character", value=character_name, inline=True)
        giveaway_embed.add_field(name="Details", value=lines[0], inline=False)
        giveaway_embed.add_field(name="Ends", value=f"<t:{end_time}:R>", inline=True)
        giveaway_embed.add_field(name="Hosted by", value=author.mention, inline=True)
        
        if card_image_url:
            giveaway_embed.set_thumbnail(url=card_image_url)

        view = GiveawayEntryView()
        msg = await channel.send(embed=giveaway_embed, view=view)

        task = asyncio.create_task(self.manage_giveaway_timer(mins * 60, msg.id, channel.id, view, giveaway_embed, character_name))
        self.active_giveaways[msg.id] = {
            "task": task,
            "view": view,
            "embed": giveaway_embed,
            "prize": character_name,
            "channel_id": channel.id
        }

async def setup(bot):
    await bot.add_cog(GiveawayCog(bot))