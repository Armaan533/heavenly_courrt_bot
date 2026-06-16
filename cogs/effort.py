import discord
from discord.ext import commands
import re

def s_round(n):
    """Standard math rounding (half up) to match Karuta's exact internal rounding."""
    return int(n + 0.5)

class EffortResultView(discord.ui.View):
    def __init__(self, base_val, current_effort, mint_core, style_grade, style_val, dye_delta, frame_delta, dye_frame_delta, mystic_delta, target_mystic_frame, target_tough, target_vanity, show_dye_frame):
        super().__init__(timeout=300)
        self.base_val = base_val
        self.current_effort = current_effort
        self.mint_core = mint_core
        self.style_grade = style_grade
        self.style_val = style_val
        self.dye_delta = dye_delta
        self.frame_delta = frame_delta
        self.dye_frame_delta = dye_frame_delta
        self.mystic_delta = mystic_delta
        self.target_mystic_frame = target_mystic_frame
        self.target_tough = target_tough
        self.target_vanity = target_vanity
        self.show_dye_frame = show_dye_frame

    @discord.ui.button(label="Advanced Diagnostics", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def advanced_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticks = chr(96) * 3
        cosmetic_base = self.mint_core + self.mystic_delta

        desc = f"⟡ **Projected Mint Core:** `{self.mint_core} ✧`\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"

        if self.style_grade == 'S':
            desc += "🎨 **Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n[ Max Cosmetics Already Applied ]\n{ticks}\n"
        else:
            desc += "🎨 **Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n"
            if self.show_dye_frame:
                desc += f"[ Dye & Frame ]  -> {self.mint_core + self.dye_frame_delta} [+ {self.dye_frame_delta}]\n"
            desc += f"[ Mystic Frame ] -> {self.mint_core + self.mystic_delta} [+ {self.mystic_delta}]\n"
            desc += f"{ticks}\n"

        desc += "⚙️ **S-Style + Vanity & Toughness:**\n"
        desc += f"{ticks}ini\n"

        desc += f"[ Toughness ]\n"
        desc += f"D Toughness  :: [0]   -> {cosmetic_base}\n"
        desc += f"S Toughness  :: [{self.target_tough}]  -> {cosmetic_base + self.target_tough}\n\n"
        
        desc += f"[ Vanity ]\n"
        desc += f"D Vanity     :: [0] -> {cosmetic_base}\n"
        desc += f"Max A Vanity :: [{self.target_vanity}]  -> {cosmetic_base + self.target_vanity}\n\n"
        
        desc += f"[ Max Theoretical ]\n"
        desc += f"Max A Vanity + S Tough -> {cosmetic_base + self.target_tough + self.target_vanity}\n"
        desc += f"{ticks}\n"
        
        desc += "*( 💡 Math Note: True gain tracking accounts for automatic Wellness scaling. )*"
        
        embed = interaction.message.embeds[0]
        embed.description = desc
        button.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)


class QualityPromptView(discord.ui.View):
    def __init__(self, base_val, current_effort, style_grade, style_val, tough_val, vanity_val):
        super().__init__(timeout=60)
        self.base_val = base_val
        self.current_effort = current_effort
        self.style_grade = style_grade
        self.style_val = style_val
        self.tough_val = tough_val
        self.vanity_val = vanity_val

    async def generate_result(self, interaction: discord.Interaction, missing_stars: int):
        # 1. Reverse the degradation to find the True Mint state
        multiplier = 1.89 ** missing_stars
        mint_base = self.base_val * multiplier
        mint_effort = s_round(self.current_effort * multiplier)
        mint_style = self.style_val * multiplier

        # 2. Calculate the theoretical Style caps at Mint condition
        target_dye_s = max(1, s_round(mint_base * 0.25))
        target_frame_s = s_round(mint_base * 0.9375)
        target_dye_frame_s = target_dye_s + target_frame_s
        target_mystic_s = s_round(mint_base * 1.5) # The ultimate hard cap

        # 3. Dynamic Gain Calculator (Accounts for Style AND the 25% Wellness Drag)
        def calc_true_gain(target_style, current_style):
            t_s = s_round(target_style)
            c_s = s_round(current_style)
            if t_s <= c_s:
                return 0
            delta_style = t_s - c_s
            wellness_bonus = s_round(t_s * 0.25) - s_round(c_s * 0.25)
            return delta_style + wellness_bonus

        dye_delta = calc_true_gain(target_dye_s, mint_style)
        frame_delta = calc_true_gain(target_frame_s, mint_style)
        dye_frame_delta = calc_true_gain(target_dye_frame_s, mint_style)
        mystic_delta = calc_true_gain(target_mystic_s, mint_style)

        # 4. Smart hide logic: If their style is higher than just a frame, they already have a dye.
        show_dye_frame = s_round(mint_style) <= target_frame_s

        # 5. Combat & Vanity Targets
        target_tough = max(1, s_round(mint_base * 0.25))
        target_vanity = int(mint_base // 2)

        ticks = chr(96) * 3
        desc = f"⟡ **Projected Mint Core:** `{mint_effort} ✧`\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"

        if self.style_grade == 'S':
            desc += "🎨 **Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n"
            desc += f"[ Max Cosmetics Already Applied ]\n"
            desc += f"{ticks}\n"
        else:
            desc += "🎨 **Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n"
            
            if self.style_grade in ['F', 'C', 'A', 'D']:
                desc += f"[ Dye ]          -> {mint_effort + dye_delta} [+ {dye_delta}]\n"
                desc += f"[ Frame ]        -> {mint_effort + frame_delta} [+ {frame_delta}]\n"
            
            if self.style_grade == 'B':
                if show_dye_frame:
                    desc += f"; Card currently has Frame OR Mystic Dye applied\n"
                else:
                    desc += f"; Card currently has Frame AND Regular Dye applied\n"
            
            if show_dye_frame:
                desc += f"[ Dye & Frame ]  -> {mint_effort + dye_frame_delta} [+ {dye_frame_delta}]\n"
                
            desc += f"[ Mystic Frame ] -> {mint_effort + mystic_delta} [+ {mystic_delta}]\n"
            desc += f"{ticks}\n"

        desc += "*( ⚠️ Beta: Report any math inconsistencies! )*"

        embed = discord.Embed(
            title="[ EFFORT TELEMETRY LOG ]",
            description= "> 💡 **Tip:** *Run `kci` right before `kwi` for the most accurate Mint projections!*",
            color=0x8b0000
        )
        embed.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")

        view = EffortResultView(self.base_val, self.current_effort, mint_effort, self.style_grade, self.style_val, dye_delta, frame_delta, dye_frame_delta, mystic_delta, target_mystic_s, target_tough, target_vanity, show_dye_frame)
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
        if not message.author.bot or "karuta" not in message.author.name.lower():
            return
        if not message.embeds:
            return
        if message.id in self.processed_cache:
            return

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
        clean_text = re.sub(r'[^\x20-\x7E]', ' ', clean_text)
        clean_text = re.sub(r'\s+', ' ', clean_text)

        if "base value" not in clean_text.lower():
            return

        try:
            base_match = re.search(r'(\d+)\s+base\s+value', clean_text, re.IGNORECASE)
            if not base_match:
                return
            base_val = int(base_match.group(1))
            
            self.processed_cache.append(message.id)
            if len(self.processed_cache) > 100:
                self.processed_cache.pop(0)

            def parse_stat(stat_name):
                match = re.search(r'(\d+)\s+\(([SABCDEF])\)\s+' + stat_name, clean_text, re.IGNORECASE)
                if match:
                    return int(match.group(1)), match.group(2).upper()
                return 0, "F"

            style_val, style_grade = parse_stat("Style")
            tough_val, _ = parse_stat("Toughness")
            vanity_val, _ = parse_stat("Vanity")
            
            effort_match = re.search(r'Effort\s+(\d+)', clean_text, re.IGNORECASE)
            current_effort = int(effort_match.group(1)) if effort_match else base_val

            prompt_desc = f"To calculate accurate cosmetics, what is the current quality of this card?\n\n"
            prompt_desc += "*(Select a condition below to generate the telemetry log)*"

            prompt_embed = discord.Embed(
                title="[ EFFORT CALIBRATION ]",
                description=prompt_desc,
                color=0x8b0000
            )

            view = QualityPromptView(base_val, current_effort, style_grade, style_val, tough_val, vanity_val)
            await message.reply(embed=prompt_embed, view=view, mention_author=False)

        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(EffortListener(bot))