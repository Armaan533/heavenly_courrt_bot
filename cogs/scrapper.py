import discord
from discord.ext import commands
import json
import os
import asyncio

from frame_prices import FRAME_DB

class ScraperCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.is_scraping = False

    @commands.command(name="start")
    async def start_scraping(self, ctx, arg=None):
        if arg != "db":
            return
        
        if self.is_scraping:
            return await ctx.send("❌ Already scraping! Type `,stop` if you want to cancel.")
            
        self.is_scraping = True
        frames_to_scrape = list(FRAME_DB.keys())
        total = len(frames_to_scrape)
        
        await ctx.send(f"🚀 **Starting recording!** ({total} frames)\n*(Type `,skip` to skip a broken frame, or `,stop` to save and pause)*")
        
        for i, frame_name in enumerate(frames_to_scrape):
            if not self.is_scraping:
                break
                
            if "image" in FRAME_DB[frame_name] and FRAME_DB[frame_name]["image"]:
                continue

            await ctx.send(f"`kii {frame_name}`")
            
            def check(m):
                if m.channel != ctx.channel: 
                    return False
                if m.author == ctx.author and m.content.lower() in [",skip", ",stop"]: 
                    return True
                if m.author.bot and "karuta" in m.author.name.lower() and m.embeds:
                    if m.embeds[0].title and "Item Details" in m.embeds[0].title:
                        return True
                return False
                
            try:
                msg = await self.bot.wait_for('message', check=check, timeout=120.0)
                
                if msg.author == ctx.author:
                    if msg.content.lower() == ",stop":
                        self.is_scraping = False
                        await ctx.send("🛑 Stopped scraping process. Generating your file now...")
                        break
                    elif msg.content.lower() == ",skip":
                        await ctx.send(f"⏭️ Skipped **{frame_name}**.")
                        continue
                    
                embed = msg.embeds[0]
                img_url = None
                
                if embed.thumbnail and embed.thumbnail.url:
                    img_url = embed.thumbnail.url
                    
                if img_url:
                    FRAME_DB[frame_name]["image"] = img_url
                    await msg.add_reaction("✅")
                    await asyncio.sleep(1)
                else:
                    await ctx.send("⚠️ Couldn't find a thumbnail in Karuta's embed. Skipping to next...")
                    
            except asyncio.TimeoutError:
                await ctx.send("⏱️ Timed out waiting for a response. Stopping scrape.")
                self.is_scraping = False
                break
        
        self.is_scraping = False
        
        file_name = "frame_prices_updated.py"
        with open(file_name, "w", encoding="utf-8") as f:
            f.write("FRAME_DB = ")
            f.write(json.dumps(FRAME_DB, indent=4))
            
        await ctx.send("🎉 **Scraping complete!** Here is your fully updated database file. Just download this, rename it to `frame_prices.py`, and replace your old one!", file=discord.File(file_name))
        
        if os.path.exists(file_name):
            os.remove(file_name)

async def setup(bot):
    await bot.add_cog(ScraperCog(bot))