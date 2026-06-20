import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageOps, ImageDraw
import sys
import os
from frame_prices import FRAME_DB

BASE_CARD_PATH = os.path.join("assets", "base_card.jpg")

class FrameRenderEngine(commands.Cog):
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
                        
                        bg_r, bg_g, bg_b = 49, 51, 56
                        
                        T_MIN = 10.0
                        T_MAX = 45.0
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
                            name="Static Vector Anchorage", 
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

    @app_commands.command(name="test_composite", description="Execute Euclidean Smoothstep Compositing Pipeline")
    async def test_composite(self, interaction: discord.Interaction, frame_name: str):
        match = next((n for n in FRAME_DB if frame_name.lower() in n.lower()), None)
        if not match:
            return await interaction.response.send_message("Target entity not located in index.", ephemeral=True)

        image_url = FRAME_DB[match].get("image")
        if not image_url:
            return await interaction.response.send_message("Vector topology unavailable.", ephemeral=True)

        if not os.path.exists(BASE_CARD_PATH):
            return await interaction.response.send_message("Base matrix `assets/base_card.jpg` missing.", ephemeral=True)

        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status != 200:
                        return await interaction.followup.send("HTTP transmission failed.")
                    
                    frame_bytes = await resp.read()
                    
                    with Image.open(BASE_CARD_PATH).convert("RGBA") as base_img, \
                         Image.open(BytesIO(frame_bytes)).convert("RGBA") as frame_img:
                         
                        fw, fh = frame_img.size
                        
                        bg_r, bg_g, bg_b = 49, 51, 56
                        
                        T_MIN = 10.0
                        T_MAX = 45.0
                        T_RANGE = T_MAX - T_MIN
                        
                        datas = frame_img.getdata()
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
                                new_data.append((r, g, b, int(a * interpolation_factor)))
                                
                        frame_img.putdata(new_data)
                        
                        LEFT, TOP = 42, 36
                        RIGHT, BOTTOM = fw - 42, fh - 36
                        inner_w, inner_h = RIGHT - LEFT, BOTTOM - TOP
                        
                        try:
                            resample_method = Image.Resampling.LANCZOS
                        except AttributeError:
                            resample_method = Image.ANTIALIAS
                            
                        card_resized = ImageOps.fit(base_img, (inner_w, inner_h), method=resample_method)
                        
                        mask = Image.new("L", (inner_w, inner_h), 0)
                        draw = ImageDraw.Draw(mask)
                        draw.rounded_rectangle((0, 0, inner_w, inner_h), radius=20, fill=255)
                        card_resized.putalpha(mask)
                        
                        canvas = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
                        canvas.paste(card_resized, (LEFT, TOP), card_resized)
                        
                        final_composite = Image.alpha_composite(canvas, frame_img)
                        
                        output_buffer = BytesIO()
                        final_composite.save(output_buffer, format="PNG")
                        output_buffer.seek(0)
                        
                        file_name = f"composite_{match.replace(' ', '_')}.png"
                        file = discord.File(fp=output_buffer, filename=file_name)
                        
                        embed = discord.Embed(
                            title="[ SYSTEM: RESTRICTED SUBSPACE FUSION ]",
                            color=0x2b2d31
                        )
                        
                        embed.add_field(
                            name="Affine Transformation", 
                            value=(
                                "$$f: \\mathbb{R}^2 \\to \\mathbb{R}^2$$\n"
                                f"$$D_{{out}} = [{LEFT}, {RIGHT}] \\times [{TOP}, {BOTTOM}]$$\n"
                                "Isomorphic mapping strictly bounded to internal frame coordinates."
                            ),
                            inline=False
                        )
                        
                        embed.add_field(
                            name="Topological Clipping ($L^\\infty$ Norm)", 
                            value=(
                                "$$\\partial \\Omega = \\{(x,y) \\in D_{out} \\mid \\text{dist}((x,y), \\text{corners}) \\le \\rho \\}$$\n"
                                "$$\\rho = 20 \\text{px} \\quad (C^1 \\text{ boundary curvature})$$"
                            ),
                            inline=False
                        )
                        
                        embed.add_field(
                            name="Hermite Isometry", 
                            value=(
                                "$$D(\\mathbf{C}_p, \\mathbf{C}_{bg}) = \\left\\| \\mathbf{C}_p - \\mathbf{C}_{bg} \\right\\|_2$$\n"
                                f"$$\\tau_{{min}} = {T_MIN}, \\quad \\tau_{{max}} = {T_MAX}$$\n"
                                "$$\\alpha_{out} = \\alpha_{in} \\cdot (3x^2 - 2x^3)$$"
                            ),
                            inline=False
                        )
                        
                        embed.set_image(url=f"attachment://{file_name}")
                        
                        await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            await interaction.followup.send(f"Runtime Exception: {e}")
            print(f"Composite Error: {e}", file=sys.stderr)

async def setup(bot):
    await bot.add_cog(FrameRenderEngine(bot))