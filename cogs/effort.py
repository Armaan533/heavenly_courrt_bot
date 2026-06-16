import discord
from discord.ext import commands
import re

class EffortResultView(discord.ui.View):
    def __init__(self, scaled_base, current_effort, mint_core, style_grade, style_val, tough_val, vanity_val, dye_frame_delta, mystic_delta, target_mystic_frame, target_tough, target_vanity):
        super().__init__(timeout=300)
        self.scaled_base = scaled_base
        self.current_effort = current_effort
        self.mint_core = mint_core
        self.style_grade = style_grade
        self.style_val = style_val
        self.tough_val = tough_val
        self.vanity_val = vanity_val
        self.dye_frame_delta = dye_frame_delta
        self.mystic_delta = mystic_delta
        self.target_mystic_frame = target_mystic_frame
        self.target_tough = target_tough
        self.target_vanity = target_vanity

    @discord.ui.button(label="Advanced Diagnostics", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def advanced_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticks = chr(96) * 3
        cosmetic_base = self.mint_core + self.target_mystic_frame

        desc = f"⟡ **Projected Mint Core:** `{self.mint_core} ✧`\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"

        if self.style_grade == 'S':
            desc += "🎨 **Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n[ Max Cosmetics Already Applied ]\n{ticks}\n"
        else:
            desc += "🎨 **Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n"
            if self.dye_frame_delta > 5:
                desc += f"[ Dye & Frame ]  -> {self.current_effort + self.dye_frame_delta} [+ {self.dye_frame_delta}]\n"
            desc += f"[ Mystic Frame ] -> {self.current_effort + self.mystic_delta} [+ {self.mystic_delta}]\n"
            desc += f"{ticks}\n"

        desc += "⚙️ **S-Style + Vanity & Toughness:**\n"
        desc += f"{ticks}ini\n"
        d_tough_val = max(1, round(self.scaled_base * 0.05)) if self.scaled_base >= 20 else 0
        d_vanity_val = max(1, round(self.scaled_base * 0.12)) if self.scaled_base >= 20 else 0

        desc += f"[ Toughness ]\n"
        desc += f"D Toughness  :: [{d_tough_val}]   -> {cosmetic_base + d_tough_val}\n"
        desc += f"S Toughness  :: [{self.target_tough}]  -> {cosmetic_base + self.target_tough}\n\n"
        desc += f"[ Vanity ]\n"
        desc += f"D Vanity     :: [0-{d_vanity_val}] -> {cosmetic_base} - {cosmetic_base + d_vanity_val}\n"
        desc += f"Max A Vanity :: [{self.target_vanity}]  -> {cosmetic_base + self.target_vanity}\n\n"
        desc += f"[ Max Theoretical ]\n"
        desc += f"Max A Vanity + S Tough -> {cosmetic_base + self.target_tough + self.target_vanity}\n"
        desc += f"{ticks}\n"
        
        desc += "*( ⚠️ Beta: Report any math inconsistencies! )*"
        
        embed = interaction.message.embeds[0]
        embed.description = desc
        button.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)


class QualityPromptView(discord.ui.View):
    def __init__(self, base_val, current_effort, style_grade, style_val, tough_val, vanity_val):
        super().__init__(timeout=60)
        self.base_val, self.current_effort = base_val, current_effort
        self.style_grade, self.style_val = style_grade, style_val
        self.tough_val, self.vanity_val = tough_val, vanity_val

    async def generate_result(self, interaction: discord.Interaction, multiplier: float):
        pure_naked_core = self.current_effort - self.style_val - self.tough_val - self.vanity_val
        mint_core = round(pure_naked_core * multiplier)
        
        # CRITICAL FIX: Scale the Base Value to Mint BEFORE calculating cosmetics!
        scaled_base = self.base_val * multiplier

        # High-Fidelity Scaling Curves derived from True Mint Base
        target_frame = round(scaled_base * 0.3) + 33 if scaled_base >= 20 else round(scaled_base)
        target_dye = max(1, round(scaled_base * 0.25))
        target_dye_frame = target_dye + target_frame
        target_mystic = round(scaled_base * (14/15)) + target_frame
        
        target_tough = round(scaled_base * 0.32) if scaled_base >= 20 else max(1, round(scaled_base * 0.25))
        target_vanity = round(scaled_base * 0.60) if scaled_base >= 20 else max(1, round(scaled_base * 0.75))

        dye_frame_delta = max(0, target_dye_frame - self.style_val)
        mystic_delta = max(0, target_mystic - self.style_val)

        ticks = chr(96) * 3
        desc = f"⟡ **Projected Mint Core:** `{mint_core} ✧`\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        desc += "🎨 **Cosmetics Optimization:**\n"
        desc += f"{ticks}ini\n"
        
        if self.style_grade == 'S':
            desc += f"[ Max Cosmetics Already Applied ]\n"
        else:
            if self.style_grade == 'B':
                if dye_frame_delta > 5:
                    desc += f"; Card currently has Frame OR Mystic Dye applied\n"
                else:
                    desc += f"; Card currently has Frame AND Regular Dye applied\n"
            
            # Hide Dye & Frame if it is already basically maxed (delta less than 5)
            if dye_frame_delta > 5:
                desc += f"[ Dye & Frame ]  -> {self.current_effort + dye_frame_delta} [+ {dye_frame_delta}]\n"
                
            desc += f"[ Mystic Frame ] -> {self.current_effort + mystic_delta} [+ {mystic_delta}]\n"
            
        desc += f"{ticks}\n"
        desc += "*( ⚠️ Note: Keqing estimates using a database. Fang Yuan calculates mathematically from your exact card. )*"

        embed = discord.Embed(title="[ EFFORT TELEMETRY LOG ]", description=desc, color=0x8b0000)
        embed.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")

        view = EffortResultView(scaled_base, self.current_effort, mint_core, self.style_grade, self.style_val, self.tough_val, self.vanity_val, dye_frame_delta, mystic_delta, target_mystic, target_tough, target_vanity)
        await interaction.response.edit_message(embed=embed, view=view)

    # Multipliers set to perfectly mirror Karuta's internal halving mechanic
    @discord.ui.button(label="Damaged", style=discord.ButtonStyle.danger)
    async def btn_damaged(self, i: discord.Interaction, b: discord.ui.Button): await self.generate_result(i, 16.0)
    @discord.ui.button(label="Poor", style=discord.ButtonStyle.secondary)
    async def btn_poor(self, i: discord.Interaction, b: discord.ui.Button): await self.generate_result(i, 8.0)
    @discord.ui.button(label="Good", style=discord.ButtonStyle.success)
    async def btn_good(self, i: discord.Interaction, b: discord.ui.Button): await self.generate_result(i, 4.0)
    @discord.ui.button(label="Excellent", style=discord.ButtonStyle.primary)
    async def btn_excellent(self, i: discord.Interaction, b: discord.ui.Button): await self.generate_result(i, 2.0)
    @discord.ui.button(label="Mint", style=discord.ButtonStyle.primary, emoji="✨")
    async def btn_mint(self, i: discord.Interaction, b: discord.ui.Button): await self.generate_result(i, 1.0)


class EffortListener(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @commands.Cog.listener()
    async def on_message(self, m: discord.Message): await self.process(m)
    @commands.Cog.listener()
    async def on_message_edit(self, b, a: discord.Message): await self.process(a)

    async def process(self, m: discord.Message):
        if not m.author.bot or "karuta" not in m.author.name.lower() or not m.embeds or "base value" not in str(m.embeds[0].to_dict()).lower(): return
        e = m.embeds[0]
        txt = re.sub(r'[*`~_]', ' ', " ".join([e.author.name or "", e.title or "", e.description or ""] + [f.name + f.value for f in e.fields]))
        base = int(re.search(r'(\d+)\s+base\s+value', txt, re.IGNORECASE).group(1))
        
        def p(n): return int(re.search(r'(\d+)\s+\([SABCDEF]\)\s+'+n, txt, re.IGNORECASE).group(1)) if re.search(r'(\d+)\s+\([SABCDEF]\)\s+'+n, txt, re.IGNORECASE) else 0
        
        view = QualityPromptView(base, int(re.search(r'Effort\s+(\d+)', txt, re.IGNORECASE).group(1)), re.search(r'\(([SABCDEF])\)\s+Style', txt, re.IGNORECASE).group(1).upper() if re.search(r'\(([SABCDEF])\)\s+Style', txt, re.IGNORECASE) else "F", p("Style"), p("Toughness"), p("Vanity"))
        await m.reply(embed=discord.Embed(title="[ EFFORT CALIBRATION ]", description="**What is the quality of this card?**\n*Select a condition below to generate the log:*", color=0x8b0000), view=view, mention_author=False)

async def setup(bot): await bot.add_cog(EffortListener(bot))