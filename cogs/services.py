import discord
from discord.ext import commands
import asyncio
import traceback

SERVICE_DB = {
    "dyers": {},
    "frame_testers": {},
    "sketchers": {}
}

class FeaturedDyeListener(discord.ui.View):
    def __init__(self, user, bot, ctx):
        super().__init__(timeout=300)
        self.user = user
        self.bot = bot
        self.ctx = ctx
        self.dyes_collected = 0
        self.max_dyes = 4
        self.listening = True

    @discord.ui.button(label="Finish Registration", style=discord.ButtonStyle.success, emoji="✅")
    async def finish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            return await interaction.response.send_message("This isn't your setup!", ephemeral=True)
        
        self.listening = False
        button.disabled = True
        await interaction.response.edit_message(content=f"✅ Registration complete! You have saved {self.dyes_collected} featured dyes.", view=self)
        self.stop()

    async def listen_for_dyes(self, message: discord.Message):
        if not self.listening or self.dyes_collected >= self.max_dyes:
            return

        def check(m):
            return (
                m.channel == self.ctx.channel and 
                m.author.bot and "karuta" in m.author.name.lower() and 
                m.embeds and 
                "Dye Details" in str(m.embeds[0].title) and 
                str(self.user.id) in str(m.embeds[0].description)
            )

        try:
            karuta_msg = await self.bot.wait_for('message', check=check, timeout=120.0)
            
            embed = karuta_msg.embeds[0]
            if embed.thumbnail and embed.thumbnail.url:
                dye_url = embed.thumbnail.url
                
                if "featured_dyes" not in SERVICE_DB["dyers"][self.user.id]:
                    SERVICE_DB["dyers"][self.user.id]["featured_dyes"] = []
                    
                SERVICE_DB["dyers"][self.user.id]["featured_dyes"].append(dye_url)
                self.dyes_collected += 1
                
                status_msg = f"✨ Successfully extracted and saved Featured Dye **{self.dyes_collected}/{self.max_dyes}**!"
                if self.dyes_collected >= self.max_dyes:
                    self.listening = False
                    status_msg += "\n\nMaximum dyes reached. Registration complete! ✅"
                    for child in self.children:
                        child.disabled = True
                    await message.edit(view=self)
                else:
                    status_msg += "\nRun another `kv <dye code>` to add more, or click Finish."
                
                await self.ctx.send(status_msg)

                if self.listening:
                    await self.listen_for_dyes(message)
                    
        except asyncio.TimeoutError:
            self.listening = False
            await self.ctx.send("⏱️ Dye listening timed out. Registration closed.")


class DyerRegistrationModal(discord.ui.Modal, title="Dye Service Registration"):
    ad_desc = discord.ui.TextInput(
        label="Service Advertisement",
        style=discord.TextStyle.paragraph,
        placeholder="E.g. Fast & reliable dyeing! Bulk discounts available...",
        required=True,
        max_length=1000
    )
    
    timezone = discord.ui.TextInput(
        label="Available Time & Timezone",
        style=discord.TextStyle.short,
        placeholder="E.g. 5PM - 11PM EST",
        required=True,
        max_length=100
    )
    
    normal_dyes = discord.ui.TextInput(
        label="Normal Dyes in Stock",
        style=discord.TextStyle.short,
        placeholder="E.g. 40",
        required=True,
        max_length=10
    )
    
    mystic_dyes = discord.ui.TextInput(
        label="Mystic Dyes in Stock",
        style=discord.TextStyle.short,
        placeholder="E.g. 12",
        required=True,
        max_length=10
    )

    def __init__(self, ctx, bot):
        super().__init__()
        self.ctx = ctx
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        SERVICE_DB["dyers"][interaction.user.id] = {
            "ad": self.ad_desc.value,
            "timezone": self.timezone.value,
            "normal": self.normal_dyes.value,
            "mystic": self.mystic_dyes.value,
            "featured_dyes": []
        }

        desc = "Your primary information has been recorded!\n\n"
        desc += "**Would you like to add Featured Dyes?**\n"
        desc += "Please type `kv <dye code>` in this channel. I will automatically read Karuta's embed and save the dye image to your profile! *(Max: 4)*\n\n"
        desc += "*(Click Finish if you are done or don't want to feature dyes right now)*"

        embed = discord.Embed(title="[ DYER PROFILE INITIALIZED ]", description=desc, color=0x6b1614)
        view = FeaturedDyeListener(interaction.user, self.bot, self.ctx)
        await interaction.response.send_message(embed=embed, view=view)
        
        self.bot.loop.create_task(view.listen_for_dyes(await interaction.original_response()))


class ServiceSelectionView(discord.ui.View):
    def __init__(self, ctx, bot):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.bot = bot

    @discord.ui.button(label="Dye Job", style=discord.ButtonStyle.primary, emoji="🧪")
    async def btn_dyer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author: return await interaction.response.send_message("Not your menu!", ephemeral=True)
        await interaction.response.send_modal(DyerRegistrationModal(self.ctx, self.bot))
        self.stop()

    @discord.ui.button(label="Frame Tester", style=discord.ButtonStyle.secondary, emoji="🖼️")
    async def btn_framer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author: return await interaction.response.send_message("Not your menu!", ephemeral=True)
        await interaction.response.send_message("Frame Tester registration is currently under construction! 🚧", ephemeral=True)

    @discord.ui.button(label="Sketcher", style=discord.ButtonStyle.secondary, emoji="🖌️")
    async def btn_sketcher(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author: return await interaction.response.send_message("Not your menu!", ephemeral=True)
        await interaction.response.send_message("Sketcher registration is currently under construction! 🚧", ephemeral=True)



class ProviderDropdown(discord.ui.Select):
    def __init__(self, category_name, providers, bot):
        self.bot = bot
        self.category_name = category_name
        options = []
        for user_id, data in providers.items():
            user = bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            options.append(discord.SelectOption(label=name[:99], value=str(user_id), emoji="👤"))
        
        super().__init__(placeholder="Select a service provider...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            
            user_id = int(self.values[0])
            data = SERVICE_DB[self.category_name].get(user_id, {})
            
            user = self.bot.get_user(user_id)
            if not user:
                try:
                    user = await self.bot.fetch_user(user_id)
                except:
                    user = None
                    
            display_name = user.display_name if user else f"User {user_id}"
            
            shared_url = "https://discord.com" 
            
            main_embed = discord.Embed(
                title=f"Service Provider: {display_name}",
                url=shared_url,
                description=data.get("ad", "No advertisement provided."),
                color=0x6b1614
            )
            
            if user and user.display_avatar:
                main_embed.set_thumbnail(url=user.display_avatar.url)
            
            if self.category_name == "dyers":
                main_embed.add_field(name="🕒 Availability", value=f"`{data.get('timezone', 'N/A')}`", inline=False)
                main_embed.add_field(name="🧪 Normal Dyes", value=f"`{data.get('normal', '0')}`", inline=True)
                main_embed.add_field(name="✨ Mystic Dyes", value=f"`{data.get('mystic', '0')}`", inline=True)
            
            embeds_to_send = [main_embed]
            
            featured_dyes = data.get("featured_dyes", [])
            for url in featured_dyes:
                dye_embed = discord.Embed(url=shared_url, color=0x6b1614)
                dye_embed.set_image(url=url)
                embeds_to_send.append(dye_embed)
                
            await interaction.followup.edit_message(message_id=interaction.message.id, embeds=embeds_to_send, view=self.view)
            
        except Exception as e:
            print(f"Error in ProviderDropdown: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"⚠️ An error occurred while loading this profile.", ephemeral=True)


class CategorySelect(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        options = [
            discord.SelectOption(label="Dye Jobs", value="dyers", emoji="🧪", description="Find people to dye your cards"),
            discord.SelectOption(label="Frame Testers", value="frame_testers", emoji="🖼️", description="Find people to test frames"),
            discord.SelectOption(label="Sketchers", value="sketchers", emoji="🖌️", description="Find sketch artists")
        ]
        super().__init__(placeholder="Select a service category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        try:
            category = self.values[0]
            providers = SERVICE_DB.get(category, {})
            
            new_view = discord.ui.View(timeout=120)
            new_view.add_item(CategorySelect(self.bot))
            
            if not providers:
                embed = discord.Embed(
                    title="[ NO PROVIDERS FOUND ]",
                    description=f"There are currently no active providers in this category.\nWant to be the first? Use `,service add`!",
                    color=0x2b2d31
                )
                return await interaction.response.edit_message(embed=embed, view=new_view)
                
            embed = discord.Embed(
                title="[ SERVICE DIRECTORY ]",
                description="Select a provider from the dropdown below to view their advertisement, stock, and featured work!",
                color=0x6b1614
            )
            
            new_view.add_item(ProviderDropdown(category, providers, self.bot))
            await interaction.response.edit_message(embed=embed, view=new_view)
            
        except Exception as e:
            print(f"Error in CategorySelect: {e}")
            traceback.print_exc()
            if not interaction.response.is_done():
                await interaction.response.send_message(f"⚠️ Failed to load category: {e}", ephemeral=True)


class ServiceListView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=120)
        self.bot = bot
        self.add_item(CategorySelect(bot))


class ServicesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True, aliases=["service"])
    async def services(self, ctx):
        await ctx.send("Use `,service add` to register as a provider, or `,service list` to view them!")

    @services.command(name="add")
    async def service_add(self, ctx):
        embed = discord.Embed(
            title="[ SERVICE REGISTRATION ]",
            description="What kind of service are you providing to the Heavenly Court?\n*(Select an option below to open your registration form)*",
            color=0x6b1614
        )
        await ctx.send(embed=embed, view=ServiceSelectionView(ctx, self.bot))

    @services.command(name="list")
    async def service_list(self, ctx):
        embed = discord.Embed(
            title="[ HEAVENLY COURT SERVICES ]",
            description="Welcome to the Service Directory! Please select a category below to browse our providers.",
            color=0x6b1614
        )
        await ctx.send(embed=embed, view=ServiceListView(self.bot))


async def setup(bot):
    await bot.add_cog(ServicesCog(bot))