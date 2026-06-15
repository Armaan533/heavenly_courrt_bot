import discord
from discord.ext import commands
from discord import app_commands

class QuoteModal(discord.ui.Modal, title="Create a Beautiful Quote"):
    quote_text = discord.ui.TextInput(
        label="The Quote",
        style=discord.TextStyle.paragraph,
        placeholder="Type your quote here...",
        required=True,
        max_length=4000
    )
    thumbnail_url = discord.ui.TextInput(
        label="Thumbnail URL (Optional)",
        style=discord.TextStyle.short,
        placeholder="https://example.com/small_image.png",
        required=False
    )
    image_url = discord.ui.TextInput(
        label="Bottom Image URL (Optional)",
        style=discord.TextStyle.short,
        placeholder="https://example.com/large_image.png",
        required=False
    )

    def __init__(self, target_channel: discord.TextChannel):
        super().__init__()
        self.target_channel = target_channel

    async def on_submit(self, interaction: discord.Interaction):
        # Removes auto-quotes, appends your custom DM message in italics, 
        # and keeps the invisible \u200B space to prevent the thumbnail gap!
        raw_quote = self.quote_text.value.strip()
        formatted_quote = f"{raw_quote}\n\u200B"
        
        embed = discord.Embed(
            title="✦ Quote ✦",
            description=formatted_quote,
            color=0x8b0000 
        )
        
        if self.thumbnail_url.value:
            embed.set_thumbnail(url=self.thumbnail_url.value.strip())
            
        if self.image_url.value:
            embed.set_image(url=self.image_url.value.strip())
            
        embed.set_footer(text="Heavenly Court ✦ *If anyone ever wants to suggest one just Dm Oddný!*")

        await self.target_channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Quote beautifully posted in {self.target_channel.mention}!", ephemeral=True)

class QuoteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    quote_group = app_commands.Group(name="quote", description="Manage the quote channel")

    @quote_group.command(name="post", description="Draft and post a new quote")
    @app_commands.describe(channel="The channel you want to send the quote to")
    async def quote_post(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        EVENT_MANAGER_ROLE_ID = 1508333073668898996
        ADMIN_ROLE_ID = 1503987120572858511
        
        is_admin = interaction.user.guild_permissions.administrator
        has_role = any(role.id in [ADMIN_ROLE_ID, EVENT_MANAGER_ROLE_ID] for role in interaction.user.roles)
        
        if not (is_admin or has_role):
            return await interaction.response.send_message("❌ You do not have permission to post quotes.", ephemeral=True)

        target = channel or interaction.channel
        await interaction.response.send_modal(QuoteModal(target))

async def setup(bot):
    await bot.add_cog(QuoteCog(bot))