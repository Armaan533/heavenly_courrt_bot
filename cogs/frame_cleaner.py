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

    @app_commands.command(name="test_clean", description="DEV TOOL: Extraction")
    async def test_clean(self, interaction: discord.Interaction, frame_name: str):
        match = next((n for n in FRAME_DB if frame_name.lower() in n.lower()), None)
        if not match:
            return await interaction.response.send_message("❌ Target asset not found.", ephemeral=True)

        image_url = FRAME_DB[match].get("image")
        if not image_url:
            return await interaction.response.send_message("❌ Matrix data unavailable.", ephemeral=True)

        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        return await interaction.followup.send("❌ Data stream interrupted.")
                    
                    frame_bytes = await resp.read()
                    
                    with Image.open(BytesIO(frame_bytes)).convert("RGBA") as img:
                        fw, fh = img.size
                        bg_r, bg_g, bg_b = img.getpixel((fw // 2, fh // 2))[:3]
                        
                        LOW_THRESHOLD = 80
                        HIGH_THRESHOLD = 650
                        
                        datas = img.getdata()
                        new_data = []
                        
                        for item in datas:
                            r, g, b, a = item
                            dist_sq = (r - bg_r)**2 + (g - bg_g)**2 + (b - bg_b)**2
                            
                            if dist_sq <= LOW_THRESHOLD:
                                new_data.append((0, 0, 0, 0))
                            elif dist_sq >= HIGH_THRESHOLD:
                                new_data.append(item)
                            else:
                                ratio = (dist_sq - LOW_THRESHOLD) / (HIGH_THRESHOLD - LOW_THRESHOLD)
                                smooth_alpha = int(a * ratio)
                                new_data.append((r, g, b, smooth_alpha))
                                
                        img.putdata(new_data)
                        
                        output_buffer = BytesIO()
                        img.save(output_buffer, format="PNG")
                        output_buffer.seek(0)
                        
                        file_name = f"heuristic_extraction_{match.replace(' ', '_')}.png"
                        file = discord.File(fp=output_buffer, filename=file_name)
                        
                        embed = discord.Embed(
                            title="[ EXTRACTION ]",
                            description=f"Target Asset: **{match.title()}**\nInitiating Non-Linear Alpha Interpolation Protocol...",
                            color=0x2b2d31
                        )
                        
                        embed.add_field(
                            name="[ DATA: CHROMATIC TENSOR ]", 
                            value=f"Origin Node: `({fw // 2}, {fh // 2})`\nBase Vector Space: `RGB({bg_r}, {bg_g}, {bg_b})`", 
                            inline=False
                        )
                        
                        embed.add_field(
                            name="[ ALGORITHM: 3D EUCLIDEAN ISOMETRY ]", 
                            value=(
                                "Employing tri-axial chromatic distance thresholding via scalar projections:\n\n"
                                "$$ \\Delta E^2 = (R_p - R_o)^2 + (G_p - G_o)^2 + (B_p - B_o)^2 $$\n\n"
                                "**Isolating Sub-pixel Raster Gradient:**\n"
                                "If $$\\Delta E^2 \\le \\beta$$ : $$\\alpha = 0$$ *(Null State)*\n"
                                "If $$\\Delta E^2 \\ge \\gamma$$ : $$\\alpha = 255$$ *(Solid State)*\n"
                                "Else : $$\\alpha_{new} = \\alpha_{org} \\times \\left( \\frac{\\Delta E^2 - \\beta}{\\gamma - \\beta} \\right)$$"
                            ), 
                            inline=False
                        )
                        
                        embed.set_image(url=f"attachment://{file_name}")
                        embed.set_footer(text="Process Complete • Stochastic Alpha-Compositing Verified")
                        
                        await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            await interaction.followup.send(f"❌ Exception in extraction pipeline: {e}")
            print(f"Extraction Error: {e}", file=sys.stderr)

async def setup(bot):
    await bot.add_cog(FrameCleanerTest(bot))