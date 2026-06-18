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
    # (me) - Sword Path / Heaven's Path
    846366974325424158: {
        "seal": "The First Supreme Elder, **{name}**, slowly clasps their hands before their chest.\n> Heaven and earth fall dead silent as endless sword light gathers. The first finger rises, and sword intent pierces the firmament; the second finger rises, and space itself fractures. \n> Before the third can even emerge, all outcomes are ruthlessly severed. Under the absolute might of **Five Finger Fist Heart Sword**, this Heavenly Dao connection is forcibly sealed.",
        "delete": "{E_TIME} **The First Supreme Elder, {name}, gazes down from atop Heaven Overseeing Tower.**\n> *'That which is not recorded within fate has no right to exist.'*\n> Channeling the overwhelming power of **Fate Vanquish**, countless dao chains descend, erasing this isolated realm from the river of history entirely. *(Dissipating in 5 seconds...)*",
        "image": "https://i.pinimg.com/736x/36/a1/25/36a12522ec7b926b3a5ea681e3775324.jpg" 
    },

    # armaan - Qi Path
    815099553032044576: {
        "seal": "The Second Supreme Elder, **{name}**, exhales slowly, drawing in heaven, earth, and human qi.\n> The legendary killer move **Triple Qi Retraction** unfolds. As the three qi converge into a single, terrifying singularity, all worldly disturbances are instantly crushed and the connection is sealed.",
        "delete": "{E_TIME} **The Second Supreme Elder, {name}, clasps their hands behind their back as the void trembles.**\n> Heaven qi collapses, earth qi rises, and human qi suffocates. Under the apocalyptic pressure of **Triple Qi Retraction**, this isolated realm is ground down into primordial dust. *(Dissipating in 5 seconds...)*",
        "image": "https://i.pinimg.com/736x/33/60/44/336044294efd5f45403842ae0343dda7.jpg"
    },

    # karma - Wind / Wood Path
    1300911596033282048: {
        "seal": "The Ceremony Elder, **{name}**, gently waves a sleeve, and a sudden breeze scatters countless peach blossoms across the heavens.\n> The immortal battlefield **Peach Blossom Labyrinth** descends. Trapped within an endless, inescapable sea of pink petals, this Heavenly Dao connection slowly drifts into an eternal slumber.",
        "delete": "{E_TIME} **The Ceremony Elder, {name}, gracefully snaps their fan shut.**\n> The endless sea of petals abruptly converges into a ferocious storm. Shredded by the collapsing **Peach Blossom Labyrinth**, the isolated realm is peacefully reduced to nothingness. *(Dissipating in 5 seconds...)*",
        "image": "https://i.pinimg.com/736x/49/4c/72/494c720de1f759165e2c1a6101488653.jpg"
    },

    # kabser - Wisdom Path
    1239587136978550804: {
        "seal": "Sect Elder **{name}** raises a hand, manifesting the vast **Star Constellation Chessboard** in the sky above.\n> Countless stars flicker as endless deductions resolve in a fraction of a breath. Having calculated every variable, a single starlight piece is placed, locking the connection in an inescapable stalemate.",
        "delete": "{E_TIME} **Sect Elder {name} coldly places the final chess piece upon the board.**\n> The heavens serve as the board; all living beings as pieces. With this ultimate move, every timeline sustaining this isolated realm is deduced and eliminated. Checkmate. *(Dissipating in 5 seconds...)*",
        "image": "https://i.pinimg.com/736x/9f/4f/d3/9f4fd3aa0234e6e63ac74be1b0214e00.jpg"
    },

    # ros - Time / Space Path 
    978584340890013748: {
        "seal": "Sect Elder **{name}** gazes into the flowing River of Time.\n> A formless blade flashes without warning. Using the peerless killer move **Time Cutting Edge**, the future possibilities of this inquiry are instantly severed, bringing the deduction to its destined, abrupt halt.",
        "delete": "{E_TIME} **Sect Elder {name} stands silently before the turbulent void.**\n> *'The destination has already been decided.'*\n> Surging with the jade light of **Fixed Immortal Travel**, the spatial boundaries collapse, banishing this entire isolated realm into the chaotic ether. *(Dissipating in 5 seconds...)*",
        "image": "https://i.pinimg.com/736x/4e/7d/52/4e7d5285a8d4de9caac66f7dd7188ea9.jpg"
    }
}

def get_seal_data(user: discord.Member):
    image_url = None
    if user.id in CUSTOM_LORE:
        lore_text = CUSTOM_LORE[user.id]["seal"].format(name=user.display_name)
        image_url = CUSTOM_LORE[user.id].get("image")
    else:
        lore_text = f"The cultivator's connection to the Heavenly Dao has been severed by **{user.display_name}**."
        
    desc = f"{E_LOTUS} {lore_text}\n\n*(The petitioner has been silenced but may still view this realm. Use `/ticket delete` to shatter it completely.)*"
    return desc, image_url

def get_delete_message(user: discord.Member):
    if user.id in CUSTOM_LORE:
        return CUSTOM_LORE[user.id]["delete"].format(name=user.display_name, E_TIME=E_TIME)
    return f"{E_TIME} **{user.display_name} is shattering this isolated realm...**\n> This space will collapse in 5 seconds."


class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Sever Connection", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_removed = False
        
        for target in list(interaction.channel.overwrites.keys()):
            if isinstance(target, discord.Member) and target != interaction.guild.me:
                overwrite = interaction.channel.overwrites[target]
                overwrite.send_messages = False
                await interaction.channel.set_permissions(target, overwrite=overwrite)
                user_removed = True
                
        if user_removed:
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            
            desc, image_url = get_seal_data(interaction.user)
            embed = discord.Embed(
                title="✦ . CONNECTION SEALED . ✦",
                description=desc,
                color=0x6b1614
            )
            
            if image_url:
                embed.set_image(url=image_url)
                
            await interaction.channel.send(embed=embed)
        else:
            await interaction.response.send_message("⚠️ The connection is already sealed. The mortal has already been silenced.", ephemeral=True)


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
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True, manage_channels=True)

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
        desc += f"*(To sever this connection, press the red seal below or use `/ticket close`)*"

        embed = discord.Embed(title="✦ . HEAVENLY DAO DEDUCTION . ✦", description=desc, color=0x6b1614)
        embed.set_footer(text=f"Node: Fang Yuan // Heavenly Court ✦")
        
        await channel.send(content=f"{user.mention} {ping_str}", embed=embed, view=TicketControls())


class TicketCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(TicketPanel())
        self.bot.add_view(TicketControls())

    ticket_group = app_commands.Group(name="ticket", description="Manage Heavenly Dao connections")

    @ticket_group.command(name="close", description="Seal the connection (Mutes the user, keeps channel for reading)")
    async def close_ticket_cmd(self, interaction: discord.Interaction):
        if "inspiration-" not in interaction.channel.name:
            return await interaction.response.send_message("❌ This command can only be used in an Inspiration channel.", ephemeral=True)
        
        user_removed = False
        
        for target in list(interaction.channel.overwrites.keys()):
            if isinstance(target, discord.Member) and target != interaction.guild.me:
                overwrite = interaction.channel.overwrites[target]
                overwrite.send_messages = False
                await interaction.channel.set_permissions(target, overwrite=overwrite)
                user_removed = True
                
        if user_removed:
            desc, image_url = get_seal_data(interaction.user)
            embed = discord.Embed(
                title="✦ . CONNECTION SEALED . ✦",
                description=desc,
                color=0x6b1614
            )
            
            if image_url:
                embed.set_image(url=image_url)
                
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("⚠️ The connection is already sealed. The mortal has already been silenced.", ephemeral=True)

    @ticket_group.command(name="delete", description="Shatter this isolated realm (Deletes the channel entirely)")
    async def delete_ticket_cmd(self, interaction: discord.Interaction):
        if "inspiration-" not in interaction.channel.name:
            return await interaction.response.send_message("❌ This command can only be used in an Inspiration channel.", ephemeral=True)
            
        is_elder = interaction.user.guild_permissions.administrator or any(role.id in ROLES_TO_PING for role in getattr(interaction.user, 'roles', []))
        if not is_elder:
            return await interaction.response.send_message("❌ Only Wisdom Path Elders possess the profound cultivation required to shatter this realm.", ephemeral=True)

        msg = get_delete_message(interaction.user)
        await interaction.response.send_message(msg)
        await asyncio.sleep(5)
        await interaction.channel.delete()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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