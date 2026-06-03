import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import time

class GiveawayEntryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.entrants = set()

    @discord.ui.button(label="Enter Giveaway", style=discord.ButtonStyle.green, custom_id="claim_giveaway_entry")
    async def enter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.entrants:
            await interaction.response.send_message(
                "❌ You have already entered your destiny token into this lottery!", 
                ephemeral=True
            )
            return
            
        self.entrants.add(interaction.user.id)
        await interaction.response.send_message("✅ Your entry has been recorded in the scroll!", ephemeral=True)

class GiveawayTypeSelect(discord.ui.View):
    def __init__(self, cog, author):
        super().__init__(timeout=60)
        self.cog = cog
        self.author = author

    @discord.ui.button(label="🎴 Karuta Card", style=discord.ButtonStyle.primary)
    async def card_choice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ This setup session belongs to someone else.", ephemeral=True)
        
        await interaction.response.defer()
        await self.cog.handle_card_flow(interaction)
        self.stop()

    @discord.ui.button(label="📦 Custom Item", style=discord.ButtonStyle.secondary)
    async def item_choice(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("❌ This setup session belongs to someone else.", ephemeral=True)
        
        await interaction.response.send_modal(ItemSetupModal(self.cog))
        self.stop()

class ItemSetupModal(discord.ui.Modal, title="Setup Item Giveaway"):
    item_name = discord.ui.TextInput(label="Item Name", placeholder="e.g., 500 Ticket Pack / Special Role")
    description = discord.ui.TextInput(label="Item Description", style=discord.TextStyle.paragraph, placeholder="Describe what the winner receives...")
    duration = discord.ui.TextInput(label="Duration (in minutes)", placeholder="e.g., 60 for 1 hour, 1440 for 1 day")

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        try:
            mins = int(self.duration.value)
        except ValueError:
            return await interaction.response.send_message("❌ Invalid duration time. Must be a valid whole number.", ephemeral=True)

        end_time = int(time.time()) + (mins * 60)
        
        embed = discord.Embed(
            title="⛩️ HEAVENLY COURT ITEM LOTTERY ⛩️",
            description=f"An item of the realm is up for acquisition!\n\n**Item:** {self.item_name.value}\n**Details:** {self.description.value}\n\n⏱️ **Closes:** <t:{end_time}:R> (<t:{end_time}:F>)",
            color=0xe67e22
        )
        embed.set_thumbnail(url="https://cdnb.artstation.com/p/assets/images/images/038/658/167/original/peter-sheff-chest-open03-small.gif")
        embed.set_footer(text=f"Hosted by {interaction.user.display_name}")

        await interaction.response.send_message("✨ Item giveaway generated successfully!", ephemeral=True)
        await interaction.channel.send(embed=embed, view=GiveawayEntryView())

class GiveawayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    giveaway_group = app_commands.Group(name="giveaway", description="Manage server giveaway flows")

    @giveaway_group.command(name="start", description="Launches the interactive giveaway generator wizard")
    async def start_wizard(self, interaction: discord.Interaction):
        EVENT_MANAGER_ROLE_ID = 1508333073668898996
        is_admin = interaction.user.guild_permissions.administrator
        is_event_manager = any(role.id == EVENT_MANAGER_ROLE_ID for role in interaction.user.roles)

        if not (is_admin or is_event_manager):
            return await interaction.response.send_message("❌ Authorized to Supreme Elders and Event Managers only.", ephemeral=True)

        embed = discord.Embed(
            title="🛠️ Giveaway Configuration Matrix",
            description="Identify the nature of the treasure you intend to distribute to the disciples below:",
            color=0x9b59b6
        )
        view = GiveawayTypeSelect(self, interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def handle_card_flow(self, interaction: discord.Interaction):
        channel = interaction.channel
        author = interaction.user

        prompt = await channel.send(f"🔮 {author.mention} **Excellent. Please issue `kci <card_code>` in this channel now.**\nI am watching the matrix lines to scan Karuta's readout metadata...")

        def karuta_check(m):
            return (m.author.id == 646937666251915264 and 
                    m.channel.id == channel.id and 
                    len(m.embeds) > 0 and 
                    "Card Details" in (m.embeds[0].title or ""))

        try:
            karuta_msg = await self.bot.wait_for('message', timeout=120.0, check=karuta_check)
        except asyncio.TimeoutError:
            return await channel.send(f"❌ {author.mention} Setup timed out. You took too long to run the `kci` command.")

        embed_data = karuta_msg.embeds[0]
        description_lines = (embed_data.description or "").split("\n")
        
        if not description_lines or len(description_lines) < 2:
            return await channel.send("❌ Error decoding Karuta data matrix framework. Ensure the embed layout matches standard configuration properties.")

        meta_row = description_lines[0]
        meta_segments = [seg.strip().replace("*", "").replace("`", "") for seg in meta_row.split("·")]
        
        card_code = meta_segments[0] if len(meta_segments) > 0 else "Unknown"
        print_num = meta_segments[2] if len(meta_segments) > 2 else "Unknown"
        edition = meta_segments[3] if len(meta_segments) > 3 else "Unknown"
        series_name = meta_segments[4] if len(meta_segments) > 4 else "Unknown"
        
        character_name = description_lines[1].replace("*", "").strip() if len(description_lines) > 1 else "Unknown"
        card_image_url = embed_data.thumbnail.url if embed_data.thumbnail else None

        duration_prompt = await channel.send(f"✅ **Data Matrix Decoded!** Parsed card: **{character_name}** (`{card_code}`).\n\n👉 Now, reply directly in chat with the **duration of the giveaway in minutes** (e.g., type `10` for 10 minutes or `1440` for a day):")

        def duration_check(m):
            return m.author.id == author.id and m.channel.id == channel.id and m.content.isdigit()

        try:
            duration_msg = await self.bot.wait_for('message', timeout=60.0, check=duration_check)
            mins = int(duration_msg.content)
        except asyncio.TimeoutError:
            return await channel.send(f"❌ {author.mention} Setup aborted due to configuration inactivity.")

        try:
            await prompt.delete()
            await duration_prompt.delete()
            await duration_msg.delete()
        except:
            pass

        end_time = int(time.time()) + (mins * 60)

        giveaway_embed = discord.Embed(
            title="⛩️ HEAVENLY COURT GRAIL GIVEAWAY ⛩️",
            description=f"A legendary character card has been sacrificed to the scroll! Press the button below to register your lottery ticket.",
            color=0xf1c40f
        )
        giveaway_embed.add_field(name="Character Identity", value=f"**{character_name}**", inline=True)
        giveaway_embed.add_field(name="Source Universe", value=f"*{series_name}*", inline=True)
        giveaway_embed.add_field(name="Card Specifications", value=f"Code: `{card_code}` • {edition} • Print **{print_num}**", inline=False)
        giveaway_embed.add_field(name="⏱️ Expiration Horizon", value=f"Closes <t:{end_time}:R> (<t:{end_time}:F>)", inline=False)
        giveaway_embed.add_field(name="👑 Host Master", value=author.mention, inline=True)
        
        if card_image_url:
            giveaway_embed.set_image(url=card_image_url) 
        giveaway_embed.set_thumbnail(url="https://cdnb.artstation.com/p/assets/images/images/038/658/167/original/peter-sheff-chest-open03-small.gif")

        await channel.send(embed=giveaway_embed, view=GiveawayEntryView())

async def setup(bot):
    await bot.add_cog(GiveawayCog(bot))