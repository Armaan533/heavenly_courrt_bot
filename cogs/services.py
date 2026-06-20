import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import traceback
import json
import os
import re
import math

DATA_FILE = "services.json"
PLACEHOLDER_IMG = "https://singlecolorimage.com/get/2b2d31/400x400"
SERVICE_ROLE_ID = 1517559992163631185

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
    def __init__(self, user, bot, channel, starting_count=0):
        super().__init__(timeout=300)
        self.user = user
        self.bot = bot
        self.channel = channel
        self.dyes_collected = starting_count
        self.max_dyes = 12
        self.listening = True

    @discord.ui.button(label="Finish Registration", style=discord.ButtonStyle.success, emoji="✅")
    async def finish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: 
            return await interaction.response.send_message("Not your setup!", ephemeral=True)
        self.listening = False
        for child in self.children: 
            child.disabled = True
        await interaction.response.edit_message(content=f"<:eight_side_sparkle:1516681364806570105> Gallery saved! You now have {self.dyes_collected} featured dyes.", view=self)
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
                
                status_msg = f"<:eight_side_sparkle:1516681364806570105> Successfully extracted and saved Featured Dye **{self.dyes_collected}/{self.max_dyes}**!"
                if self.dyes_collected >= self.max_dyes:
                    self.listening = False
                    status_msg += "\n\nMaximum dyes reached. Gallery complete! ✅"
                    for child in self.children: child.disabled = True
                    await message.edit(view=self)
                else:
                    status_msg += "\nRun another `kv <dye code>` to add more, or click Finish."
                
                await self.channel.send(status_msg)
                if self.listening: 
                    await self.listen_for_dyes(message)
                    
        except asyncio.TimeoutError:
            self.listening = False
            await self.channel.send("⏱️ Dye listening timed out. Process closed.")

class DyerRegistrationModal(discord.ui.Modal, title="Dye Service Registration"):
    def __init__(self, bot, existing_data=None):
        super().__init__()
        self.bot = bot
        self.is_update = bool(existing_data)
        
        self.ad_desc = discord.ui.TextInput(label="Service Advertisement", style=discord.TextStyle.paragraph, max_length=1000, default=existing_data.get("ad") if existing_data else None)
        self.timezone = discord.ui.TextInput(label="Available Time & Timezone", style=discord.TextStyle.short, max_length=100, default=existing_data.get("timezone") if existing_data else None)
        self.normal_dyes = discord.ui.TextInput(label="Normal Dyes in Stock", style=discord.TextStyle.short, max_length=10, default=existing_data.get("normal") if existing_data else None)
        self.mystic_dyes = discord.ui.TextInput(label="Mystic Dyes in Stock", style=discord.TextStyle.short, max_length=10, default=existing_data.get("mystic") if existing_data else None)
        self.pricing = discord.ui.TextInput(label="Pricing Options", style=discord.TextStyle.paragraph, placeholder="E.g. Normal: 1 tix, Mystic: 10 tix", max_length=300, default=existing_data.get("pricing") if existing_data else None)

        self.add_item(self.ad_desc)
        self.add_item(self.timezone)
        self.add_item(self.normal_dyes)
        self.add_item(self.mystic_dyes)
        self.add_item(self.pricing)

    async def on_submit(self, interaction: discord.Interaction):
        if self.is_update:
            SERVICE_DB["dyers"][interaction.user.id].update({
                "ad": self.ad_desc.value,
                "timezone": self.timezone.value,
                "normal": self.normal_dyes.value,
                "mystic": self.mystic_dyes.value,
                "pricing": self.pricing.value
            })
            save_data()
            await interaction.response.send_message("<:emoji_for_oddny:1517225564023554219> Profile text successfully updated!", ephemeral=True)
        else:
            SERVICE_DB["dyers"][interaction.user.id] = {
                "ad": self.ad_desc.value,
                "timezone": self.timezone.value,
                "normal": self.normal_dyes.value,
                "mystic": self.mystic_dyes.value,
                "pricing": self.pricing.value,
                "featured_dyes": []
            }
            save_data()
            desc = "Your primary information has been recorded!\n\n**Want to add Featured Dyes?**\nType `kv <dye code>` here to automatically add the image to your profile! *(Max 12)*\n*(Click Finish if you are done)*"
            embed = discord.Embed(title="<:eight_side_sparkle:1516681364806570105> [ DYER PROFILE INITIALIZED ] <:eight_side_sparkle:1516681364806570105>", description=desc, color=0x6b1614)
            view = FeaturedDyeListener(interaction.user, self.bot, interaction.channel)
            await interaction.response.send_message(embed=embed, view=view)
            self.bot.loop.create_task(view.listen_for_dyes(await interaction.original_response()))

class PortfolioListener(discord.ui.View):
    def __init__(self, user, bot, channel, starting_count=0):
        super().__init__(timeout=300)
        self.user = user
        self.bot = bot
        self.channel = channel
        self.images_collected = starting_count
        self.max_images = 12
        self.listening = True

    @discord.ui.button(label="Finish Registration", style=discord.ButtonStyle.success, emoji="✅")
    async def finish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: 
            return await interaction.response.send_message("Not your setup!", ephemeral=True)
        self.listening = False
        for child in self.children: 
            child.disabled = True
        await interaction.response.edit_message(content=f"<:book_ig:1516683126066253844> Gallery saved! You now have {self.images_collected} portfolio images.", view=self)
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
                
                status_msg = f"<:book_ig:1516683126066253844> Successfully added image link **{self.images_collected}/{self.max_images}**!"
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
            await self.channel.send("⏱️ Listening timed out. Process closed.")

class SketcherRegistrationModal(discord.ui.Modal, title="Sketcher Registration"):
    def __init__(self, bot, existing_data=None):
        super().__init__()
        self.bot = bot
        self.is_update = bool(existing_data)
        
        self.ad_desc = discord.ui.TextInput(label="Service Advertisement", style=discord.TextStyle.paragraph, max_length=1000, default=existing_data.get("ad") if existing_data else None)
        self.timezone = discord.ui.TextInput(label="Available Time & Timezone", style=discord.TextStyle.short, max_length=100, default=existing_data.get("timezone") if existing_data else None)
        self.pricing = discord.ui.TextInput(label="Pricing Options", style=discord.TextStyle.paragraph, placeholder="E.g. Full body: 50 tix", max_length=300, default=existing_data.get("pricing") if existing_data else None)

        self.add_item(self.ad_desc)
        self.add_item(self.timezone)
        self.add_item(self.pricing)

    async def on_submit(self, interaction: discord.Interaction):
        if self.is_update:
            SERVICE_DB["sketchers"][interaction.user.id].update({
                "ad": self.ad_desc.value,
                "timezone": self.timezone.value,
                "pricing": self.pricing.value
            })
            save_data()
            await interaction.response.send_message("<:emoji_for_oddny:1517225564023554219> Profile text successfully updated!", ephemeral=True)
        else:
            SERVICE_DB["sketchers"][interaction.user.id] = {
                "ad": self.ad_desc.value,
                "timezone": self.timezone.value,
                "pricing": self.pricing.value,
                "portfolio": []
            }
            save_data()
            desc = "Your primary information has been recorded!\n\n**Let's build your Portfolio!**\nPlease paste image links (Imgur, Pinterest, etc.) in this channel one by one. *(Max 12)*\n*(Click Finish if you are done)*"
            embed = discord.Embed(title="<:book_ig:1516683126066253844> [ SKETCHER PROFILE INITIALIZED ] <:book_ig:1516683126066253844>", description=desc, color=0x6b1614)
            view = PortfolioListener(interaction.user, self.bot, interaction.channel)
            await interaction.response.send_message(embed=embed, view=view)
            self.bot.loop.create_task(view.listen_for_links(await interaction.original_response()))

class FrameRegistrationModal(discord.ui.Modal, title="Frame Tester Registration"):
    def __init__(self, bot, existing_data=None):
        super().__init__()
        self.bot = bot
        self.is_update = bool(existing_data)
        
        self.ad_desc = discord.ui.TextInput(label="Service Advertisement", style=discord.TextStyle.paragraph, max_length=1000, default=existing_data.get("ad") if existing_data else None)
        self.timezone = discord.ui.TextInput(label="Available Time & Timezone", style=discord.TextStyle.short, max_length=100, default=existing_data.get("timezone") if existing_data else None)
        self.pricing = discord.ui.TextInput(label="Pricing Options", style=discord.TextStyle.paragraph, max_length=300, default=existing_data.get("pricing") if existing_data else None)

        self.add_item(self.ad_desc)
        self.add_item(self.timezone)
        self.add_item(self.pricing)

    async def on_submit(self, interaction: discord.Interaction):
        SERVICE_DB["frame_testers"][interaction.user.id] = {
            "ad": self.ad_desc.value,
            "timezone": self.timezone.value,
            "pricing": self.pricing.value,
        }
        save_data()
        await interaction.response.send_message("<:emoji_for_oddny:1517225564023554219> **Frame Tester profile successfully registered/updated!**", ephemeral=True)

class ServiceUpdateActionView(discord.ui.View):
    def __init__(self, user, bot, category):
        super().__init__(timeout=120)
        self.user = user
        self.bot = bot
        self.category = category

    @discord.ui.button(label="Edit Text & Info", style=discord.ButtonStyle.primary, emoji="📝")
    async def edit_text_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: 
            return await interaction.response.send_message("Not your menu!", ephemeral=True)
        
        data = SERVICE_DB[self.category].get(interaction.user.id, {})
        
        if self.category == "dyers":
            await interaction.response.send_modal(DyerRegistrationModal(self.bot, existing_data=data))
        elif self.category == "frame_testers":
            await interaction.response.send_modal(FrameRegistrationModal(self.bot, existing_data=data))
        elif self.category == "sketchers":
            await interaction.response.send_modal(SketcherRegistrationModal(self.bot, existing_data=data))
            
        self.stop()

    @discord.ui.button(label="Add Images", style=discord.ButtonStyle.secondary, emoji="🖼️")
    async def add_images_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: 
            return await interaction.response.send_message("Not your menu!", ephemeral=True)
            
        if self.category == "frame_testers":
            return await interaction.response.send_message("Frame Testers do not use image galleries!", ephemeral=True)
            
        if self.category == "dyers":
            current_count = len(SERVICE_DB["dyers"][interaction.user.id].get("featured_dyes", []))
            if current_count >= 12:
                return await interaction.response.send_message("❌ Your gallery is full (12/12)! Clear it first.", ephemeral=True)
                
            desc = f"**Let's add more Featured Dyes!**\nYou currently have {current_count}/12 slots filled.\nType `kv <dye code>` here to add more to your profile!\n*(Click Finish if you are done)*"
            embed = discord.Embed(title="<:eight_side_sparkle:1516681364806570105> [ UPDATING DYE GALLERY ] <:eight_side_sparkle:1516681364806570105>", description=desc, color=0x6b1614)
            view = FeaturedDyeListener(interaction.user, self.bot, interaction.channel, starting_count=current_count)
            await interaction.response.edit_message(embed=embed, view=view)
            self.bot.loop.create_task(view.listen_for_dyes(interaction.message))
            
        elif self.category == "sketchers":
            current_count = len(SERVICE_DB["sketchers"][interaction.user.id].get("portfolio", []))
            if current_count >= 12:
                return await interaction.response.send_message("❌ Your portfolio is full (12/12)! Clear it first.", ephemeral=True)
                
            desc = f"**Let's add more Portfolio Images!**\nYou currently have {current_count}/12 slots filled.\nPlease paste image links in this channel one by one.\n*(Click Finish if you are done)*"
            embed = discord.Embed(title="<:book_ig:1516683126066253844> [ UPDATING SKETCH GALLERY ] <:book_ig:1516683126066253844>", description=desc, color=0x6b1614)
            view = PortfolioListener(interaction.user, self.bot, interaction.channel, starting_count=current_count)
            await interaction.response.edit_message(embed=embed, view=view)
            self.bot.loop.create_task(view.listen_for_links(interaction.message))
            
        self.stop()
        
    @discord.ui.button(label="Clear Gallery", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def clear_gallery_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: 
            return await interaction.response.send_message("Not your menu!", ephemeral=True)
            
        if self.category == "frame_testers":
            return await interaction.response.send_message("Frame Testers do not use image galleries!", ephemeral=True)
            
        if self.category == "dyers":
            SERVICE_DB["dyers"][interaction.user.id]["featured_dyes"] = []
        elif self.category == "sketchers":
            SERVICE_DB["sketchers"][interaction.user.id]["portfolio"] = []
            
        save_data()
        await interaction.response.edit_message(content="🗑️ **Your image gallery has been successfully cleared!**", embed=None, view=None)
        self.stop()

class ServiceUpdateSelectionView(discord.ui.View):
    def __init__(self, user, bot):
        super().__init__(timeout=60)
        self.user = user
        self.bot = bot

    @discord.ui.button(label="Dye Job", style=discord.ButtonStyle.primary, emoji="🧪")
    async def btn_dyer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: 
            return await interaction.response.send_message("Not your menu!", ephemeral=True)
        if interaction.user.id not in SERVICE_DB["dyers"]:
            return await interaction.response.send_message("❌ You are not registered as a Dyer!", ephemeral=True)
            
        embed = discord.Embed(title="<:emoji_for_oddny:1517225564023554219> [ UPDATE DYE PROFILE ]", description="What would you like to update?", color=0x6b1614)
        await interaction.response.edit_message(embed=embed, view=ServiceUpdateActionView(self.user, self.bot, "dyers"))

    @discord.ui.button(label="Frame Tester", style=discord.ButtonStyle.secondary, emoji="🖼️")
    async def btn_framer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: 
            return await interaction.response.send_message("Not your menu!", ephemeral=True)
        if interaction.user.id not in SERVICE_DB["frame_testers"]:
            return await interaction.response.send_message("❌ You are not registered as a Frame Tester!", ephemeral=True)
            
        embed = discord.Embed(title="<:emoji_for_oddny:1517225564023554219> [ UPDATE FRAME PROFILE ]", description="What would you like to update?", color=0x6b1614)
        await interaction.response.edit_message(embed=embed, view=ServiceUpdateActionView(self.user, self.bot, "frame_testers"))

    @discord.ui.button(label="Sketcher", style=discord.ButtonStyle.secondary, emoji="🖌️")
    async def btn_sketcher(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user: 
            return await interaction.response.send_message("Not your menu!", ephemeral=True)
        if interaction.user.id not in SERVICE_DB["sketchers"]:
            return await interaction.response.send_message("❌ You are not registered as a Sketcher!", ephemeral=True)
            
        embed = discord.Embed(title="<:emoji_for_oddny:1517225564023554219> [ UPDATE SKETCHER PROFILE ]", description="What would you like to update?", color=0x6b1614)
        await interaction.response.edit_message(embed=embed, view=ServiceUpdateActionView(self.user, self.bot, "sketchers"))

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

class ProviderProfileView(discord.ui.View):
    def __init__(self, bot, category_name, providers, user_id, page=0):
        super().__init__(timeout=120)
        self.bot = bot
        self.category_name = category_name
        self.providers = providers
        self.user_id = user_id
        self.page = page
        
        data = SERVICE_DB[category_name].get(user_id, {})
        self.images = data.get("featured_dyes", []) if category_name == "dyers" else data.get("portfolio", [])
        self.max_pages = max(1, math.ceil(len(self.images) / 4))
        
        if self.max_pages > 1:
            prev_btn = discord.ui.Button(label="Prev", style=discord.ButtonStyle.secondary, disabled=(self.page == 0), emoji="⬅️")
            prev_btn.callback = self.prev_page
            self.add_item(prev_btn)
            
            next_btn = discord.ui.Button(label="Next", style=discord.ButtonStyle.secondary, disabled=(self.page >= self.max_pages - 1), emoji="➡️")
            next_btn.callback = self.next_page
            self.add_item(next_btn)
            
        back_btn = discord.ui.Button(label="Back to Providers", style=discord.ButtonStyle.danger, emoji="🔙", row=1)
        back_btn.callback = self.go_back
        self.add_item(back_btn)

    async def get_embeds(self):
        data = SERVICE_DB[self.category_name].get(self.user_id, {})
        user = self.bot.get_user(self.user_id) or await self.bot.fetch_user(self.user_id)
        display_name = user.display_name if user else f"User {self.user_id}"
        shared_url = "https://discord.com" 
        
        main_embed = discord.Embed(
            title=f"<:red_lotus:1516679367743377448> Service Provider: {display_name}",
            url=shared_url,
            description=data.get("ad", "No advertisement provided."),
            color=0x6b1614
        )
        if user and user.display_avatar:
            main_embed.set_thumbnail(url=user.display_avatar.url)
        
        main_embed.add_field(name="<:for_john:1517226175901208696> Availability", value=f"`{data.get('timezone', 'N/A')}`", inline=False)
        
        if self.category_name == "dyers":
            main_embed.add_field(name="<:for_booster:1517226639438778503> Normal Dyes", value=f"`{data.get('normal', '0')}`", inline=True)
            main_embed.add_field(name="<:eight_side_sparkle:1516681364806570105> Mystic Dyes", value=f"`{data.get('mystic', '0')}`", inline=True)
            
        main_embed.add_field(name="<:two_flowers:1516684386546880614> Pricing", value=f"```\n{data.get('pricing', 'N/A')}\n```", inline=False)
        
        if self.max_pages > 1:
            main_embed.set_footer(text=f"Gallery Page {self.page + 1} of {self.max_pages}")
            
        embeds_to_send = [main_embed]
        
        start_idx = self.page * 4
        chunk = self.images[start_idx : start_idx + 4]
        
        if len(chunk) > 0 and len(chunk) < 4:
            while len(chunk) < 4:
                chunk.append(PLACEHOLDER_IMG)
        
        for url in chunk:
            img_embed = discord.Embed(url=shared_url, color=0x6b1614)
            img_embed.set_image(url=url)
            embeds_to_send.append(img_embed)
            
        return embeds_to_send

    async def prev_page(self, interaction: discord.Interaction):
        self.page -= 1
        new_view = ProviderProfileView(self.bot, self.category_name, self.providers, self.user_id, self.page)
        embeds = await new_view.get_embeds()
        await interaction.response.edit_message(embeds=embeds, view=new_view)

    async def next_page(self, interaction: discord.Interaction):
        self.page += 1
        new_view = ProviderProfileView(self.bot, self.category_name, self.providers, self.user_id, self.page)
        embeds = await new_view.get_embeds()
        await interaction.response.edit_message(embeds=embeds, view=new_view)

    async def go_back(self, interaction: discord.Interaction):
        desc = "Select a provider from the dropdown below to view their profile and pricing!\n\n**<:eight_side_sparkle:1516681364806570105> Available Providers:**\n"
        for uid in self.providers:
            u = self.bot.get_user(uid)
            n = u.display_name if u else f"User {uid}"
            desc += f"• **{n}**\n"
            
        embed = discord.Embed(
            title=f"<:two_flowers:1516684386546880614> [ {self.category_name.replace('_', ' ').upper()} DIRECTORY ] <:two_flowers:1516684386546880614>",
            description=desc,
            color=0x6b1614
        )
        await interaction.response.edit_message(embed=embed, view=ProviderSelectionView(self.bot, self.category_name, self.providers))

class ProviderSelectionView(discord.ui.View):
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
        
        back_btn = discord.ui.Button(label="Back to Categories", style=discord.ButtonStyle.danger, emoji="🔙", row=2)
        back_btn.callback = self.back_btn
        self.add_item(back_btn)

    async def dropdown_callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            user_id = int(self.dropdown.values[0])
            
            profile_view = ProviderProfileView(self.bot, self.category_name, self.providers, user_id)
            embeds = await profile_view.get_embeds()
            
            await interaction.followup.edit_message(message_id=interaction.message.id, embeds=embeds, view=profile_view)
            
        except Exception:
            traceback.print_exc()
            await interaction.followup.send(f"⚠️ Error loading profile.", ephemeral=True)

    async def back_btn(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="<:red_lotus:1516679367743377448> [ HEAVENLY COURT SERVICES ] <:red_lotus:1516679367743377448>",
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
                    title="<:eight_side_sparkle:1516681364806570105> [ NO PROVIDERS FOUND ] <:eight_side_sparkle:1516681364806570105>",
                    description=f"There are currently no active providers in this category.\nWant to be the first? Use `/services add`!",
                    color=0x2b2d31
                )
                new_view = discord.ui.View(timeout=120)
                new_view.add_item(CategoryView(self.bot).select)
                return await interaction.response.edit_message(embed=embed, view=new_view)
                
            desc = "Select a provider from the dropdown below to view their profile and pricing!\n\n**<:eight_side_sparkle:1516681364806570105> Available Providers:**\n"
            for user_id in providers:
                user = self.bot.get_user(user_id)
                name = user.display_name if user else f"User {user_id}"
                desc += f"• **{name}**\n"
                
            embed = discord.Embed(
                title=f"<:two_flowers:1516684386546880614> [ {category.replace('_', ' ').upper()} DIRECTORY ] <:two_flowers:1516684386546880614>",
                description=desc,
                color=0x6b1614
            )
            
            await interaction.response.edit_message(embed=embed, view=ProviderSelectionView(self.bot, category, providers))
            
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
        role = discord.utils.get(interaction.user.roles, id=SERVICE_ROLE_ID)
        if not role:
            return await interaction.response.send_message("❌ You need the **service_access** role to register a profile!", ephemeral=True)

        embed = discord.Embed(
            title="<:emoji_for_oddny:1517225564023554219> [ SERVICE REGISTRATION ] <:emoji_for_oddny:1517225564023554219>",
            description="What kind of service are you providing to the Heavenly Court?\n*(Select an option below to open your registration form)*",
            color=0x6b1614
        )
        await interaction.response.send_message(embed=embed, view=ServiceSelectionView(interaction.user, self.bot))

    @services.command(name="list", description="Browse active service providers")
    async def service_list(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="<:red_lotus:1516679367743377448> [ HEAVENLY COURT SERVICES ] <:red_lotus:1516679367743377448>",
            description="Welcome to the Service Directory! Please select a category below to browse our providers.",
            color=0x6b1614
        )
        await interaction.response.send_message(embed=embed, view=CategoryView(self.bot))

    @services.command(name="update", description="Update your registered service profile")
    async def service_update(self, interaction: discord.Interaction):
        role = discord.utils.get(interaction.user.roles, id=SERVICE_ROLE_ID)
        if not role:
            return await interaction.response.send_message("❌ You need the **service_access** role to update a profile!", ephemeral=True)

        embed = discord.Embed(
            title="<:emoji_for_oddny:1517225564023554219> [ UPDATE SERVICE PROFILE ] <:emoji_for_oddny:1517225564023554219>",
            description="Which of your registered profiles would you like to update?",
            color=0x6b1614
        )
        await interaction.response.send_message(embed=embed, view=ServiceUpdateSelectionView(interaction.user, self.bot))

    @services.command(name="delete", description="Delete your registered service profile")
    async def service_delete(self, interaction: discord.Interaction):
        role = discord.utils.get(interaction.user.roles, id=SERVICE_ROLE_ID)
        if not role:
            return await interaction.response.send_message("❌ You need the **service_access** role to delete a profile!", ephemeral=True)

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