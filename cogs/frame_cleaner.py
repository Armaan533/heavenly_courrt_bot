import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image
import sys
from frame_prices import FRAME_DB

class FrameCleanerTest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="test_clean", description="DEV TOOL: Process frame transparency")
    async def test_clean(self, interaction: discord.Interaction, frame_name: str):
        match = next((n for n in FRAME_DB if frame_name.lower() in n.lower()), None)
        if not match:
            return await interaction.response.send_message("❌ Target asset not found.", ephemeral=True)

        image_url = FRAME_DB[match].get("image")
        if not image_url:
            return await interaction.response.send_message("❌ Asset URL unavailable.", ephemeral=True)

        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        return await interaction.followup.send("❌ HTTP Stream failed.")
                    
                    frame_bytes = await resp.read()
                    
                    with Image.open(BytesIO(frame_bytes)).convert("RGBA") as img:
                        fw, fh = img.size
                        bg_r, bg_g, bg_b = img.getpixel((fw // 2, fh // 2))[:3]
                        
                        LOW_THRESHOLD = 350
                        HIGH_THRESHOLD = 800
                        
                        datas = img.getdata()
                        new_data = []
                        
                        for item in datas:
                            r, g, b, a = item
                            dist_sq = (r - bg_r)**2 + (g - bg_g)**2 + (b - bg_b)**2
                            color_variance = max(abs(r-g), abs(g-b), abs(r-b))
                            
                            if dist_sq <= LOW_THRESHOLD and color_variance < 25:
                                new_data.append((0, 0, 0, 0))
                            elif dist_sq >= HIGH_THRESHOLD or color_variance >= 25:
                                new_data.append(item)
                            else:
                                ratio = (dist_sq - LOW_THRESHOLD) / (HIGH_THRESHOLD - LOW_THRESHOLD)
                                smooth_alpha = int(a * ratio)
                                new_data.append((r, g, b, smooth_alpha))
                                
                        img.putdata(new_data)
                        
                        output_buffer = BytesIO()
                        img.save(output_buffer, format="PNG")
                        output_buffer.seek(0)
                        
                        file_name = f"processed_{match.replace(' ', '_')}.png"
                        file = discord.File(fp=output_buffer, filename=file_name)
                        
                        embed = discord.Embed(
                            title="Background Extraction Diagnostics",
                            color=0x2b2d31
                        )
                        embed.add_field(
                            name="Asset ID", 
                            value=f"`{match}`", 
                            inline=True
                        )
                        embed.add_field(
                            name="Sample Vector", 
                            value=f"`RGB({bg_r}, {bg_g}, {bg_b})`", 
                            inline=True
                        )
                        embed.add_field(
                            name="Alpha Band", 
                            value=f"`T_low: {LOW_THRESHOLD} | T_high: {HIGH_THRESHOLD}`", 
                            inline=True
                        )
                        embed.add_field(
                            name="Algorithm Parameters", 
                            value=(
                                "**Distance Metric:** Euclidean squared ($d^2$)\n"
                                "**Color Variance Gate:** $\\Delta_{max} < 25$ (Isolates achromatic regions)\n"
                                "**Interpolation:** Linear mapping within transition boundary."
                            ), 
                            inline=False
                        )
                        embed.set_image(url=f"attachment://{file_name}")
                        
                        await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            await interaction.followup.send(f"❌ Exception: {e}")
            print(f"Extraction Error: {e}", file=sys.stderr)

async def setup(bot):
    await bot.add_cog(FrameCleanerTest(bot))