import discord
from discord.ext import commands
from discord import app_commands

ROLE_ANNOUNCEMENTS = 1503820853660614678
ROLE_EVENTS = 1503820902687834143
ROLE_GIVEAWAYS = 1503820804230742227
ROLE_QOTD = 1515602867770101882
ROLE_QUOTES = 1515602828733972520       
ROLE_MASS_DROPS = 1509092342295036025
ROLE_SERVER_DROPS = 1474366528836206654

ROLE_NA = 1509110481690951841
ROLE_EU = 1509110588725264404
ROLE_SA = 1509110670019268648
ROLE_OCEANIA = 1509110720644517928
ROLE_EAST_ASIA = 1509110909774200944
ROLE_WEST_ASIA = 1509111137092763758
ROLE_AFRICA = 1509110834121408532

CLAN_MEMBER_ROLE = 1504127544801366128
BOOSTER_ROLE = 1474356762063667210


class NotificationDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Announcements", value=str(ROLE_ANNOUNCEMENTS), emoji="🌟"),
            discord.SelectOption(label="Events", value=str(ROLE_EVENTS), emoji="🎉"),
            discord.SelectOption(label="Giveaways", value=str(ROLE_GIVEAWAYS), emoji="🎁"),
            discord.SelectOption(label="Question of the Day", value=str(ROLE_QOTD), emoji="❔"),
            discord.SelectOption(label="Quotes", value=str(ROLE_QUOTES), emoji="📜"),
            discord.SelectOption(label="Mass Drops (Clan/Booster)", value=str(ROLE_MASS_DROPS), emoji="💧"),
            discord.SelectOption(label="Server Drops (Clan/Booster)", value=str(ROLE_SERVER_DROPS), emoji="🚨")
        ]
        super().__init__(placeholder="choose your notifications", min_values=0, max_values=7, options=options, custom_id="notif_roles_dropdown")

    async def callback(self, interaction: discord.Interaction):
        selected_role_ids = [int(val) for val in self.values]
        all_dropdown_role_ids = [int(opt.value) for opt in self.options]
        
        user_roles = [role.id for role in interaction.user.roles]
        roles_to_add = []
        roles_to_remove = []

        is_exclusive_member = (CLAN_MEMBER_ROLE in user_roles) or (BOOSTER_ROLE in user_roles)
        exclusive_rejection = False

        for role_id in all_dropdown_role_ids:
            role_obj = interaction.guild.get_role(role_id)
            if not role_obj:
                continue
                
            if role_id in selected_role_ids:
                if role_id in [ROLE_MASS_DROPS, ROLE_SERVER_DROPS] and not is_exclusive_member:
                    exclusive_rejection = True
                    continue 
                
                if role_obj not in interaction.user.roles:
                    roles_to_add.append(role_obj)
            else:
                if role_obj in interaction.user.roles:
                    roles_to_remove.append(role_obj)

        if roles_to_add:
            await interaction.user.add_roles(*roles_to_add)
        if roles_to_remove:
            await interaction.user.remove_roles(*roles_to_remove)

        if exclusive_rejection:
            await interaction.response.send_message("✅ Roles updated! *(Note: Mass/Server drops were not added as they are exclusive to Clan Members and Boosters).* ", ephemeral=True)
        else:
            await interaction.response.send_message("✅ Your notification roles have been successfully updated!", ephemeral=True)

class RegionDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="North America", value=str(ROLE_NA), emoji="🇺🇸"),
            discord.SelectOption(label="Europe", value=str(ROLE_EU), emoji="🇪🇺"),
            discord.SelectOption(label="South America", value=str(ROLE_SA), emoji="🇧🇷"),
            discord.SelectOption(label="Oceania", value=str(ROLE_OCEANIA), emoji="🇦🇺"),
            discord.SelectOption(label="East Asia", value=str(ROLE_EAST_ASIA), emoji="🇯🇵"),
            discord.SelectOption(label="West Asia", value=str(ROLE_WEST_ASIA), emoji="🇹🇷"),
            discord.SelectOption(label="Africa", value=str(ROLE_AFRICA), emoji="🇿🇦")
        ]
        super().__init__(placeholder="select your region", min_values=0, max_values=1, options=options, custom_id="region_roles_dropdown")

    async def callback(self, interaction: discord.Interaction):
        selected_role_ids = [int(val) for val in self.values]
        all_dropdown_role_ids = [int(opt.value) for opt in self.options]
        
        roles_to_add = []
        roles_to_remove = []

        for role_id in all_dropdown_role_ids:
            role_obj = interaction.guild.get_role(role_id)
            if not role_obj: continue
                
            if role_id in selected_role_ids:
                if role_obj not in interaction.user.roles:
                    roles_to_add.append(role_obj)
            else:
                if role_obj in interaction.user.roles:
                    roles_to_remove.append(role_obj)

        if roles_to_add:
            await interaction.user.add_roles(*roles_to_add)
        if roles_to_remove:
            await interaction.user.remove_roles(*roles_to_remove)

        await interaction.response.send_message("✅ Your region role has been successfully updated!", ephemeral=True)

class RolesView(discord.ui.View):
    def __init__(self, role_type: str):
        super().__init__(timeout=None)
        if role_type == "notification":
            self.add_item(NotificationDropdown())
        elif role_type == "region":
            self.add_item(RegionDropdown())

class RolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(RolesView("notification"))
        self.bot.add_view(RolesView("region"))

    @app_commands.command(name="setup_roles", description="Deploys the self-role menus to the current channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_roles(self, interaction: discord.Interaction):
        
        notif_desc = (
            "✨ *choose the pings you wish to receive* ✨\n\n"
            "╭━━━━━━━━━━━━━୨୧━━━━━━━━━━━━━╮\n\n"
            "🌟 | Announcements\n"
            "🎉 | Events\n"
            "🎁 | Giveaways\n"
            "❔ | Question of the Day\n"
            "📜 | Quotes\n\n"
            "*exclusive to clan members and boosters:*\n"
            "💧 | Mass Drops\n"
            "🚨 | Server Drops\n\n"
            "╰━━━━━━━━━━━━━୨୧━━━━━━━━━━━━━╯\n\n"
            "✦ select pings from the dropdown below ⬇️"
        )
        notif_embed = discord.Embed(title="📢 NOTIFICATION ROLES 📢", description=notif_desc, color=0x8b0000)

        # --- Region Embed ---
        region_desc = (
            "✨ *which region you reside in* ✨\n\n"
            "╭━━━━━━━━━━━━━୨୧━━━━━━━━━━━━━╮\n\n"
            "🇺🇸 | North America\n"
            "🇪🇺 | Europe\n"
            "🇧🇷 | South America\n"
            "🇦🇺 | Oceania\n"
            "🇯🇵 | East Asia\n"
            "🇹🇷 | West Asia\n"
            "🇿🇦 | Africa\n\n"
            "╰━━━━━━━━━━━━━୨୧━━━━━━━━━━━━━╯\n\n"
            "✦ select your region from the dropdown below ⬇️"
        )
        region_embed = discord.Embed(title="🌍 REGION ROLES 🌍", description=region_desc, color=0x8b0000)

        await interaction.response.send_message("Deploying role menus...", ephemeral=True)
        
        await interaction.channel.send(embed=notif_embed, view=RolesView("notification"))
        await interaction.channel.send("**━━━━━━━━━━━━━━━━━━━━ ✦ ━━━━━━━━━━━━━━━━━━━━**")
        await interaction.channel.send(embed=region_embed, view=RolesView("region"))

async def setup(bot):
    await bot.add_cog(RolesCog(bot))