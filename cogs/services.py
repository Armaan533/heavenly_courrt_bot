import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import traceback
import json
import os
import re

DATA_FILE = "services.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                raw_data = json.load(f)
                return {
                    "dyers": {int(k): v for k, v in raw_data.get("dyers", {}).items()},
                    "frame_testers": {int(k): v for k, v in raw_data.get("frame_testers", {}).items()},
                    "sketchers": {int(k): v for k, v in raw_data.get("sketchers", {}).items()}
                }
        except Exception:
            pass
    return {"dyers": {}, "frame_testers": {}, "sketchers": {}}

def save_data():
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(SERVICE_DB, f, indent=4)
    except Exception:
        pass

SERVICE_DB = load_data()

class FeaturedDyeListener(discord.ui.View):
    def __init__(self, user, bot, channel):
        super().__init__(timeout=300)
        self.user = user
        self.bot = bot
        self.channel = channel
        self.dyes_collected = 0
        self.max_dyes = 4
        self.listening = True

    @discord.ui.button(label="Finish Registration", style=discord.ButtonStyle.success, emoji="✅")
    async def finish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: 
            return await interaction.response.send_message("Not your setup!", ephemeral=True)
        self.listening = False
        for child in self.children: 
            child.disabled = True
        await interaction.response.edit_message(content=f"✅ Registration complete! You saved {self.dyes_collected} featured dyes.", view=self)
        self.stop()

    async def listen_for_dyes(self, message: discord.Message):
        if not self.listening or self.dyes_collected >= self.max_dyes: 
            return

        def check(m):
            return (
                m.channel == self.channel and 
                m.author.bot and "karuta" in m.author.name.lower() and 
                m.embeds and "Dye Details" in str(m.embeds[0].title) and 
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
                save_data()
                
                status_msg = f"✨ Successfully extracted and saved Featured Dye **{self.dyes_collected}/{self.max_dyes}**!"
                if self.dyes_collected >= self.max_dyes:
                    self.listening = False
                    status_msg += "\n\nMaximum dyes reached. Registration complete! ✅"
                    for child in self.children: child.disabled = True
                    await message.edit(view=self)
                else:
                    status_msg += "\nRun another `kv <dye code>` to add more, or click Finish."
                
                await self.channel.send(status_msg)
                if self.listening: 
                    await self.listen_for_dyes(message)
                    
        except asyncio.TimeoutError:
            self.listening = False
            await self.channel.send("⏱️ Dye listening timed out. Registration closed.")

class DyerRegistrationModal(discord.ui.Modal, title="Dye Service Registration"):
    ad_desc = discord.ui.TextInput(label="Service Advertisement", style=discord.TextStyle.paragraph, max_length=1000)
    timezone = discord.ui.TextInput(label="Available Time & Timezone", style=discord.TextStyle.short, max_length=100)
    normal_dyes = discord.ui.TextInput(label="Normal Dyes in Stock", style=discord.TextStyle.short, max_length=10)
    mystic_dyes = discord.ui.TextInput(label="Mystic Dyes in Stock", style=discord.TextStyle.short, max_length=10)
    pricing = discord.ui.TextInput(label="Pricing Options", style=discord.TextStyle.paragraph, placeholder="E.g. Normal: 1 tix, Mystic: 10 tix", max_length=300)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        SERVICE_DB["dyers"][interaction.user.id] = {
            "ad": self.ad_desc.value,
            "timezone": self.timezone.value,
            "normal": self.normal_dyes.value,
            "mystic": self.mystic_dyes.value,
            "pricing": self.pricing.value,
            "featured_dyes": []
        }
        save_data()
        desc = "Your primary information has been recorded!\n\n**Want to add Featured Dyes?**\nType `kv <dye code>` here to automatically add the image to your profile! *(Max 4)*\n*(Click Finish if you are done)*"
        embed = discord.Embed(title="[ DYER PROFILE INITIALIZED ]", description=desc, color=0x6b1614)
        view = FeaturedDyeListener(interaction.user, self.bot, interaction.channel)
        await interaction.response.send_message(embed=embed, view=view)
        self.bot.loop.create_task(view.listen_for_dyes(await interaction.original_response()))

class PortfolioListener(discord.ui.View):
    def __init__(self, user, bot, channel):
        super().__init__(timeout=300)
        self.user = user
        self.bot = bot
        self.channel = channel
        self.images_collected = 0
        self.max_images = 4
        self.listening = True

    @discord.ui.button(label="Finish Registration", style=discord.ButtonStyle.success, emoji="✅")
    async def finish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: 
            return await interaction.response.send_message("Not your setup!", ephemeral=True)
        self.listening = False
        for child in self.children: 
            child.disabled = True
        await interaction.response.edit_message(content=f"✅ Registration complete! You saved {self.images_collected} portfolio images.", view=self)
        self.stop()

    async def listen_for_links(self, message: discord.Message):
        if not self.listening or self.images_collected >= self.max_images: 
            return

        def check(m):
            return m.author == self.user and m.channel == self.channel

        try:
            user_msg = await self.bot.wait_for('message', check=check, timeout=120.0)
            urls = re.findall(r'(https?://[^\s]+)', user_msg.content)
            
            if urls:
                img_url = urls[0]
                if "portfolio" not in SERVICE_DB["sketchers"][self.user.id]:
                    SERVICE_DB["sketchers"][self.user.id]["portfolio"] = []
                    
                SERVICE_DB["sketchers"][self.user.id]["portfolio"].append(img_url)
                self.images_collected += 1
                save_data()
                
                status_msg = f"🖌️ Successfully added image link **{self.images_collected}/{self.max_images}**!"
                if self.images_collected >= self.max_images:
                    self.listening = False
                    status_msg += "\n\nMaximum portfolio slots reached! ✅"
                    for child in self.children: child.disabled = True
                    await message.edit(view=self)
                else:
                    status_msg += "\nPaste another link, or click Finish."
                
                await self.channel.send(status_msg)
            
            if self.listening: 
                await self.listen_for_links(message)
                    
        except asyncio.TimeoutError:
            self.listening = False
            await self.channel.send("⏱️ Listening timed out. Registration closed.")

class SketcherRegistrationModal(discord.ui.Modal, title="Sketcher Registration"):
    ad_desc = discord.ui.TextInput(label="Service Advertisement", style=discord.TextStyle.paragraph, max_length=1000)
    timezone = discord.ui.TextInput(label="Available Time & Timezone", style=discord.TextStyle.short, max_length=100)
    pricing = discord.ui.TextInput(label="Pricing Options", style=discord.TextStyle.paragraph, placeholder="E.g. Full body: 50 tix, Headshot: 20 tix", max_length=300)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        SERVICE_DB["sketchers"][interaction.user.id] = {
            "ad": self.ad_desc.value,
            "timezone": self.timezone.value,
            "pricing": self.pricing.value,
            "portfolio": []
        }
        save_data()
        desc = "Your primary information has been recorded!\n\n**Let's build your Portfolio!**\nPlease paste image links (Imgur, Pinterest, etc.) in this channel one by one. *(Max 4)*\n*(Click Finish if you are done)*"
        embed = discord.Embed(title="[ SKETCHER PROFILE INITIALIZED ]", description=desc, color=0x6b1614)
        view = PortfolioListener(interaction.user, self.bot, interaction.channel)
        await interaction.response.send_message(embed=embed, view=view)
        self.bot.loop.create_task(view.listen_for_links(await interaction.original_response()))

class FrameRegistrationModal(discord.ui.Modal, title="Frame Tester Registration"):
    ad_desc = discord.ui.TextInput(label="Service Advertisement", style=discord.TextStyle.paragraph, placeholder="List the notable frames you own here!", max_length=1000)
    timezone = discord.ui.TextInput(label="Available Time & Timezone", style=discord.TextStyle.short, max_length=100)
    pricing = discord.ui.TextInput(label="Pricing Options", style=discord.TextStyle.paragraph, placeholder="E.g. 1 ticket per 3 frame tests", max_length=300)

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        SERVICE_DB["frame_testers"][interaction.user.id] = {
            "ad": self.ad_desc.value,
            "timezone": self.timezone.value,
            "pricing": self.pricing.value,
        }
        save_data()
        await interaction.response.send_message("✅ **Frame Tester profile successfully registered!**", ephemeral=True)

class ServiceSelectionView(discord.ui.View):
    def __init__(self, user, bot):
        super().__init__(timeout=60)
        self.user = user
        self.bot = bot

    @discord.ui.button(label="Dye Job", style=discord.ButtonStyle.primary, emoji="🧪")
    async def btn_dyer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: 
            return await interaction.response.send_message("Not your menu!", ephemeral=True)
        await interaction.response.send_modal(DyerRegistrationModal(self.bot))
        self.stop()

    @discord.ui.button(label="Frame Tester", style=discord.ButtonStyle.secondary, emoji="🖼️")
    async def btn_framer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: 
            return await interaction.response.send_message("Not your menu!", ephemeral=True)
        await interaction.response.send_modal(FrameRegistrationModal(self.bot))
        self.stop()

    @discord.ui.button(label="Sketcher", style=discord.ButtonStyle.secondary, emoji="🖌️")
    async def btn_sketcher(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: 
            return await interaction.response.send_message("Not your menu!", ephemeral=True)
        await interaction.response.send_modal(SketcherRegistrationModal(self.bot))
        self.stop()

class ProviderView(discord.ui.View):
    def __init__(self, bot, category_name, providers):
        super().__init__(timeout=120)
        self.bot = bot
        self.category_name = category_name
        self.providers = providers
        
        options = []
        for user_id in list(providers.keys())[:25]:
            user = bot.get_user(user_id)
            name = user.display_name if user else f"User {user_id}"
            options.append(discord.SelectOption(label=name[:99], value=str(user_id), emoji="👤"))
            
        self.dropdown = discord.ui.Select(placeholder="Select a service provider...", min_values=1, max_values=1, options=options)
        self.dropdown.callback = self.dropdown_callback
        self.add_item(self.dropdown)

    async def dropdown_callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            user_id = int(self.dropdown.values[0])
            data = SERVICE_DB[self.category_name].get(user_id, {})
            
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
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
            
            main_embed.add_field(name="🕒 Availability", value=f"`{data.get('timezone', 'N/A')}`", inline=False)
            
            if self.category_name == "dyers":
                main_embed.add_field(name="🧪 Normal Dyes", value=f"`{data.get('normal', '0')}`", inline=True)
                main_embed.add_field(name="✨ Mystic Dyes", value=f"`{data.get('mystic', '0')}`", inline=True)
                
            main_embed.add_field(name="💰 Pricing", value=f"```\n{data.get('pricing', 'N/A')}\n```", inline=False)
            
            embeds_to_send = [main_embed]
            
            images = data.get("featured_dyes", []) if self.category_name == "dyers" else data.get("portfolio", [])
            for url in images[:4]:
                img_embed = discord.Embed(url=shared_url, color=0x6b1614)
                img_embed.set_image(url=url)
                embeds_to_send.append(img_embed)
                
            await interaction.followup.edit_message(message_id=interaction.message.id, embeds=embeds_to_send, view=self)
            
        except Exception:
            traceback.print_exc()
            await interaction.followup.send(f"⚠️ Error loading profile.", ephemeral=True)

    @discord.ui.button(label="Back to Categories", style=discord.ButtonStyle.danger, emoji="🔙", row=2)
    async def back_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="[ HEAVENLY COURT SERVICES ]",
            description="Welcome to the Service Directory! Please select a category below to browse our providers.",
            color=0x6b1614
        )
        await interaction.response.edit_message(embed=embed, view=CategoryView(self.bot))

class CategoryView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=120)
        self.bot = bot
        
        options = [
            discord.SelectOption(label="Dye Jobs", value="dyers", emoji="🧪", description="Find people to dye your cards"),
            discord.SelectOption(label="Frame Testers", value="frame_testers", emoji="🖼️", description="Find people to test frames"),
            discord.SelectOption(label="Sketchers", value="sketchers", emoji="🖌️", description="Find sketch artists")
        ]
        self.select = discord.ui.Select(placeholder="Select a service category...", min_values=1, max_values=1, options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        try:
            category = self.select.values[0]
            providers = SERVICE_DB.get(category, {})
            
            if not providers:
                embed = discord.Embed(
                    title="[ NO PROVIDERS FOUND ]",
                    description=f"There are currently no active providers in this category.\nWant to be the first? Use `/services add`!",
                    color=0x2b2d31
                )
                return await interaction.response.edit_message(embed=embed, view=self)
                
            desc = "Select a provider from the dropdown below to view their profile and pricing!\n\n**Available Providers:**\n"
            for user_id in providers:
                user = self.bot.get_user(user_id)
                name = user.display_name if user else f"User {user_id}"
                desc += f"• **{name}**\n"
                
            embed = discord.Embed(
                title=f"[ {category.replace('_', ' ').upper()} DIRECTORY ]",
                description=desc,
                color=0x6b1614
            )
            
            await interaction.response.edit_message(embed=embed, view=ProviderView(self.bot, category, providers))
            
        except Exception as e:
            traceback.print_exc()
            if not interaction.response.is_done():
                await interaction.response.send_message(f"⚠️ Failed to load category: {e}", ephemeral=True)

class ServicesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    services = app_commands.Group(name="services", description="Service directory management")

    @services.command(name="add", description="Register as a service provider")
    async def service_add(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="[ SERVICE REGISTRATION ]",
            description="What kind of service are you providing to the Heavenly Court?\n*(Select an option below to open your registration form)*",
            color=0x6b1614
        )
        await interaction.response.send_message(embed=embed, view=ServiceSelectionView(interaction.user, self.bot))

    @services.command(name="list", description="Browse active service providers")
    async def service_list(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="[ HEAVENLY COURT SERVICES ]",
            description="Welcome to the Service Directory! Please select a category below to browse our providers.",
            color=0x6b1614
        )
        await interaction.response.send_message(embed=embed, view=CategoryView(self.bot))

    @services.command(name="delete", description="Delete your registered service profile")
    async def service_delete(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        removed = False
        for cat in ["dyers", "frame_testers", "sketchers"]:
            if user_id in SERVICE_DB[cat]:
                del SERVICE_DB[cat][user_id]
                removed = True
        if removed:
            save_data()
            await interaction.response.send_message("✅ Your service profile has been deleted.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ You do not have a registered profile.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ServicesCog(bot))