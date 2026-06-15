import discord
from discord.ext import commands
import re

class EffortResultView(discord.ui.View):
    def __init__(self, mint_core, style_grade, dye_add, frame_add, dye_frame_add, mystic_add, tough_add, vanity_add):
        super().__init__(timeout=300)
        self.mint_core = mint_core
        self.style_grade = style_grade
        self.dye_add = dye_add
        self.frame_add = frame_add
        self.dye_frame_add = dye_frame_add
        self.mystic_add = mystic_add
        self.tough_add = tough_add
        self.vanity_add = vanity_add

    @discord.ui.button(label="Advanced Diagnostics", style=discord.ButtonStyle.secondary, emoji="⚙️")
    async def advanced_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        ticks = chr(96) * 3
        
        desc = f"⟡ **Projected Mint Core:** `{self.mint_core} ✧`\n"
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
                desc += f"[ Dye ]          -> {self.mint_core + self.dye_add} [+ {self.dye_add}]\n"
                desc += f"[ Frame ]        -> {self.mint_core + self.frame_add} [+ {self.frame_add}]\n"
            
            if self.style_grade == 'B':
                desc += f"; Card currently has Frame OR Mystic Dye applied\n"
            
            desc += f"[ Dye & Frame ]  -> {self.mint_core + self.dye_frame_add} [+ {self.dye_frame_add}]\n"
            desc += f"[ Mystic Frame ] -> {self.mint_core + self.mystic_add} [+ {self.mystic_add}]\n"
            desc += f"{ticks}\n"

        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        desc += "⚙️ **S-Style + Vanity & Toughness:**\n"
        desc += f"{ticks}ini\n"
        desc += f"[ Toughness ]\n"
        desc += f"D Toughness  :: [+0]\n"
        desc += f"S Toughness  :: [+{self.tough_add}]\n\n"
        
        desc += f"[ Vanity ]\n"
        desc += f"D Vanity     :: [+0]\n"
        desc += f"Max A Vanity :: [+{self.vanity_add}]\n\n"
        
        max_optimized = self.mint_core + self.mystic_add + self.tough_add + self.vanity_add
        desc += f"[ Maximum Theoretical ]\n"
        desc += f"Max Vanity + S Toughness -> {max_optimized}\n"
        desc += f"{ticks}\n"
        
        desc += "*( ⚠️ Effort telemetry is currently in testing. Please report any math inconsistencies! )*"
        
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
        naked_core = self.current_effort - self.style_val - self.tough_val - self.vanity_val
        
        mint_core = round(naked_core * multiplier)

        dye_add = self.base_val
        frame_add = 30
        mystic_add = max(self.base_val + 10, 30) + 30
        tough_add = self.base_val
        vanity_add = self.base_val * 2

        if mint_core < 20: 
            dye_add = max(1, round(self.base_val * 0.25))
            frame_add = self.base_val
            mystic_add = self.base_val * 2
            tough_add = max(1, round(self.base_val * 0.5))
            vanity_add = max(1, round(self.base_val * 0.75))

        dye_frame_add = dye_add + frame_add
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
                desc += f"[ Dye ]          -> {mint_core + dye_add} [+ {dye_add}]\n"
                desc += f"[ Frame ]        -> {mint_core + frame_add} [+ {frame_add}]\n"
            if self.style_grade == 'B':
                desc += f"; Card currently has Frame OR Mystic Dye applied\n"
            
            desc += f"[ Dye & Frame ]  -> {mint_core + dye_frame_add} [+ {dye_frame_add}]\n"
            desc += f"[ Mystic Frame ] -> {mint_core + mystic_add} [+ {mystic_add}]\n"
            desc += f"{ticks}\n"

        desc += "*( ⚠️ Effort telemetry is currently in testing. Please report any math inconsistencies! )*"

        embed = discord.Embed(
            title="[ EFFORT TELEMETRY LOG ]",
            description=desc,
            color=0x8b0000
        )
        embed.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")

        view = EffortResultView(mint_core, self.style_grade, dye_add, frame_add, dye_frame_add, mystic_add, tough_add, vanity_add)
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
                color=0x2b2d31
            )

            view = QualityPromptView(base_val, current_effort, style_grade, style_val, tough_val, vanity_val)
            await message.reply(embed=prompt_embed, view=view, mention_author=False)

        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(EffortListener(bot))