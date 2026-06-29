import discord
from discord.ext import commands
import aiohttp
from io import BytesIO
from PIL import Image, ImageOps, ImageDraw
import asyncio
import numpy as np
from frame_prices import FRAME_DB

KARUTA_BOT_ID = 646937666251915264

BG_RGB = np.array([49.0, 51.0, 56.0], dtype=np.float32)
BG_LUM = float(BG_RGB[0] * 0.299 + BG_RGB[1] * 0.587 + BG_RGB[2] * 0.114)  

PAD_X = 26
PAD_Y = 38

FADE = 20.0

T_LOW_CENTER  = 5.0
T_HIGH_CENTER = 80.0   

T_LOW_EDGE  = 2.0
T_HIGH_EDGE = 18.0

SAT_THRESHOLD = 0.10

SAT_WEIGHT = 0.9

DARK_BORDER_SLACK = 8.0   
DARK_BORDER_RANGE = 40.0  

UNMAT_COLORS = True
UNMAT_MIN_ALPHA = 0.15   

ALPHA_GAMMA = 1.25

CORNER_RADIUS = 20


class FrameTestModal(discord.ui.Modal, title="Frame Rendering Matrix"):
    frame_name = discord.ui.TextInput(
        label="Enter Frame Name",
        placeholder="e.g. Voidspawn, Hacker, Spring..."
    )

    def __init__(self, bot, card_url, char_name, prompt_message):
        super().__init__()
        self.bot = bot
        self.card_url = card_url
        self.char_name = char_name
        self.prompt_message = prompt_message

    async def on_submit(self, interaction: discord.Interaction):
        f_name = self.frame_name.value.strip().lower()

        try:
            await self.prompt_message.delete()
        except Exception:
            pass

        match = next((n for n in FRAME_DB if f_name in n.lower()), None)
        if not match:
            return await interaction.response.send_message(
                f"❌ Frame `{f_name}` not found in the database.", ephemeral=True
            )

        frame_url = FRAME_DB[match].get("image")
        if not frame_url:
            return await interaction.response.send_message(
                f"❌ No image mapped for {match.title()}.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=False)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.card_url) as card_resp, \
                           session.get(frame_url) as frame_resp:

                    if card_resp.status != 200 or frame_resp.status != 200:
                        return await interaction.followup.send(
                            "❌ Failed to fetch assets from Discord servers."
                        )

                    card_bytes  = await card_resp.read()
                    frame_bytes = await frame_resp.read()

                    output_buffer = await asyncio.to_thread(
                        self.process_frame, card_bytes, frame_bytes
                    )

                    fname = f"preview_{match.replace(' ', '_')}.png"
                    file  = discord.File(fp=output_buffer, filename=fname)

                    embed = discord.Embed(
                        title="✦ . FRAME RENDER . ✦",
                        description=f"**Character:** {self.char_name}\n**Frame:** {match.title()}",
                        color=0x2b2d31,
                    )
                    embed.set_image(url=f"attachment://{fname}")

                    await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            await interaction.followup.send(f"❌ **Render Error:** {e}")

    
    
    
    def process_frame(self, card_bytes: bytes, frame_bytes: bytes) -> BytesIO:
        """
        Multi-signal un-matting algorithm.

        Three independent alpha signals are computed then max-blended:

          A) COLOR DISTANCE  — how far is the pixel from the background grey?
             Varies spatially: strict in the centre (only vivid glows survive),
             lenient at edges (dark borders are preserved).

          B) SATURATION       — any pixel with noticeable colour is frame art.
             Catches golden borders, neon glows, and coloured effects that a
             pure-luminance check would miss.

          C) DARK BORDER      — pixels darker than BG_LUM near the edges are
             almost certainly part of the frame border, not the background.

        After blending, an optional colour un-matting step strips the grey
        tint from semi-transparent glow pixels to produce purer colours.
        """
        with Image.open(BytesIO(card_bytes)).convert("RGBA") as card_img, \
             Image.open(BytesIO(frame_bytes)).convert("RGBA") as frame_img:

            fw, fh = frame_img.size

            try:
                resample = Image.Resampling.LANCZOS
            except AttributeError:
                resample = Image.ANTIALIAS  

            card_resized = ImageOps.fit(card_img, (fw, fh), method=resample).convert("RGBA")
            frame_arr    = np.array(frame_img, dtype=np.float32)

            r = frame_arr[:, :, 0]
            g = frame_arr[:, :, 1]
            b = frame_arr[:, :, 2]
            
            orig_a = frame_arr[:, :, 3] / 255.0

            
            dist = np.sqrt((r - BG_RGB[0])**2 + (g - BG_RGB[1])**2 + (b - BG_RGB[2])**2)

            
            
            y_idx, x_idx = np.ogrid[:fh, :fw]
            edge_x = np.clip(np.minimum(x_idx - PAD_X,
                                        (fw - PAD_X) - x_idx) / FADE, 0.0, 1.0)
            edge_y = np.clip(np.minimum(y_idx - PAD_Y,
                                        (fh - PAD_Y) - y_idx) / FADE, 0.0, 1.0)
            centre = np.minimum(edge_x, edge_y)   

            
            t_low  = T_LOW_EDGE  + (T_LOW_CENTER  - T_LOW_EDGE)  * centre
            t_high = T_HIGH_EDGE + (T_HIGH_CENTER - T_HIGH_EDGE) * centre

            color_alpha = np.clip((dist - t_low) / (t_high - t_low + 1e-6), 0.0, 1.0)

            
            c_max = np.maximum(np.maximum(r, g), b)
            c_min = np.minimum(np.minimum(r, g), b)
            sat   = np.where(c_max > 1e-5, (c_max - c_min) / c_max, 0.0)

            
            sat_alpha = np.clip(
                (sat - SAT_THRESHOLD) / (1.0 - SAT_THRESHOLD + 1e-6), 0.0, 1.0
            ) * SAT_WEIGHT

            
            lum = r * 0.299 + g * 0.587 + b * 0.114

            
            dark_excess = BG_LUM - DARK_BORDER_SLACK - lum   
            dark_signal = np.clip(dark_excess / DARK_BORDER_RANGE, 0.0, 1.0)

            
            
            
            dark_alpha = dark_signal * (1.0 - centre)

            
            raw_alpha = np.maximum(color_alpha,
                        np.maximum(sat_alpha, dark_alpha))

            
            raw_alpha = raw_alpha * orig_a

            
            final_alpha = np.power(np.clip(raw_alpha, 0.0, 1.0), ALPHA_GAMMA)

            
            
            
            if UNMAT_COLORS:
                safe_a = np.where(final_alpha >= UNMAT_MIN_ALPHA, final_alpha, 1.0)
                safe_a = safe_a[:, :, np.newaxis]            

                stacked_bg = BG_RGB[np.newaxis, np.newaxis, :]  
                rgb        = np.stack([r, g, b], axis=-1)       
                fa_3d      = final_alpha[:, :, np.newaxis]

                unmatted   = (rgb - stacked_bg * (1.0 - fa_3d)) / safe_a
                unmatted   = np.clip(unmatted, 0.0, 255.0)

                
                apply_mask = (final_alpha >= UNMAT_MIN_ALPHA)[:, :, np.newaxis]
                rgb_out    = np.where(apply_mask, unmatted, rgb)

                frame_arr[:, :, 0] = rgb_out[:, :, 0]
                frame_arr[:, :, 1] = rgb_out[:, :, 1]
                frame_arr[:, :, 2] = rgb_out[:, :, 2]

            frame_arr[:, :, 3] = np.clip(final_alpha * 255.0, 0.0, 255.0)
            clean_frame = Image.fromarray(frame_arr.astype(np.uint8), "RGBA")

            
            result = Image.alpha_composite(card_resized, clean_frame)

            mask = Image.new("L", (fw, fh), 0)
            draw = ImageDraw.Draw(mask)
            draw.rounded_rectangle((0, 0, fw, fh), radius=CORNER_RADIUS, fill=255)
            result.putalpha(mask)

            output = BytesIO()
            result.save(output, format="PNG")
            output.seek(0)
            return output


class FrameTestPromptView(discord.ui.View):
    def __init__(self, bot, card_url, char_name):
        super().__init__(timeout=60)
        self.bot       = bot
        self.card_url  = card_url
        self.char_name = char_name

    @discord.ui.button(label="Test Frame", style=discord.ButtonStyle.danger, emoji="⚙️")
    async def open_test_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message(
                "❌ Access Denied. Administrator clearance required.", ephemeral=True
            )
        await interaction.response.send_modal(
            FrameTestModal(self.bot, self.card_url, self.char_name, interaction.message)
        )


class FrameTesterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id != KARUTA_BOT_ID or not message.embeds:
            return
        embed = message.embeds[0]
        if embed.title and "Character Lookup" in str(embed.title):
            try:
                await message.add_reaction("⚠️")
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.author.id != KARUTA_BOT_ID or not after.embeds:
            return
        embed = after.embeds[0]
        if embed.title and "Character Lookup" in str(embed.title):
            has_reaction = any(str(r.emoji) == "⚠️" and r.me for r in after.reactions)
            if not has_reaction:
                try:
                    await after.add_reaction("⚠️")
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "⚠️" or payload.user_id == self.bot.user.id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        member = guild.get_member(payload.user_id) or await guild.fetch_member(payload.user_id)
        if not member or not member.guild_permissions.administrator:
            return

        try:
            channel = self.bot.get_channel(payload.channel_id) or \
                      await self.bot.fetch_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)

            if message.author.id != KARUTA_BOT_ID or not message.embeds:
                return

            embed = message.embeds[0]
            if not embed.title or "Character Lookup" not in str(embed.title):
                return

            card_url = None
            if embed.image and embed.image.url:
                card_url = embed.image.url
            elif embed.thumbnail and embed.thumbnail.url:
                card_url = embed.thumbnail.url

            if not card_url:
                return

            
            if "?" in card_url:
                card_url = card_url.split("?")[0]

            char_name = "Unknown"
            if embed.description:
                for line in embed.description.splitlines():
                    if "Character" in line:
                        char_name = line.split("·")[-1].replace("*", "").strip()
                        break

            await channel.send(
                f"🔧 **Session Initialized:** {member.mention}, "
                f"render a custom workspace for **{char_name}**?",
                view=FrameTestPromptView(self.bot, card_url, char_name),
                delete_after=60,
            )

        except Exception as e:
            print(f"Reaction Session Error: {e}")


async def setup(bot):
    await bot.add_cog(FrameTesterCog(bot))