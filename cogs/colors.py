import discord
from discord.ext import commands
from discord import app_commands
from constants import EMBED_COLOR

COLOR_ROLES = {
    "red":       1503801901165318275,
    "orange":    1503801901848858747,
    "yellow":    1503801902926794886,
    "green":     1503801903753203782,
    "cyan":      1503801904629678110,
    "blue":      1503801905443242124,
    "purple":    1503801906038833395,
    "pink":      1503801907003527380,
    "lime":      1509095064855646338,
    "wine":      1509094732272373812,
    "midnight":  1509095361581682818,
    "amethyst":  1509095177686356140,
}

class ColorDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Red", emoji="❤️", value="red"),
            discord.SelectOption(label="Orange", emoji="🧡", value="orange"),
            discord.SelectOption(label="Yellow", emoji="💛", value="yellow"),
            discord.SelectOption(label="Green", emoji="💚", value="green"),
            discord.SelectOption(label="Cyan", emoji="🩵", value="cyan"),
            discord.SelectOption(label="Blue", emoji="💙", value="blue"),
            discord.SelectOption(label="Purple", emoji="💜", value="purple"),
            discord.SelectOption(label="Pink", emoji="🩷", value="pink"),
            discord.SelectOption(label="Lime", emoji="🍏", value="lime"),
            discord.SelectOption(label="Wine", emoji="🍷", value="wine"),
            discord.SelectOption(label="Midnight", emoji="🌌", value="midnight"),
            discord.SelectOption(label="Amethyst", emoji="💠", value="amethyst"),
            discord.SelectOption(label="Clear Color Aura", emoji="❌", value="clear", description="Removes your current color role")
        ]
        super().__init__(
            placeholder="Choose your cultivation aura...",
            min_values=1,
            max_values=10,
            options=options,
            custom_id="color_selector"
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        member = interaction.user
        selected_color = self.values[0]
        
        roles_to_remove = [
            interaction.guild.get_role(role_id)
            for color, role_id in COLOR_ROLES.items()
            if (role_id in [r.id for r in member.roles]) and interaction.guild.get_role(role_id)
        ]
        
        if roles_to_remove:
            await member.remove_roles(*roles_to_remove)
            
        if selected_color == "clear":
            return await interaction.followup.send("✦ Your cultivation aura color has been removed!", ephemeral=True)
            
        new_role_id = COLOR_ROLES.get(selected_color)
        new_role = interaction.guild.get_role(new_role_id)
        
        if new_role:
            await member.add_roles(new_role)
            await interaction.followup.send(f"✦ Your cultivation aura has changed to **{new_role.name}**!", ephemeral=True)
        else:
            await interaction.followup.send("❌ Error: That role could not be found. Please contact an admin.", ephemeral=True)

class ColorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ColorDropdown())

class ColorsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="send_color_panel", description="Spawns the beautiful color role selection panel.")
    @app_commands.default_permissions(administrator=True)
    async def send_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🎨 COLOR ROLES 🎨", color=EMBED_COLOR)
        embed.description = (
            "✨ *choose an aura worthy of your cultivation path* ✨\n\n"
            "╭──────────୨୧──────────╮\n\n"
            "❤️ ｜ Red\n"
            "🧡 ｜ Orange\n"
            "💛 ｜ Yellow\n"
            "💚 ｜ Green\n\n"
            "🩵 ｜ Cyan\n"
            "💙 ｜ Blue\n"
            "💜 ｜ Purple\n"
            "🩷 ｜ Pink\n\n"
            "🍏 ｜ Lime\n"
            "🍷 ｜ Wine\n"
            "🌌 ｜ Midnight\n"
            "💠 ｜ Amethyst\n\n"
            "╰──────────୨୧──────────╯\n\n"
            "✦ select colour from the dropdown below ⬇️"
        )
        
        await interaction.channel.send(embed=embed, view=ColorView())
        await interaction.response.send_message("✦ Panel posted successfully!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ColorsCog(bot))