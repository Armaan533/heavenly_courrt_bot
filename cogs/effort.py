import discord
from discord.ext import commands
import re

class EffortResultView(discord.ui.View):
    def __init__(self, base_val, current_effort, mint_core, style_grade, style_val, tough_val, vanity_val, dye_delta, frame_delta, dye_frame_delta, mystic_delta, target_mystic_frame, target_tough, target_vanity):
        super().__init__(timeout=300)
        self.base_val = base_val
        self.current_effort = current_effort
        self.mint_core = mint_core
        self.style_grade = style_grade
        self.style_val = style_val
        self.tough_val = tough_val
        self.vanity_val = vanity_val
        self.dye_delta = dye_delta
        self.frame_delta = frame_delta
        self.dye_frame_delta = dye_frame_delta
        self.mystic_delta = mystic_delta
        self.target_mystic_frame = target_mystic_frame
        self.target_tough = target_tough
        self.target_vanity = target_vanity

    @discord.ui.button(label="Advanced Diagnostics", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def advanced_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticks = chr(96) * 3
        
        # Absolute base layout with maxed cosmetics, stripped of current combat stats
        cosmetic_base = self.mint_core + self.target_mystic_frame

        desc = f"⟡ **Projected Mint Core:** `{self.mint_core} ✧`\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"

        if self.style_grade == 'S':
            desc += "🎨 **Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n"
            desc += f"[ Max Cosmetics Already Applied ]\n"
            desc += f"{ticks}\n"
        else:
            desc += "🎨 **Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n"
            # HIDE DYE & FRAME IF IT'S ALREADY APPLIED (Delta is less than 5)
            if self.dye_frame_delta > 5:
                desc += f"[ Dye & Frame ]  -> {self.current_effort + self.dye_frame_delta} [+ {self.dye_frame_delta}]\n"
            desc += f"[ Mystic Frame ] -> {self.current_effort + self.mystic_delta} [+ {self.mystic_delta}]\n"
            desc += f"{ticks}\n"

        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        desc += "⚙️ **S-Style + Vanity & Toughness:**\n"
        desc += f"{ticks}ini\n"
        
        d_tough_val = max(1, round(self.base_val * 0.05)) if self.base_val >= 20 else 0
        d_vanity_val = max(1, round(self.base_val * 0.12)) if self.base_val >= 20 else 0

        desc += f"[ Toughness ]\n"
        desc += f"D Toughness  :: [{d_tough_val}]   -> {cosmetic_base + d_tough_val}\n"
        desc += f"S Toughness  :: [{self.target_tough}]  -> {cosmetic_base + self.target_tough}\n\n"
        
        desc += f"[ Vanity ]\n"
        desc += f"D Vanity     :: [0-{d_vanity_val}] -> {cosmetic_base} - {cosmetic_base + d_vanity_val}\n"
        desc += f"Max A Vanity :: [{self.target_vanity}]  -> {cosmetic_base + self.target_vanity}\n\n"
        
        desc += f"[ Maximum Theoretical ]\n"
        desc += f"D Vanity + S Tough.    -> {cosmetic_base + d_vanity_val + self.target_tough}\n"
        desc += f"Max A Vanity + S Tough -> {cosmetic_base + self.target_tough + self.target_vanity}\n"
        desc += f"{ticks}\n"
        
        desc += "*( ⚠️ Effort telemetry is currently in beta testing. Please report any math inconsistencies! )*\n"
        desc += "*(Note: True global scale may vary outcomes by ±1%)*"
        
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

    async def generate_result(self, interaction: discord.Interaction, multiplier: float):
        pure_naked_core = self.current_effort - self.style_val - self.tough_val - self.vanity_val
        mint_core = round(pure_naked_core * multiplier)

        target_dye = max(1, round(self.base_val * 0.25))
        target_tough = max(1, round(self.base_val * 0.25))
        target_vanity = self.base_val // 2

        if self.base_val >= 20:
            target_frame = round(self.base_val * 0.3) + 33
            mystic_dye = round(self.base_val * (14 / 15))
        else:
            target_frame = self.base_val
            mystic_dye = self.base_val

        target_dye_frame = target_dye + target_frame
        target_mystic_frame = target_frame + mystic_dye

        dye_delta = max(0, target_dye - self.style_val)
        frame_delta = max(0, target_frame - self.style_val)
        dye_frame_delta = max(0, target_dye_frame - self.style_val)
        mystic_delta = max(0, target_mystic_frame - self.style_val)

        ticks = chr(96) * 3
        
        desc = f"⟡ **Projected Mint Core:** `{mint_core} ✧`\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"

        if self.style_grade == 'S':
            desc += "🎨 **Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n"
            desc += f"[ Max Cosmetics (Mystic & Frame) Already Applied ]\n"
            desc += f"{ticks}\n"
        else:
            desc += "🎨 **Cosmetics Optimization:**\n"
            desc += f"{ticks}ini\n"
            if self.style_grade in ['F', 'C', 'A', 'D']:
                desc += f"[ Dye ]          -> {self.current_effort + dye_delta} [+ {dye_delta}]\n"
                desc += f"[ Frame ]        -> {self.current_effort + frame_delta} [+ {frame_delta}]\n"
            
            if self.style_grade == 'B':
                if dye_frame_delta > 5:
                    desc += f"; Card currently has Frame OR Mystic Dye applied\n"
                else:
                    desc += f"; Card currently has Frame AND Regular Dye applied\n"
            
            if dye_frame_delta > 5:
                desc += f"[ Dye & Frame ]  -> {self.current_effort + dye_frame_delta} [+ {dye_frame_delta}]\n"
                
            desc += f"[ Mystic Frame ] -> {self.current_effort + mystic_delta} [+ {mystic_delta}]\n"
            desc += f"{ticks}\n"

        desc += "*( ⚠️ Effort telemetry is currently in testing. Please report any math inconsistencies! )*"

        embed = discord.Embed(
            title="[ EFFORT TELEMETRY LOG ]",
            description=desc,
            color=0x8b0000
        )
        embed.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")

        view = EffortResultView(self.base_val, self.current_effort, mint_core, self.style_grade, self.style_val, self.tough_val, self.vanity_val, dye_delta, frame_delta, dye_frame_delta, mystic_delta, target_mystic_frame, target_tough, target_vanity)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Damaged", style=discord.ButtonStyle.danger)
    async def btn_damaged(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.generate_result(interaction, 4.0) 

    @discord.ui.button(label="Poor", style=discord.ButtonStyle.secondary)
    async def btn_poor(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.generate_result(interaction, 2.22) 

    @discord.ui.button(label="Good", style=discord.ButtonStyle.success)
    async def btn_good(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.generate_result(interaction, 1.53) 

    @discord.ui.button(label="Excellent", style=discord.ButtonStyle.primary)
    async def btn_excellent(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.generate_result(interaction, 1.17) 

    @discord.ui.button(label="Mint", style=discord.ButtonStyle.primary, emoji="✨")
    async def btn_mint(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.generate_result(interaction, 1.0) 


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