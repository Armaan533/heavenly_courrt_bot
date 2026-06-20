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

    @app_commands.command(name="test_clean", description="DEV TOOL: Test the background removal algorithm")
    async def test_clean(self, interaction: discord.Interaction, frame_name: str):
        match = next((n for n in FRAME_DB if frame_name.lower() in n.lower()), None)
        if not match:
            return await interaction.response.send_message("❌ Frame not found.", ephemeral=True)

        image_url = FRAME_DB[match].get("image")
        if not image_url:
            return await interaction.response.send_message("❌ No image URL for this frame.", ephemeral=True)

        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        return await interaction.followup.send("❌ Failed to download image.")
                    
                    frame_bytes = await resp.read()
                    
                    with Image.open(BytesIO(frame_bytes)).convert("RGBA") as img:
                        fw, fh = img.size
                        
                        bg_r, bg_g, bg_b = img.getpixel((fw // 2, fh // 2))[:3]
                        
                        datas = img.getdata()
                        new_data = []
                        
                        for item in datas:
                            r, g, b, a = item
                            
                            dist_sq = (r - bg_r)**2 + (g - bg_g)**2 + (b - bg_b)**2
                            
                            if dist_sq < 150:
                                new_data.append((0, 0, 0, 0)) 
                            else:
                                new_data.append(item) 
                                
                        img.putdata(new_data)
                        
                        output_buffer = BytesIO()
                        img.save(output_buffer, format="PNG")
                        output_buffer.seek(0)
                        
                        file = discord.File(fp=output_buffer, filename=f"cleaned_{match.replace(' ', '_')}.png")
                        
                        embed = discord.Embed(
                            title=f"🧪 Clean Test: {match.title()}", 
                            description="Background wiped. Inspect the edges below.",
                            color=0x2b2d31 
                        )
                        embed.set_image(url=f"attachment://cleaned_{match.replace(' ', '_')}.png")
                        
                        await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            await interaction.followup.send(f"❌ Error processing image: {e}")
            print(f"Cleaner Error: {e}", file=sys.stderr)

async def setup(bot):
    await bot.add_cog(FrameCleanerTest(bot))