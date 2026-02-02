"""
Discord Integration for BeatBot.

Handles:
- Message reception and routing to Agent
- Interactive Approval Buttons
- Heartbeat notifications
"""

import sys
import asyncio
import logging
from typing import Optional, List, Dict, Any, Union
from pathlib import Path

# Third-party
import discord
from discord.ext import commands

# Project imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.agent import Agent
from security.permissions import ApprovalManager


class DiscordApprovalManager(ApprovalManager):
    """
    Extends ApprovalManager to send interactive Discord cards.
    """
    
    def __init__(self, bot, approval_timeout: int = 300):
        super().__init__(approval_timeout)
        self.bot = bot
        self.msg_map: Dict[str, int] = {}  # approval_id -> discord_message_id
        
    def request_approval(
        self,
        operation_id: str,
        description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Request approval via Discord View.
        """
        # Call super to store in pending_approvals
        op_id = super().request_approval(operation_id, description, context)
        
        # Determine channel from context
        channel_id = None
        if context:
            if 'channel_id' in context:
                channel_id = context['channel_id']
            elif 'conversation_id' in context:
                # Expecting 'discord_CHANNELID'
                val = str(context['conversation_id'])
                if val.startswith('discord_'):
                    try:
                        channel_id = int(val.split('_')[1])
                    except (IndexError, ValueError):
                        pass
        
        # If no channel yet, maybe this is a system/heartbeat command?
        # We need a fallback channel from bot config (if injected)
        if not channel_id:
             # Try first allowed user or configured channel
             # This is tricky without access to bot's allowed lists here easily,
             # but we can query the bot for them if exposed.
             pass
            
        if not channel_id:
            logging.warning(f"Could not determine channel ID for approval {op_id}")
            return op_id
            
        # Schedule the Discord message sending (must happen on the loop)
        asyncio.run_coroutine_threadsafe(
            self._send_approval_card(channel_id, op_id, description, context),
            self.bot.loop
        )
        return op_id

    async def _send_approval_card(self, channel_id: int, op_id: str, description: str, context: Dict[str, Any]):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException:
                pass
        
        if not channel:
            # Fallback: DM first allowed user?
            return

        embed = discord.Embed(
            title="⚠️ Approval Required",
            description=description,
            color=discord.Color.orange()
        )
        
        if context:
            cmd = context.get('command', 'Unknown')
            embed.add_field(name="Command", value=f"```bash\n{cmd}\n```", inline=False)
            
        view = ApprovalView(self, op_id)
        msg = await channel.send(embed=embed, view=view)
        self.msg_map[op_id] = msg.id


class ApprovalView(discord.ui.View):
    """Buttons for Approve/Deny."""
    
    def __init__(self, manager: 'DiscordApprovalManager', op_id: str):
        super().__init__(timeout=manager.approval_timeout)
        self.manager = manager
        self.op_id = op_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.manager.approve(self.op_id):
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()
            embed.title = "✅ Approved"
            embed.set_footer(text=f"Approved by {interaction.user.display_name}")
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message("Approval failed or expired.", ephemeral=True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, emoji="🛑")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.manager.deny(self.op_id):
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.red()
            embed.title = "🛑 Denied"
            embed.set_footer(text=f"Denied by {interaction.user.display_name}")
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message("Denial failed or expired.", ephemeral=True)


class BeatBotDiscord(commands.Bot):
    """
    Discord Bot client for BeatBot.
    """
    
    def __init__(self, agent: Agent, config: Dict[str, Any]):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix=config.get('messaging', {}).get('discord', {}).get('command_prefix', '!'),
            intents=intents,
            help_command=None
        )
        
        self.agent = agent
        self.beatbot_config = config
        self.allowed_users = [
            str(uid) for uid in 
            config.get('messaging', {}).get('discord', {}).get('allowed_users', [])
        ]
        
    async def on_ready(self):
        print(f"🤖 Connected to Discord as {self.user} (ID: {self.user.id})")
        print(f"   Invite Link: https://discord.com/api/oauth2/authorize?client_id={self.user.id}&permissions=2147483648&scope=bot")
        
        # Inject Discord-aware Approval Manager
        timeout = self.beatbot_config.get('security', {}).get('approval_timeout', 300)
        discord_approvals = DiscordApprovalManager(self, approval_timeout=timeout)
        
        if hasattr(self.agent, 'executor'):
            discord_approvals.pending_approvals = self.agent.executor.approvals.pending_approvals
            self.agent.executor.approvals = discord_approvals
            print("✅ Discord Approval Manager injected.")
        
    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return
        
        if self.allowed_users and str(message.author.id) not in self.allowed_users:
            return
            
        await self.process_commands(message)
        
        is_dm = isinstance(message.channel, discord.DMChannel)
        is_mention = self.user in message.mentions
        is_prefix = message.content.startswith(self.command_prefix)
        
        if not (is_dm or is_mention or is_prefix):
            return

        content = message.content.replace(f"<@{self.user.id}>", "").strip()
        if is_prefix:
            content = content[len(self.command_prefix):].strip()
            
        if not content:
            return

        async with message.channel.typing():
            try:
                conv_id = f"discord_{message.channel.id}"
                
                response = await self.agent.process_message(
                    user_message=content,
                    user_id=f"discord_{message.author.id}",
                    conversation_id=conv_id,
                    enable_autonomy=True
                )
                
                await self._send_chunked(message.channel, response)
                
            except Exception as e:
                await message.channel.send(f"❌ Error: {str(e)}")

    async def _send_chunked(self, channel, text):
        if len(text) <= 2000:
            await channel.send(text)
        else:
            for i in range(0, len(text), 2000):
                await channel.send(text[i:i+2000])


async def run_discord_bot(token: str, app):
    """Entry point to run the bot. app is BeatBot instance."""
    agent = app.agent
    config = app.config
    
    bot = BeatBotDiscord(agent, config)
    
    # Callback for heartbeat messages from BeatBot app
    async def send_heartbeat_message(text: str):
        allowed_channels = config.get('messaging', {}).get('discord', {}).get('allowed_channels', [])
        target_channel = None
        
        # Priority 1: Configured channel
        if allowed_channels:
            try:
                target_channel = await bot.fetch_channel(int(allowed_channels[0]))
            except:
                pass
        
        # Priority 2: DM first allowed user
        if not target_channel:
            allowed_users = config.get('messaging', {}).get('discord', {}).get('allowed_users', [])
            if allowed_users:
                try:
                    user = await bot.fetch_user(int(allowed_users[0]))
                    target_channel = user
                except:
                    pass
        
        if target_channel:
            await bot._send_chunked(target_channel, text)
        else:
            logging.warning("Heartbeat triggered but nowhere to send message.")

    # Apply callback
    app.set_message_callback(send_heartbeat_message)
    
    async with bot:
        await bot.start(token)
