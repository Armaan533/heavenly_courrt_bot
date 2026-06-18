import discord
from discord.ext import commands
import re

class EffortResultView(discord.ui.View):
    def __init__(self, current_effort, no_gd_effort, mint_effort, dye_delta, frame_delta, dye_frame_delta, mystic_delta, tough_val, vanity_val, mint_base):
        super().__init__(timeout=300)
        self.current_effort = current_effort
        self.no_gd_effort = no_gd_effort
        self.mint_effort = mint_effort
        self.dye_delta = dye_delta
        self.frame_delta = frame_delta
        self.dye_frame_delta = dye_frame_delta
        self.mystic_delta = mystic_delta
        self.tough_val = tough_val
        self.vanity_val = vanity_val
        self.mint_base = mint_base

    @discord.ui.button(label="Advanced Stats", style=discord.ButtonStyle.secondary, emoji="📊")
    async def advanced_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        mystic_total_effort = self.mint_effort + self.mystic_delta
        base_sum = int(mystic_total_effort * 0.8)
        if base_sum + (base_sum // 4) < mystic_total_effort:
            base_sum += 1
            
        clean_sum = base_sum - self.tough_val - self.vanity_val
        
        target_d_tough = int((self.mint_base * 0.05) + 0.5)
        target_s_tough = int((self.mint_base * 0.25) + 0.5)
        target_d_van_max = int((self.mint_base * 0.125) + 0.5)
        target_a_vanity = int(self.mint_base // 2)

        def calc_eff(tough, vanity):
            raw = clean_sum + tough + vanity
            return raw + (raw // 4)

        v_dt = calc_eff(target_d_tough, self.vanity_val)
        v_st = calc_eff(target_s_tough, self.vanity_val)
        
        v_dv_min = calc_eff(self.tough_val, 0)
        v_dv_max = calc_eff(self.tough_val, target_d_van_max)
        v_av = calc_eff(self.tough_val, target_a_vanity)
        
        v_max_d_min = calc_eff(target_s_tough, 0)
        v_max_d_max = calc_eff(target_s_tough, target_d_van_max)
        v_max_a = calc_eff(target_s_tough, target_a_vanity)
        
        ticks = "```"
        desc = f"⟡ **Projected Mint Core:** `{self.mint_effort} ✧`\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        desc += "🎨 **Cosmetics Optimization:**\n"
        desc += f"{ticks}ini\n"
        desc += f"[ Dye ]            -> {self.mint_effort + self.dye_delta} [+ {self.dye_delta}]\n"
        desc += f"[ Frame ]          -> {self.mint_effort + self.frame_delta} [+ {self.frame_delta}]\n"
        desc += f"[ Dye & Frame ]    -> {self.mint_effort + self.dye_frame_delta} [+ {self.dye_frame_delta}]\n"
        desc += f"[ Mystic & Frame ] -> {self.mint_effort + self.mystic_delta} [+ {self.mystic_delta}]\n"
        desc += f"{ticks}\n"
        
        desc += "⚙️ **S-Style + Vanity & Toughness:**\n"
        desc += f"{ticks}ini\n"
        desc += f"[ Toughness ]\n"
        desc += f"D Toughness  :: [{target_d_tough}]  -> {v_dt}\n"
        desc += f"S Toughness  :: [{target_s_tough}] -> {v_st}\n\n"
        
        desc += f"[ Vanity ]\n"
        desc += f"D Vanity     :: [0-{target_d_van_max}] -> {v_dv_min} - {v_dv_max}\n"
        desc += f"Max A Vanity :: [{target_a_vanity}] -> {v_av}\n\n"
        
        desc += f"[ Max Possible Core ]\n"
        desc += f"D Vanity + S Tough -> {v_max_d_min} - {v_max_d_max}\n"
        desc += f"Max A Vanity + S Tough -> {v_max_a}\n"
        desc += f"{ticks}\n"
        
        if self.current_effort != self.no_gd_effort:
            desc += f"*( ⚖️ True Base Core without G/D transfers as {self.no_gd_effort} )*\n\n"
            
        desc += "( 💡 *Engine Updated: 100% Karuta Accuracy* )"

        embed = interaction.message.embeds[0]
        embed.description = desc
        button.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)


class QualityPromptView(discord.ui.View):
    def __init__(self, char_name, base_val, true_effort, no_gd_effort, style_applied, tough_val, vanity_val):
        super().__init__(timeout=60)
        self.char_name = char_name
        self.base_val = base_val
        self.true_effort = true_effort
        self.no_gd_effort = no_gd_effort
        self.style_applied = style_applied
        self.tough_val = tough_val
        self.vanity_val = vanity_val

    async def generate_result(self, interaction: discord.Interaction, missing_stars: int):
        multiplier = 1.89 ** missing_stars
        mint_base = self.base_val * multiplier
        mint_effort = int((self.true_effort * multiplier) + 0.5)

        dye_delta = int((mint_base * 0.25) + 0.5)
        frame_delta = int((mint_base * 0.93) + 0.5)
        dye_frame_delta = int((mint_base * 1.18) + 0.5)
        mystic_delta = int((mint_base * 1.86) + 0.5)

        ticks = "```"
        desc = f"⟡ **Projected Mint Core:** `{mint_effort} ✧`\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        desc += "🎨 **Cosmetics Optimization:**\n"
        desc += f"{ticks}ini\n"
        desc += f"[ Dye ]            -> {mint_effort + dye_delta} [+ {dye_delta}]\n"
        desc += f"[ Frame ]          -> {mint_effort + frame_delta} [+ {frame_delta}]\n"
        desc += f"[ Dye & Frame ]    -> {mint_effort + dye_frame_delta} [+ {dye_frame_delta}]\n"
        desc += f"[ Mystic & Frame ] -> {mint_effort + mystic_delta} [+ {mystic_delta}]\n"
        desc += f"{ticks}\n"
        
        if self.true_effort != self.no_gd_effort:
            desc += f"*( ⚖️ True Base Core without G/D transfers as {self.no_gd_effort} )*\n\n"

        embed = discord.Embed(
            title="[ EFFORT TELEMETRY LOG ]",
            description=desc,
            color=0x6b1614
        )
        embed.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")

        view = EffortResultView(self.true_effort, self.no_gd_effort, mint_effort, dye_delta, frame_delta, dye_frame_delta, mystic_delta, self.tough_val, self.vanity_val, mint_base)
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
        clean_text = raw_text.replace('·', ' ').replace('\xb7', ' ')
        clean_text = re.sub(r'[*`~_]', ' ', clean_text)
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

            style_val, style_grade = parse_stat("Style")
            wellness_val, _ = parse_stat("Wellness")
            tough_val, _ = parse_stat("Toughness")
            vanity_val, _ = parse_stat("Vanity")
            grabber_val, _ = parse_stat("Grabber")
            dropper_val, _ = parse_stat("Dropper")
            
            style_applied = "None"
            if style_grade != "F":
                style_applied = f"Grade {style_grade}"
            
            effort_match = re.search(r'Effort\s+(\d+)', clean_text, re.IGNORECASE)
            visible_effort = int(effort_match.group(1)) if effort_match else base_val

            is_injured = "injured" in clean_text.lower() and "healthy" not in clean_text.lower()
            if is_injured:
                true_effort = (visible_effort * 2) + wellness_val
            else:
                true_effort = visible_effort

            no_gd_effort = true_effort - grabber_val - dropper_val

            prompt_desc = f"To calculate accurate cosmetics, what is the current quality of this card?\n\n"
            prompt_desc += "*(Select a condition below to generate the telemetry log)*"

            prompt_embed = discord.Embed(
                title="[ EFFORT CALIBRATION ]",
                description=prompt_desc,
                color=0x6b1614
            )

            view = QualityPromptView(char_name, base_val, true_effort, no_gd_effort, style_applied, tough_val, vanity_val)
            await message.reply(embed=prompt_embed, view=view, mention_author=False)

        except Exception:
            pass

async def setup(bot):
    await bot.add_cog(EffortListener(bot))