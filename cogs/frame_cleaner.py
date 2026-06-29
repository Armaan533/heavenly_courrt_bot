import discord
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageOps, ImageDraw
import asyncio
from collections import deque
from frame_prices import FRAME_DB

KARUTA_BOT_ID = 646937666251915264

class FrameTestModal(discord.ui.Modal, title="Frame Rendering Matrix"):
    frame_name = discord.ui.TextInput(
        label="Enter Frame Name", 
        placeholder="e.g. Voidspawn, Interface, Spring..."
    )

    def __init__(self, bot, card_url, char_name):
        super().__init__()
        self.bot = bot
        self.card_url = card_url
        self.char_name = char_name

    async def on_submit(self, interaction: discord.Interaction):
        f_name = self.frame_name.value.strip().lower()
        
        match = next((n for n in FRAME_DB if f_name in n.lower()), None)
        if not match:
            return await interaction.response.send_message(f"❌ Frame `{f_name}` not found in the database.", ephemeral=True)

        frame_url = FRAME_DB[match].get("image")
        if not frame_url:
            return await interaction.response.send_message(f"❌ No image mapped for {match.title()}.", ephemeral=True)

        await interaction.response.send_message(f"⏳ **Rendering {match.title()} on {self.char_name}...**\n*Executing Dual-Zone Flood Fill...*", ephemeral=False)
        msg = await interaction.original_response()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.card_url) as card_resp, session.get(frame_url) as frame_resp:
                    if card_resp.status != 200 or frame_resp.status != 200:
                        return await msg.edit(content="❌ Failed to fetch images from Discord servers.")
                    
                    card_bytes = await card_resp.read()
                    frame_bytes = await frame_resp.read()

                    output_buffer = await asyncio.to_thread(self.process_frame, card_bytes, frame_bytes)

                    file = discord.File(fp=output_buffer, filename=f"preview_{match.replace(' ', '_')}.png")
                    
                    embed = discord.Embed(
                        title="✦ . FRAME RENDER COMPLETE . ✦",
                        description=f"**Character:** {self.char_name}\n**Frame:** {match.title()}",
                        color=0x2b2d31
                    )
                    embed.set_image(url=f"attachment://{file.filename}")
                    embed.set_footer(text="Grey boundary isolated and erased via spatial flood-fill.")
                    
                    await msg.edit(content=None, embed=embed, attachments=[file])

        except Exception as e:
            await msg.edit(content=f"❌ **Render Error:** {e}")

    def process_frame(self, card_bytes, frame_bytes):
        """Executes the dual-zone flood fill and compositing"""
        with Image.open(BytesIO(card_bytes)).convert("RGBA") as card_img, \
             Image.open(BytesIO(frame_bytes)).convert("RGBA") as frame_img:
             
            fw, fh = frame_img.size
            
            def flood_fill(start_xy, tolerance=30):
                pixels = frame_img.load()
                q = deque([start_xy])
                visited = set([start_xy])
                
                while q:
                    cx, cy = q.popleft()
                    r, g, b, a = pixels[cx, cy]
                    if a == 0: continue 
                    
                    dist = ((r - 49)**2 + (g - 51)**2 + (b - 56)**2) ** 0.5
                    
                    if dist <= tolerance:
                        pixels[cx, cy] = (0, 0, 0, 0) 
                        
                        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < fw and 0 <= ny < fh:
                                if (nx, ny) not in visited:
                                    visited.add((nx, ny))
                                    q.append((nx, ny))

            flood_fill((0, 0))
            flood_fill((fw // 2, fh // 2))
            
            PAD = 14
            inner_w, inner_h = fw - (PAD*2), fh - (PAD*2)
            
            try: resample_method = Image.Resampling.LANCZOS
            except AttributeError: resample_method = Image.ANTIALIAS
                
            card_resized = ImageOps.fit(card_img, (inner_w, inner_h), method=resample_method).convert("RGBA")
            
            mask = Image.new("L", (inner_w, inner_h), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, inner_w, inner_h), radius=15, fill=255)
            card_resized.putalpha(mask)
            
            canvas = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
            canvas.paste(card_resized, (PAD, PAD), card_resized)
            final_composite = Image.alpha_composite(canvas, frame_img)
            
            output = BytesIO()
            final_composite.save(output, format="PNG")
            output.seek(0)
            return output


class FrameTestPromptView(discord.ui.View):
    def __init__(self, bot, card_url, char_name):
        super().__init__(timeout=120)
        self.bot = bot
        self.card_url = card_url
        self.char_name = char_name

    @discord.ui.button(label="Test Frame", style=discord.ButtonStyle.primary, emoji="🖼️")
    async def open_test_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FrameTestModal(self.bot, self.card_url, self.char_name))


class FrameTesterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "⚠️" or payload.user_id == self.bot.user.id:
            return
            
        try:
            channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            
            if message.author.id != KARUTA_BOT_ID or not message.embeds:
                return
                
            embed = message.embeds[0]
            title = str(embed.title) if embed.title else ""

            if "Character Lookup" not in title:
                return

            card_url = None
            if embed.image and embed.image.url:
                card_url = embed.image.url
            elif embed.thumbnail and embed.thumbnail.url:
                card_url = embed.thumbnail.url

            if not card_url:
                return
            
            char_name = "Unknown"
            if embed.description:
                for line in embed.description.splitlines():
                    if "Character" in line or "Character ·" in line:
                        char_name = line.split("·")[-1].replace("*", "").strip()
                        break

            user = await self.bot.fetch_user(payload.user_id)
            await channel.send(
                f"🔧 {user.mention}, initialize frame rendering protocol for **{char_name}**?",
                view=FrameTestPromptView(self.bot, card_url, char_name),
                delete_after=60
            )

        except Exception as e:
            print(f"Reaction Error: {e}")

async def setup(bot):
    await bot.add_cog(FrameTesterCog(bot))