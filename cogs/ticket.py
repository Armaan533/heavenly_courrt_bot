import discord
from discord.ext import commands
import asyncio

E_SPARKLE = "<:eight_side_sparkle:1516681364806570105>"    
E_LOTUS   = "<:red_lotus:1516679367743377448>"   
E_BOOK    = "<:book_ig:1516683126066253844>"    
E_FLOWERS = "<:two_flowers:1516684386546880614>"    
E_TIME    = "<:celestial_hourglass:1516684938509029396>"  

ROLES_TO_PING = [1515096544364331128, 1515097042131615775, 1503987120572858511, 1508333073668898996]

class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Sever Connection", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        
        await interaction.channel.send(f"{E_TIME} **Severing connection to the Heavenly Dao...** This inspiration will dissipate in 5 seconds.")
        await asyncio.sleep(5)
        await interaction.channel.delete()


class TicketPanel(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Seek Natural Inspiration", style=discord.ButtonStyle.secondary, custom_id="create_ticket_btn", emoji=discord.PartialEmoji.from_str(E_LOTUS))
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        
        channel_name = f"inspiration-{user.name.lower()}"
        existing_channel = discord.utils.get(guild.channels, name=channel_name)
        if existing_channel:
            return await interaction.response.send_message(f"❌ You are already communing with the heavens here: {existing_channel.mention}", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True, read_message_history=True)
        }
        
        for role_id in ROLES_TO_PING:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)

        category = interaction.channel.category
        
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"Heavenly Dao Deduction for {user.display_name}"
        )

        await interaction.response.send_message(f"{E_SPARKLE} Your mind connects to the Heavenly Dao. Proceed to {channel.mention}.", ephemeral=True)

        ping_str = " ".join([f"<@&{r}>" for r in ROLES_TO_PING])
        
        desc = f"{E_SPARKLE} **{user.display_name} has connected to the Heavenly Dao.**\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        desc += f"{E_FLOWERS} Please state the nature of your tribulation.\n"
        desc += f"{E_BOOK} The Wisdom Path elders will begin their deductions shortly.\n\n"
        desc += f"*(To sever this connection, press the red seal below)*"

        embed = discord.Embed(title="✦ . HEAVENLY DAO DEDUCTION . ✦", description=desc, color=0x6b1614)
        embed.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")
        
        await channel.send(content=f"{user.mention} {ping_str}", embed=embed, view=TicketControls())


class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(TicketPanel())
        self.bot.add_view(TicketControls())

    @commands.command(name="setup_tickets", aliases=["ticketpanel"])
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx):
        
        desc = f"{E_SPARKLE} *Are you seeking the profound truths of the Great Dao?* {E_SPARKLE}\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        desc += f"{E_BOOK} **Initiate a Natural Inspiration to:**\n"
        desc += f"✦ Karuta mechanics or inquiries\n"
        desc += f"✦ Resolve Contribution & Clan tribulations\n"
        desc += f"✦ Report deviations in the Heavenly Dao (Bugs/Issues)\n"
        desc += f"✦ Seek general guidance from the sect's Wisdom Path elders\n\n"
        
        desc += f"{E_FLOWERS} *To reach the apex, one must continually question the heavens and earth. Do not hesitate to seek knowledge.*\n\n"
        
        desc += f"{E_LOTUS} **Laws of the Dao:**\n"
        desc += f"> ✦ The heavens take time to respond; wait patiently for an Elder's deduction.\n"
        desc += f"> ✦ Do not force multiple inspirations; duplicate requests disturb the Dao marks.\n"
        desc += f"> ✦ Maintain absolute reverence towards the immortals guiding your path.\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━"

        embed = discord.Embed(title="✦ . NATURAL INSPIRATION . ✦", description=desc, color=0x6b1614)
        embed.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")
        
        await ctx.message.delete()
        await ctx.send(embed=embed, view=TicketPanel())


async def setup(bot):
    await bot.add_cog(TicketCog(bot))