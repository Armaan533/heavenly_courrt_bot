import discord
from discord.ext import commands
import csv
import os

class WishlistTestCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.wishlist_db = {}
        self.load_database()

    def load_database(self):
        filepath = "final_readable_master.csv"
        
        if not os.path.exists(filepath):
            print(f"⚠️ [Wishlist DB] File '{filepath}' not found! Make sure it is next to main.py.")
            return
            
        try:
            with open(filepath, mode='r', encoding='utf-8-sig') as file:
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
            await ctx.send(f"❌ Could not find **{character_name}** in the database. Ensure it is spelled exactly as it is in the CSV.", delete_after=10)

    @commands.command(name="wlreload")
    @commands.has_permissions(administrator=True)
    async def reload_wishlist(self, ctx):
        """Allows admins to reload the CSV without restarting the bot."""
        self.wishlist_db.clear()
        self.load_database()
        await ctx.send(f"✅ Reloaded the Wishlist database! Current character count: **{len(self.wishlist_db):,}**")

async def setup(bot):
    await bot.add_cog(WishlistTestCog(bot))