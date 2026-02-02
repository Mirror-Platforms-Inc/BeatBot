"""
BeatBot - Secure AI Agent with System Access

Main entry point for the application.
"""

import asyncio
import argparse
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass  # In case stdout is not a file-like object (e.g. during some tests)
from pathlib import Path

from config.settings import init_config, get_config
from security.credentials import get_credential_manager
from storage.database import EncryptedDatabase, AuditLogger
from core.memory import MemoryManager
from core.agent import Agent
from core.executor import CommandExecutor, ExecutionContext
from core.heartbeat import HeartbeatScheduler
from models.litellm_provider import LiteLLMProvider
from security.sandbox import SandboxManager, SandboxConfig
from security.validator import CommandValidator, ValidationLevel
from security.permissions import PermissionManager, ApprovalManager
from core.skill_manager import SkillManager


class BeatBot:
    """Main BeatBot application."""
    
    def __init__(self, config_path: Optional[str] = None, profile: str = "default"):
        """
        Initialize BeatBot.
        
        Args:
            config_path: Path to configuration file
            profile: Configuration profile
        """
        # Initialize configuration
        init_config(config_path, profile)
        self.config = get_config()
        
        # Initialize components
        self.credential_manager = None
        self.db = None
        self.memory = None
        self.agent = None
        self.heartbeat = None
        self.message_callback = None  # Function to handle proactive messages
        
    def set_message_callback(self, callback):
        """Set callback for proactive messages."""
        self.message_callback = callback
        
    async def initialize(self) -> None:
        """Initialize all components."""
        print("🤖 Initializing BeatBot...")
        
        # Credentials
        self.credential_manager = get_credential_manager()
        
        # Database
        db_key = self.credential_manager.get_credential("db_encryption_key")
        if not db_key:
            # Generate new key
            import secrets
            db_key = secrets.token_urlsafe(32)
            self.credential_manager.store_credential("db_encryption_key", db_key)
        
        self.db = EncryptedDatabase(
            self.config.storage.database_path,
            db_key
        )
        
        # Audit logger
        audit_logger = AuditLogger(self.db)
        
        # Memory
        self.memory = MemoryManager(
            self.db,
            context_window=20,
            retention_days=self.config.storage.retention.get('conversation_days', 90)
        )
        
        # Model provider
        model_config = {
            'default_model': self.config.model.default_model,
            'fallback_models': self.config.model.fallback_models,
            'temperature': self.config.model.temperature,
            'max_tokens': self.config.model.max_tokens,
            'timeout': self.config.model.timeout
        }
        model_provider = LiteLLMProvider(model_config)
        
        # Security components
        sandbox_config = SandboxConfig(
            enabled=self.config.security.sandbox_enabled,
            timeout=self.config.security.sandbox_timeout,
            memory_limit=self.config.security.sandbox_memory_limit,
            cpu_limit=self.config.security.sandbox_cpu_limit,
            allowed_volume_mounts=self.config.security.allowed_directories
        )
        
        validator = CommandValidator(ValidationLevel.STRICT)
        permission_manager = PermissionManager()
        approval_manager = ApprovalManager(
            approval_timeout=self.config.security.approval_timeout
        )
        
        # Command executor
        executor = CommandExecutor(
            sandbox_config,
            validator,
            permission_manager,
            approval_manager
        )
        
        # Agent
        self.agent = Agent(
            model_provider,
            self.memory,
            executor,
            audit_logger
        )
        
        # Skill Manager
        skill_manager = SkillManager()
        
        # Load custom skills
        custom_skills_path = Path(self.config.skills.custom_skills_path).expanduser()
        if custom_skills_path.exists():
            skill_manager.load_from_directory(str(custom_skills_path))
            
        # Register with Agent
        self.agent.register_skill_manager(skill_manager)
        
        # Heartbeat scheduler
        if self.config.heartbeat.enabled:
            quiet_hours = self.config.heartbeat.quiet_hours
            self.heartbeat = HeartbeatScheduler(
                enabled=True,
                quiet_hours_start=datetime.strptime(quiet_hours['start'], "%H:%M").time() if quiet_hours.get('enabled') else None,
                quiet_hours_end=datetime.strptime(quiet_hours['end'], "%H:%M").time() if quiet_hours.get('enabled') else None
            )
            
            # Register triggers from config
            for trigger in self.config.heartbeat.triggers:
                if trigger['type'] == 'time':
                    self.heartbeat.add_task(
                        task_id=f"trigger_{trigger['action']}",
                        name=trigger['action'],
                        schedule=trigger['schedule'],
                        action=lambda t=trigger: self._handle_heartbeat_trigger(t)
                    )
            
            # Start the scheduler
            self.heartbeat.start()
        
        print("✅ BeatBot initialized successfully!")
    
    async def _handle_heartbeat_trigger(self, trigger: dict):
        """Handle a heartbeat trigger action."""
        action = trigger.get('action')
        print(f"💓 Heartbeat Trigger: {action}")
        
        prompt = ""
        if action == 'morning_briefing':
            prompt = "Please check my schedule and reminders and give me a morning briefing."
        elif action == 'check_reminders':
            prompt = "Check if there are any pending reminders or tasks."
        else:
            prompt = f"Executing scheduled action: {action}"
            
        # Process via Agent
        # Use a system user ID for internal triggers
        response = await self.agent.process_message(
            user_message=prompt,
            user_id="beatbot_system",
            conversation_id="system_heartbeat",
            enable_autonomy=True
        )
        
        # Send output if callback registered
        if self.message_callback:
            await self.message_callback(response)
    
    async def interactive_mode(self) -> None:
        """Run in interactive console mode."""
        print("\n" + "="*60)
        print("BeatBot Interactive Mode")
        print("Type 'exit' to quit, 'help' for commands")
        print("="*60 + "\n")
        
        user_id = "console_user"
        conversation_id = self.memory.start_conversation(user_id, title="Console Session")
        
        while True:
            try:
                user_input = input("\n💬 You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['exit', 'quit']:
                    print("👋 Goodbye!")
                    break
                
                if user_input.lower() == 'help':
                    self._print_help()
                    continue
                
                # Process message
                print("\n🤖 BeatBot: ", end="", flush=True)
                
                async for token in self.agent.stream_response(user_input, user_id, conversation_id):
                    print(token, end="", flush=True)
                
                print()  # New line after response
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
    
    def _print_help(self) -> None:
        """Print help message."""
        print("""
Available commands:
  - Just type naturally to chat with BeatBot
  - 'help' - Show this help message
  - 'exit' or 'quit' - Exit the program
  
BeatBot can:
  - Execute system commands (with your approval)
  - Manage files and directories
  - Search the web
  - Set reminders
  - And more!

All dangerous operations require your approval.
All commands run in isolated sandboxes for security.
        """)
    
    async def shutdown(self) -> None:
        """Shutdown BeatBot cleanly."""
        print("\n🛑 Shutting down BeatBot...")
        
        if self.heartbeat:
            await self.heartbeat.stop()
        
        if self.db:
            self.db.close()
        
        print("✅ Shutdown complete")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="BeatBot - Secure AI Agent")
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--profile', default='default', help='Configuration profile')
    parser.add_argument('--mode', default='interactive', choices=['interactive', 'daemon', 'discord'], 
                       help='Run mode')
    
    args = parser.parse_args()
    
    bot = BeatBot(config_path=args.config, profile=args.profile)
    
    try:
        await bot.initialize()
        
        if args.mode == 'interactive':
            await bot.interactive_mode()
        elif args.mode == 'discord':
            import os
            # Try to get token from env var first, then keyring
            token = os.getenv('BEATBOT_DISCORD_TOKEN')
            if not token and bot.credential_manager:
                token = bot.credential_manager.get_credential('discord_token')
                
            if not token:
                print("❌ Error: Discord token not found.")
                print("   Please set BEATBOT_DISCORD_TOKEN env var or store 'discord_token' in keyring.")
                return 1
                
            from integrations.messaging.discord_bot import run_discord_bot
            print("🚀 Starting BeatBot in Discord Mode...")
            await run_discord_bot(token, bot)
            
        else:
            print("Daemon mode not yet implemented")
            return 1
        
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await bot.shutdown()
    
    return 0


if __name__ == "__main__":
    from datetime import datetime
    from typing import Optional
    
    sys.exit(asyncio.run(main()))
