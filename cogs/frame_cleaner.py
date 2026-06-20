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

    @app_commands.command(name="test_clean", description="Execute Euclidean Smoothstep background extraction")
    async def test_clean(self, interaction: discord.Interaction, frame_name: str):
        match = next((n for n in FRAME_DB if frame_name.lower() in n.lower()), None)
        if not match:
            return await interaction.response.send_message("Frame entity not located in database.", ephemeral=True)

        image_url = FRAME_DB[match].get("image")
        if not image_url:
            return await interaction.response.send_message("Image vector unavailable.", ephemeral=True)

        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        return await interaction.followup.send("HTTP transmission failed.")
                    
                    frame_bytes = await resp.read()
                    
                    with Image.open(BytesIO(frame_bytes)).convert("RGBA") as img:
                        fw, fh = img.size
                        bg_r, bg_g, bg_b = img.getpixel((fw // 2, fh // 2))[:3]
                        
                        T_MIN = 12.0
                        T_MAX = 55.0
                        T_RANGE = T_MAX - T_MIN
                        
                        datas = img.getdata()
                        new_data = []
                        
                        for item in datas:
                            r, g, b, a = item
                            
                            dist = ((r - bg_r)**2 + (g - bg_g)**2 + (b - bg_b)**2) ** 0.5
                            
                            if dist <= T_MIN:
                                new_data.append((0, 0, 0, 0))
                            elif dist >= T_MAX:
                                new_data.append(item)
                            else:
                                x = (dist - T_MIN) / T_RANGE
                                interpolation_factor = (x ** 2) * (3.0 - 2.0 * x)
                                new_alpha = int(a * interpolation_factor)
                                new_data.append((r, g, b, new_alpha))
                                
                        img.putdata(new_data)
                        
                        output_buffer = BytesIO()
                        img.save(output_buffer, format="PNG")
                        output_buffer.seek(0)
                        
                        file_name = f"hermite_extract_{match.replace(' ', '_')}.png"
                        file = discord.File(fp=output_buffer, filename=file_name)
                        
                        embed = discord.Embed(
                            title="Alpha Channel Mapping Diagnostics",
                            color=0x2b2d31
                        )
                        
                        embed.add_field(
                            name="Vector Inputs", 
                            value=(
                                f"$$\\mathbf{{C}}_{{bg}} = \\begin{{bmatrix}} {bg_r} \\\\ {bg_g} \\\\ {bg_b} \\end{{bmatrix}}$$\n"
                                f"$$\\tau_{{min}} = {T_MIN}, \\quad \\tau_{{max}} = {T_MAX}$$"
                            ),
                            inline=False
                        )
                        
                        embed.add_field(
                            name="Distance Metric ($L^2$ Norm)", 
                            value="$$D(\\mathbf{C}_p, \\mathbf{C}_{bg}) = \\left\\| \\mathbf{C}_p - \\mathbf{C}_{bg} \\right\\|_2 = \\sqrt{(R_p - R_{bg})^2 + (G_p - G_{bg})^2 + (B_p - B_{bg})^2}$$",
                            inline=False
                        )
                        
                        embed.add_field(
                            name="Cubic Hermite Interpolation (Smoothstep)", 
                            value=(
                                "$$f(D) = \\begin{cases} "
                                "0 & \\text{if } D \\le \\tau_{min} \\\\"
                                "1 & \\text{if } D \\ge \\tau_{max} \\\\"
                                "3\\left(\\frac{D - \\tau_{min}}{\\tau_{max} - \\tau_{min}}\\right)^2 - 2\\left(\\frac{D - \\tau_{min}}{\\tau_{max} - \\tau_{min}}\\right)^3 & \\text{otherwise}"
                                "\\end{cases}$$\n\n"
                                "$$\\alpha_{out} = \\lfloor \\alpha_{in} \\cdot f(D) \\rfloor$$"
                            ),
                            inline=False
                        )
                        
                        embed.set_image(url=f"attachment://{file_name}")
                        
                        await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            await interaction.followup.send(f"Runtime Exception: {e}")
            print(f"Extraction Error: {e}", file=sys.stderr)

async def setup(bot):
    await bot.add_cog(FrameCleanerTest(bot))