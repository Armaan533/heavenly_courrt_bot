import discord
from discord.ext import commands
import csv
import os
import re

KARUTA_BOT_ID = 432610292342587392

class WishlistTestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.wishlist_db = {}
        self.filepath = "final_readable_master.csv"
        self.load_database()

    def load_database(self):
        if not os.path.exists(self.filepath):
            print(f"⚠️ [Wishlist DB] File '{self.filepath}' not found! Make sure it is next to main.py.")
            return
            
        try:
            with open(self.filepath, mode='r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    char_name = row['character'].strip().lower()
                    self.wishlist_db[char_name] = {
                        "name": row['character'].strip(),
                        "series": row['series'].strip(),
                        "wishlists": int(row['wishlist'].strip())
                    }
            print(f"✅ [Wishlist DB] Successfully loaded {len(self.wishlist_db):,} characters!")
        except Exception as e:
            print(f"❌ [Wishlist DB] Error loading data: {e}")

    def save_database(self):
        """Writes the current dictionary back into the CSV file."""
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
        except Exception as e:
            print(f"❌ [Wishlist DB] Error saving to CSV: {e}")

    async def process_karuta_embed(self, message: discord.Message):
        """Scans a Karuta lookup message to extract and save wishlist data."""
        if message.author.id != KARUTA_BOT_ID or not message.embeds:
            return

        embed = message.embeds[0]

        if not embed.title or "Character Lookup" not in embed.title:
            return
            
        if not embed.description:
            return

        clean_desc = embed.description.replace('*', '').replace('_', '')

        char_match = re.search(r'Character\s*.\s*(.+)', clean_desc)
        series_match = re.search(r'Series\s*.\s*(.+)', clean_desc)
        wl_match = re.search(r'Wishlisted\s*.\s*([\d,]+)', clean_desc)
        
        if char_match and series_match and wl_match:
            try:
                char_name = char_match.group(1).strip()
                series_name = series_match.group(1).strip()
                wishlists = int(wl_match.group(1).replace(',', '').strip())
                
                search_query = char_name.lower()
                needs_update = False
                
                if search_query in self.wishlist_db:
                    if self.wishlist_db[search_query]['wishlists'] != wishlists:
                        self.wishlist_db[search_query]['wishlists'] = wishlists
                        needs_update = True
                        print(f"🔄 [Wishlist DB] Updated {char_name} to {wishlists} WL")
                else:
                    self.wishlist_db[search_query] = {
                        "name": char_name,
                        "series": series_name,
                        "wishlists": wishlists
                    }
                    needs_update = True
                    print(f"🌟 [Wishlist DB] Discovered new character: {char_name} ({wishlists} WL)")

                if needs_update:
                    self.save_database()
                    await message.add_reaction("✅")

            except Exception as e:
                print(f"❌ [Wishlist DB] Parsing processing failure: {e}")

    # --- EVENT LISTENERS ---
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Fires when Karuta sends a new lookup embed."""
        await self.process_karuta_embed(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Fires when Karuta edits an embed (often happens a split second after sending)."""
        await self.process_karuta_embed(after)

    # --- COMMANDS ---

    @commands.command(name="wl", aliases=["wishlist", "check"])
    async def test_wishlist(self, ctx, *, character_name: str):
        """Prefix command to look up a character's wishlist count."""
        search_query = character_name.strip().lower()
        
        if search_query in self.wishlist_db:
            data = self.wishlist_db[search_query]
            
            embed = discord.Embed(
                title="🔍 Wishlist Database Search",
                color=0x6b1614
            )
            embed.add_field(name="Character", value=f"**{data['name']}**", inline=True)
            embed.add_field(name="Series", value=f"*{data['series']}*", inline=True)
            embed.add_field(name="Wishlists", value=f"💌 **{data['wishlists']:,}**", inline=False)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Could not find **{character_name}** in the database. Run `klu {character_name}` to automatically add them!", delete_after=10)

    @commands.command(name="wlreload")
    @commands.has_permissions(administrator=True)
    async def reload_wishlist(self, ctx):
        """Allows admins to reload the CSV without restarting the bot."""
        self.wishlist_db.clear()
        self.load_database()
        await ctx.send(f"✅ Reloaded the Wishlist database! Current character count: **{len(self.wishlist_db):,}**")

async def setup(bot):
    await bot.add_cog(WishlistTestCog(bot))