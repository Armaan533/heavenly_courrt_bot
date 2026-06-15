import discord
from discord.ext import commands
from discord import app_commands
import time
import datetime
import platform
import psutil
import sys

from utils.database import connector, hcdb 

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time() 

    @app_commands.command(name="status", description="Displays advanced system telemetry and diagnostic data")
    async def status_telemetry(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)

        uptime_seconds = int(time.time() - self.start_time)
        uptime_string = str(datetime.timedelta(seconds=uptime_seconds))
        api_latency = round(self.bot.latency * 1000)

        ram = psutil.virtual_memory()
        ram_used_gb = round(ram.used / (1024 ** 3), 2)
        ram_total_gb = round(ram.total / (1024 ** 3), 2)
        cpu_usage = psutil.cpu_percent(interval=0.1)

        try:
            db_start = time.perf_counter()
            await connector.admin.command('ping')
            db_ping = round((time.perf_counter() - db_start) * 1000, 2)
            db_status = "Online (Connected)"
            doc_count = await hcdb.points.count_documents({})
        except Exception:
            db_ping = "N/A"
            db_status = "Offline (Connection Failed)"
            doc_count = "N/A"

        ticks = chr(96) * 3
        
        embed = discord.Embed(
            title="[ SYSTEM TELEMETRY & DIAGNOSTICS ]",
            description=f"{ticks}ini\n[Status]: ALL SYSTEMS NOMINAL\n{ticks}",
            color=0x8b0000
        )
        
        runtime_stats = (
            f"**⟡ Node Uptime:** `{uptime_string}`\n"
            f"**⟡ API Latency:** `{api_latency}ms`\n"
            f"**⟡ Protocol:** `WebSocket (WSS)`\n"
            f"**⟡ Deployment Pipeline:** `GitHub CI/CD Sync`"
        )
        embed.add_field(name="💠 Runtime Telemetry", value=runtime_stats, inline=False)

        db_stats = (
            f"**⟡ Cluster State:** `{db_status}`\n"
            f"**⟡ Cluster Heartbeat:** `{db_ping}ms`\n"
            f"**⟡ Indexed Entities:** `{doc_count} records`\n"
            f"**⟡ Driver:** `Pymongo Async v{__import__('pymongo').__version__}`"
        )
        embed.add_field(name="🗄️ Database Node (MongoDB)", value=db_stats, inline=False)

        infra_stats = (
            f"**⟡ Compute Node:** `PebbleHost ({platform.system()} {platform.release()})`\n"
            f"**⟡ CPU Thread Allocation:** `{cpu_usage}% utilization`\n"
            f"**⟡ Memory Payload:** `{ram_used_gb} GB / {ram_total_gb} GB ({ram.percent}%)`"
        )
        embed.add_field(name="🖥️ Compute Infrastructure", value=infra_stats, inline=False)

        stack_stats = (
            f"**⟡ Python Runtime Environment:** `v{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}`\n"
            f"**⟡ Discord.py API Wrapper:** `v{discord.__version__}`"
        )
        embed.add_field(name="⚙️ Software Architecture", value=stack_stats, inline=False)

        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.set_footer(text=f"Auth: {interaction.user.display_name} // Heavenly Court ✦", icon_url=interaction.user.display_avatar.url)

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(StatsCog(bot))