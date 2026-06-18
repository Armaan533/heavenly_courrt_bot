import discord
from discord.ext import commands
import re

class EffortResultView(discord.ui.View):
    def __init__(self, current_effort, no_gd_effort, mint_effort, dye_delta, frame_delta, dye_frame_delta, mystic_delta, target_tough, target_vanity):
        super().__init__(timeout=300)
        self.current_effort = current_effort
        self.no_gd_effort = no_gd_effort
        self.mint_effort = mint_effort
        self.dye_delta = dye_delta
        self.frame_delta = frame_delta
        self.dye_frame_delta = dye_frame_delta
        self.mystic_delta = mystic_delta
        self.target_tough = target_tough
        self.target_vanity = target_vanity

    @discord.ui.button(label="Advanced Stats", style=discord.ButtonStyle.secondary, emoji="📊")
    async def advanced_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        cosmetic_base = self.mint_effort + self.mystic_delta
        
        desc = f"**Projected Mint Effort (No G/D):** `{self.mint_effort}`\n\n"
        desc += "**Cosmetics Optimization:**\n"
        desc += "```ini\n"
        desc += f"Dye              -> {self.mint_effort + self.dye_delta} [+ {self.dye_delta}]\n"
        desc += f"Frame            -> {self.mint_effort + self.frame_delta} [+ {self.frame_delta}]\n"
        desc += f"Dye & Frame      -> {self.mint_effort + self.dye_frame_delta} [+ {self.dye_frame_delta}]\n"
        desc += f"Mystic & Frame   -> {self.mint_effort + self.mystic_delta} [+ {self.mystic_delta}]\n"
        desc += "```\n"
        desc += "**S Style + Vanity & Toughness (Max Potential):**\n"
        desc += "```ini\n"
        desc += f"D Toughness  :: [0]  -> {cosmetic_base}\n"
        desc += f"S Toughness  :: [{self.target_tough}] -> {cosmetic_base + self.target_tough}\n\n"
        desc += f"D Vanity     :: [0]  -> {cosmetic_base}\n"
        desc += f"Max A Vanity :: [{self.target_vanity}] -> {cosmetic_base + self.target_vanity}\n\n"
        desc += f"Max Theoretical -> {cosmetic_base + self.target_tough + self.target_vanity}\n"
        desc += "```"

        embed = interaction.message.embeds[0]
        embed.description = desc
        button.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

class QualityPromptView(discord.ui.View):
    def __init__(self, char_name, base_val, true_effort, no_gd_effort):
        super().__init__(timeout=60)
        self.char_name = char_name
        self.base_val = base_val
        self.true_effort = true_effort
        self.no_gd_effort = no_gd_effort

    async def generate_result(self, interaction: discord.Interaction, missing_stars: int):
        multiplier = 1.89 ** missing_stars
        mint_base = self.base_val * multiplier
        mint_effort = int((self.no_gd_effort * multiplier) + 0.5)

        # Multipliers math
        dye_delta = int((mint_base * 0.25) + 0.5)
        frame_delta = int((mint_base * 0.93) + 0.5)
        dye_frame_delta = int((mint_base * 1.18) + 0.5)
        mystic_delta = int((mint_base * 1.86) + 0.5)

        target_tough = int((mint_base * 0.48) + 0.5)
        target_vanity = int((mint_base * 0.50) + 0.5)

        desc = "🔍 **Identified:**\n"
        desc += f"**Name:** {self.char_name}\n"
        desc += f"**Current Effort:** {self.true_effort}\n"
        
        if self.true_effort != self.no_gd_effort:
            desc += f"**No G/D Effort:** {self.no_gd_effort} *(Used for calculations)*\n"
        
        desc += "\n🖼️ **Dyes and Frame (At Mint):**\n"
        desc += "```ini\n"
        desc += f"Dye              -> {mint_effort + dye_delta} [+ {dye_delta}]\n"
        desc += f"Frame            -> {mint_effort + frame_delta} [+ {frame_delta}]\n"
        desc += f"Dye & Frame      -> {mint_effort + dye_frame_delta} [+ {dye_frame_delta}]\n"
        desc += f"Mystic & Frame   -> {mint_effort + mystic_delta} [+ {mystic_delta}]\n"
        desc += "```"

        embed = discord.Embed(title="Effort Calculator", description=desc, color=0x2b2d31)
        
        view = EffortResultView(self.true_effort, self.no_gd_effort, mint_effort, dye_delta, frame_delta, dye_frame_delta, mystic_delta, target_tough, target_vanity)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Damaged", style=discord.ButtonStyle.danger)
    async def btn_damaged(self, i: discord.Interaction, b: discord.ui.Button): await self.generate_result(i, 4) 
    @discord.ui.button(label="Poor", style=discord.ButtonStyle.secondary)
    async def btn_poor(self, i: discord.Interaction, b: discord.ui.Button): await self.generate_result(i, 3) 
    @discord.ui.button(label="Good", style=discord.ButtonStyle.success)
    async def btn_good(self, i: discord.Interaction, b: discord.ui.Button): await self.generate_result(i, 2) 
    @discord.ui.button(label="Excellent", style=discord.ButtonStyle.primary)
    async def btn_excellent(self, i: discord.Interaction, b: discord.ui.Button): await self.generate_result(i, 1) 
    @discord.ui.button(label="Mint", style=discord.ButtonStyle.primary, emoji="✨")
    async def btn_mint(self, i: discord.Interaction, b: discord.ui.Button): await self.generate_result(i, 0)

class EffortListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.processed_cache = []

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.process_effort_data(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        await self.process_effort_data(after)

    async def process_effort_data(self, message: discord.Message):
        if not message.author.bot or "karuta" not in message.author.name.lower(): return
        if not message.embeds: return
        if message.id in self.processed_cache: return

        embed = message.embeds[0]
        content_parts = []
        if embed.author and embed.author.name: content_parts.append(embed.author.name)
        if embed.title: content_parts.append(embed.title)
        if embed.description: content_parts.append(embed.description)
        for field in embed.fields:
            content_parts.append(field.name)
            content_parts.append(field.value)
            
        raw_text = " ".join(content_parts)
        clean_text = re.sub(r'[*`~_]', ' ', raw_text)
        clean_text = re.sub(r'\s+', ' ', clean_text)

        if "base value" not in clean_text.lower(): return

        try:
            base_match = re.search(r'(\d+)\s+base\s+value', clean_text, re.IGNORECASE)
            if not base_match: return
            base_val = int(base_match.group(1))
            
            self.processed_cache.append(message.id)
            if len(self.processed_cache) > 100: self.processed_cache.pop(0)

            char_name = "Unknown Character"
            name_match = re.search(r'Character\s+[\xb7\·]\s+(.*?)\s+\(', raw_text)
            if name_match:
                char_name = name_match.group(1).strip()

            def parse_stat(stat_name):
                match = re.search(r'(\d+)\s+\(([SABCDEF])\)\s+' + stat_name, clean_text, re.IGNORECASE)
                if match: return int(match.group(1)), match.group(2).upper()
                return 0, "F"

            wellness_val, _ = parse_stat("Wellness")
            grabber_val, _ = parse_stat("Grabber")
            dropper_val, _ = parse_stat("Dropper")
            
            effort_match = re.search(r'Effort\s+(\d+)', clean_text, re.IGNORECASE)
            visible_effort = int(effort_match.group(1)) if effort_match else base_val

            is_injured = "injured" in clean_text.lower() and "healthy" not in clean_text.lower()
            if is_injured:
                true_effort = (visible_effort * 2) + wellness_val
            else:
                true_effort = visible_effort

            no_gd_effort = true_effort - grabber_val - dropper_val

            prompt_desc = "Select the card's current quality to calculate effort projections:"
            prompt_embed = discord.Embed(
                title="Effort Calibration",
                description=prompt_desc,
                color=0x2b2d31
            )

            view = QualityPromptView(char_name, base_val, true_effort, no_gd_effort)
            await message.reply(embed=prompt_embed, view=view, mention_author=False)

        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(EffortListener(bot))