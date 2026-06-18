import discord
from discord.ext import commands
from discord import app_commands
import asyncio

E_SPARKLE = "<:eight_side_sparkle:1516681364806570105>"    
E_LOTUS   = "<:red_lotus:1516679367743377448>"   
E_BOOK    = "<:book_ig:1516683126066253844>"    
E_FLOWERS = "<:two_flowers:1516684386546880614>"    
E_TIME    = "<:celestial_hourglass:1516684938509029396>"  

ROLES_TO_PING = [1515096544364331128, 1515097042131615775, 1503987120572858511, 1508333073668898996]


CUSTOM_LORE = {
    846366974325424158: {
        "seal": "The First Supreme Elder, **{name}**, descends upon the will of Heaven itself.\n> Activating the Rank 9 Immortal Gu House **Heaven Overseeing Tower**, they invoke the supreme killer move **Fate Vanquishing Decree**. Under the judgment of fate, this Heavenly Dao connection is forcefully suppressed and sealed.",

        "delete": "{E_TIME} **The First Supreme Elder, {name}, gazes down from atop Heaven Overseeing Tower.**\n> *'That which is not recorded within fate has no right to exist.'*\n> With a single decree, countless fate dao chains descend and erase this isolated realm from the river of history itself. *(Dissipating in 5 seconds...)*"
    },

    815099553032044576: {
        "seal": "The Second Supreme Elder, **{name}**, calmly opens their eyes.\n> Countless thoughts collide like stars as the Wisdom Path killer move **Star Thought Deduction** unfolds. Having seen all possible outcomes, they conclude this matter and sever the Heavenly Dao connection.",

        "delete": "{E_TIME} **The Second Supreme Elder, {name}, raises the legendary Immortal Gu, Wisdom Sword.**\n> A sword light flashes across heaven and earth. Before anyone can react, the causal threads sustaining this isolated realm are cleanly severed. *(Dissipating in 5 seconds...)*"
    },

    1300911596033282048: {
        "seal": "The Ceremony Elder, **{name}**, smiles gently.\n> *'Meeting is fate. Parting is also fate.'*\n> Summoning the renowned killer move **Farewell Friend Wind**, they send this Heavenly Dao connection drifting peacefully beyond the horizon.",

        "delete": "{E_TIME} **The Ceremony Elder, {name}, watches as a gentle wind rises.**\n> *'This old friend has lingered long enough. Allow me to send you on your final journey.'*\n> The majestic **Farewell Friend Wind** sweeps across the isolated realm, carrying every trace away into the boundless heavens. *(Dissipating in 5 seconds...)*"
    },

    1239587136978550804: {
        "seal": "Sect Elder **{name}** sits beneath the stars, unmoving as a mountain.\n> Employing the Wisdom Path killer move **Sitting and Forgetting Dao**, all disturbances are pacified. The petitioner's thoughts settle, and this matter is quietly sealed.",

        "delete": "{E_TIME} **Sect Elder {name} waves a sleeve toward the night sky.**\n> Activating the Star Path killer move **Myriad Star Fireflies**, countless starlights descend like a celestial river and consume this isolated realm. *(Dissipating in 5 seconds...)*"
    },

    978584340890013748: {
        "seal": "Sect Elder **{name}** traces a line through the River of Time.\n> Using the Time Path killer move **Time Cutting Edge**, they sever the future possibilities of this matter, bringing the deduction to its destined conclusion.",

        "delete": "{E_TIME} **Sect Elder {name} stands before the turbulent void.**\n> *'The destination has already been decided.'*\n> Activating **Fixed Immortal Travel**, the entire isolated realm vanishes from existence and is transported beyond mortal perception. *(Dissipating in 5 seconds...)*"
    }
}

def get_seal_message(user: discord.Member):
    if user.id in CUSTOM_LORE:
        lore_text = CUSTOM_LORE[user.id]["seal"].format(name=user.display_name)
    else:
        lore_text = f"The cultivator's connection to the Heavenly Dao has been severed by **{user.display_name}**."
        
    return f"{E_LOTUS} {lore_text}\n\nElders may review the remnants of this deduction, or use `/ticket delete` to shatter this realm completely."

def get_delete_message(user: discord.Member):
    if user.id in CUSTOM_LORE:
        return CUSTOM_LORE[user.id]["delete"].format(name=user.display_name, E_TIME=E_TIME)
    return f"{E_TIME} **{user.display_name} is severing connection to the Heavenly Dao...**\n> This inspiration will dissipate in 5 seconds."


class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Sever Connection", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        
        msg = get_delete_message(interaction.user)
        await interaction.channel.send(msg)
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
        desc += f"{E_FLOWERS} Please state the nature of your bottleneck or inquiry.\n"
        desc += f"{E_BOOK} The Wisdom Path elders will begin their deductions shortly.\n\n"
        desc += f"*(To sever this connection, press the red seal below or use `/ticket delete`)*"

        embed = discord.Embed(title="✦ . HEAVENLY DAO DEDUCTION . ✦", description=desc, color=0x6b1614)
        embed.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")
        
        await channel.send(content=f"{user.mention} {ping_str}", embed=embed, view=TicketControls())


class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(TicketPanel())
        self.bot.add_view(TicketControls())

    ticket_group = app_commands.Group(name="ticket", description="Manage Heavenly Dao connections")

    @ticket_group.command(name="close", description="Seal the connection (Removes the user, keeps channel for Elders)")
    async def close_ticket_cmd(self, interaction: discord.Interaction):
        if "inspiration-" not in interaction.channel.name:
            return await interaction.response.send_message("❌ This command can only be used in an Inspiration channel.", ephemeral=True)
        
        user_removed = False
        for target in list(interaction.channel.overwrites.keys()):
            if isinstance(target, discord.Member) and target != interaction.guild.me:
                await interaction.channel.set_permissions(target, overwrite=None)
                user_removed = True
                
        if user_removed:
            desc = get_seal_message(interaction.user)
            embed = discord.Embed(
                title="✦ . CONNECTION SEALED . ✦",
                description=desc,
                color=0x6b1614
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("⚠️ The connection is already sealed. The mortal has already been removed.", ephemeral=True)

    @ticket_group.command(name="delete", description="Shatter this isolated realm (Deletes the channel entirely)")
    async def delete_ticket_cmd(self, interaction: discord.Interaction):
        if "inspiration-" not in interaction.channel.name:
            return await interaction.response.send_message("❌ This command can only be used in an Inspiration channel.", ephemeral=True)
            
        msg = get_delete_message(interaction.user)
        await interaction.response.send_message(msg)
        await asyncio.sleep(5)
        await interaction.channel.delete()


    @commands.command(name="setup_tickets", aliases=["ticketpanel"])
    @commands.has_permissions(administrator=True)
    async def setup_tickets(self, ctx):
        
        desc = f"{E_SPARKLE} *Are you facing a bottleneck, or seeking the profound truths of the Great Dao?* {E_SPARKLE}\n"
        desc += "━━━━━━━━━━━━━━━━━━━━━━\n"
        desc += f"{E_BOOK} **Initiate a Natural Inspiration to:**\n"
        desc += f"✦ Deduce Karuta mechanics and worldly laws\n"
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