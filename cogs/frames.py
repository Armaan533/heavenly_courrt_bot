import discord
from discord import app_commands
from discord.ext import commands
from frame_prices import FRAME_DB

class FramesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def frame_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        frames = list(FRAME_DB.keys())
        matches = [f for f in frames if current.lower() in f.lower()]
        return [app_commands.Choice(name=match.title(), value=match) for match in matches[:25]]

    frame_group = app_commands.Group(name="frame", description="Heavenly Court Frame Utilities")

    @frame_group.command(name="info", description="Look up a frame's market value, liquid cost, and image")
    @app_commands.autocomplete(frame_name=frame_autocomplete)
    async def frame_info(self, interaction: discord.Interaction, frame_name: str):
        frame_name_lower = frame_name.lower()
        
        if frame_name_lower not in FRAME_DB:
            return await interaction.response.send_message(
                f"❌ Could not find **{frame_name}** in the Heavenly Court database.", 
                ephemeral=True
            )
            
        data = FRAME_DB[frame_name_lower]
        frame_type = data.get("type", "Unknown")
        market_price = data.get("market", 0)
        liquid_price = data.get("liquid cost", 0)
        image_url = data.get("image", None)
        
        embed = discord.Embed(
            title=f"<:two_flowers:1516684386546880614> Frame: {frame_name_lower.title()}",
            color=0x6b1614
        )
        
        embed.add_field(name="<:book_ig:1516683126066253844> Category", value=f"`{frame_type}`", inline=False)
        
        if market_price == 0 and liquid_price == 0:
            embed.add_field(name="💰 Pricing", value="*Not tradable or zero value.*", inline=False)
        else:
            embed.add_field(name="<:eight_side_sparkle:1516681364806570105> Market Value", value=f"**{market_price}** 🎟️", inline=True)
            embed.add_field(name="<:for_john:1517226175901208696> Liquid Cost", value=f"**{liquid_price}** 🎟️", inline=True)
            
        if image_url:
            embed.set_image(url=image_url)
            embed.set_footer(text="Heavenly Court Frame Database")
        else:
            embed.set_footer(text="Heavenly Court Frame Database | Image pending scrape 🔄")
            
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(FramesCog(bot))