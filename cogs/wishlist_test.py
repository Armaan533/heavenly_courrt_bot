import discord
from discord.ext import commands
import csv
import os
import re

KARUTA_BOT_ID = 646937666251915264

class WishlistTestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.wishlist_db = {}
        self.filepath = "final_readable_master.csv"
        self.load_database()

    def load_database(self):
        if not os.path.exists(self.filepath):
            return
            
        try:
            with open(self.filepath, mode='r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                temp_db = {} 
                for row in reader:
                    char_name = row['character'].strip()
                    series_name = row['series'].strip()
                    key = f"{char_name.lower()}||{series_name.lower()}"
                    
                    temp_db[key] = {
                        "name": char_name,
                        "series": series_name,
                        "wishlists": int(row['wishlist'].strip())
                    }
                self.wishlist_db = temp_db
        except Exception:
            pass

    def save_database(self):
        if not self.wishlist_db:
            return
            
        try:
            with open(self.filepath, mode='w', newline='', encoding='utf-8-sig') as file:
                fieldnames = ['character', 'series', 'wishlist']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                for data in self.wishlist_db.values():
                    writer.writerow({
                        'character': data['name'],
                        'series': data['series'],
                        'wishlist': data['wishlists']
                    })
        except Exception:
            pass

    def update_db_entry(self, char_name: str, series_name: str, wishlists: int) -> bool:
        char_lower = char_name.lower()
        series_lower = series_name.lower()
        matched_key = None
        
        for key in self.wishlist_db.keys():
            k_char, k_series = key.split('||', 1)
            
            if k_char == char_lower:
                if k_series == series_lower:
                    matched_key = key
                    break
                elif series_lower.endswith('...') and k_series.startswith(series_lower[:-3].strip()):
                    matched_key = key
                    break
                elif k_series.endswith('...') and series_lower.startswith(k_series[:-3].strip()):
                    matched_key = key
                    break

        needs_update = False
        
        if matched_key:
            entry = self.wishlist_db[matched_key]
            if entry['wishlists'] != wishlists:
                entry['wishlists'] = wishlists
                needs_update = True
                
            if entry['series'].endswith('...') and not series_name.endswith('...'):
                entry['series'] = series_name
                new_key = f"{char_lower}||{series_name.lower()}"
                self.wishlist_db[new_key] = entry
                del self.wishlist_db[matched_key]
                needs_update = True
        else:
            new_key = f"{char_lower}||{series_lower}"
            self.wishlist_db[new_key] = {
                "name": char_name,
                "series": series_name,
                "wishlists": wishlists
            }
            needs_update = True
            
        return needs_update

    async def process_karuta_embed(self, message: discord.Message):
        if message.author.id != KARUTA_BOT_ID or not message.embeds:
            return

        embed = message.embeds[0]
        
        full_text_parts = []
        if embed.description:
            full_text_parts.append(embed.description)
        for field in embed.fields:
            if field.name:
                full_text_parts.append(field.name)
            if field.value:
                full_text_parts.append(field.value)
                
        full_text = "\n".join(full_text_parts)
        if not full_text:
            return

        needs_global_save = False
        title = str(embed.title) if embed.title else ""

        if "Character Lookup" in title:
            char_name, series_name, wishlists = None, None, None
            for line in full_text.splitlines():
                clean_line = line.replace('*', '').replace('_', '').strip()
                if clean_line.startswith('Character'):
                    parts = re.split(r'[·:]', clean_line, maxsplit=1)
                    if len(parts) > 1: char_name = parts[1].strip()
                elif clean_line.startswith('Series'):
                    parts = re.split(r'[·:]', clean_line, maxsplit=1)
                    if len(parts) > 1: series_name = parts[1].strip()
                elif clean_line.startswith('Wishlisted'):
                    parts = re.split(r'[·:]', clean_line, maxsplit=1)
                    if len(parts) > 1:
                        wl_str = parts[1].replace(',', '').strip()
                        if wl_str.isdigit(): wishlists = int(wl_str)

            if char_name and series_name and wishlists is not None:
                needs_global_save = self.update_db_entry(char_name, series_name, wishlists)

        elif "Character Results" in title:
            chunks = re.split(r'(?=\d+\s*\.\s*[♡❤❤️♥️🤍💖])', full_text)
            
            for chunk in chunks:
                chunk = chunk.replace('*', '').replace('_', '').replace('~', '').strip()
                match = re.match(r'^\d+\s*\.\s*[♡❤❤️♥️🤍💖]?([\d,]+)\s*·\s*(.*?)\s*·\s*(.+)$', chunk)
                
                if match:
                    wishlists = int(match.group(1).replace(',', ''))
                    series_name = match.group(2).strip()
                    char_name = match.group(3).strip()
                    
                    if self.update_db_entry(char_name, series_name, wishlists):
                        needs_global_save = True

        if needs_global_save:
            self.save_database()
            try:
                await message.add_reaction("✅")
            except:
                pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.process_karuta_embed(message)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        author_data = payload.data.get("author")
        if author_data and str(author_data.get("id")) != str(KARUTA_BOT_ID):
            return
                
        try:
            channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
            if not channel:
                return
                
            message = await channel.fetch_message(payload.message_id)
            
            if message.author.id == KARUTA_BOT_ID:
                for r in message.reactions:
                    if str(r.emoji) == "✅" and r.me:
                        await message.remove_reaction("✅", self.bot.user)
                        
                await self.process_karuta_embed(message)
        except:
            pass

    @commands.command(name="wl", aliases=["wishlist", "check"])
    async def test_wishlist(self, ctx, *, character_name: str):
        search_query = character_name.strip().lower()
        
        matches = []
        for key, data in self.wishlist_db.items():
            k_char, k_series = key.split('||', 1)
            if search_query in k_char:
                matches.append(data)
                
        if not matches:
            return await ctx.send(f"❌ Could not find any character matching **{character_name}** in the database.", delete_after=10)

        matches.sort(key=lambda x: x['wishlists'], reverse=True)

        if len(matches) == 1:
            data = matches[0]
            embed = discord.Embed(title="🔍 Wishlist Database Search", color=0x6b1614)
            embed.add_field(name="Character", value=f"**{data['name']}**", inline=True)
            embed.add_field(name="Series", value=f"*{data['series']}*", inline=True)
            embed.add_field(name="Wishlists", value=f"💌 **{data['wishlists']:,}**", inline=False)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(title=f"🔍 Multiple Matches for '{character_name.title()}'", color=0x6b1614)
            desc = ""
            for data in matches[:15]:
                desc += f"• **{data['name']}** from *{data['series']}* — 💌 **{data['wishlists']:,}** WL\n"
            
            if len(matches) > 15:
                desc += f"\n*...and {len(matches) - 15} more matches.*"
                
            embed.description = desc
            await ctx.send(embed=embed)

    @commands.command(name="wlreload")
    @commands.has_permissions(administrator=True)
    async def reload_wishlist(self, ctx):
        self.load_database()
        await ctx.send(f"✅ Reloaded the Wishlist database! Current character count: **{len(self.wishlist_db):,}**")

    @commands.command(name="wlbackup")
    @commands.has_permissions(administrator=True)
    async def backup_wishlist(self, ctx):
        if os.path.exists(self.filepath):
            await ctx.send("📥 Here is the latest Wishlist Database backup:", file=discord.File(self.filepath))
        else:
            await ctx.send("❌ File not found on the server!")

async def setup(bot):
    await bot.add_cog(WishlistTestCog(bot))