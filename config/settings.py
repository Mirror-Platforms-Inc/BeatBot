"""
Configuration management for BeatBot.

Loads configuration from YAML files and environment variables,
with support for profiles and hot-reloading.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv


class ModelConfig(BaseModel):
    """Model provider configuration."""
    provider: str = "litellm"
    default_model: str = "ollama/llama3.2"
    fallback_models: list[str] = Field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 4096
    timeout: int = 120


class SecurityConfig(BaseModel):
    """Security settings."""
    sandbox_enabled: bool = True
    sandbox_timeout: int = 60
    sandbox_memory_limit: str = "512m"
    sandbox_cpu_limit: float = 1.0
    require_approval: bool = True
    approval_timeout: int = 300
    auto_approve_safe_commands: bool = False
    allowed_directories: list[str] = Field(default_factory=list)
    command_whitelist: list[str] = Field(default_factory=list)
    command_blacklist: list[str] = Field(default_factory=list)
    rate_limit: Dict[str, Any] = Field(default_factory=dict)


class StorageConfig(BaseModel):
    """Storage and persistence settings."""
    database_path: str = "~/.beatbot/data.db"
    encryption_enabled: bool = True
    use_embeddings: bool = True
    embedding_model: str = "all-MiniLM-L6-v2"
    retention: Dict[str, Any] = Field(default_factory=dict)

    @validator('database_path')
    def expand_path(cls, v):
        return str(Path(v).expanduser())


class HeartbeatConfig(BaseModel):
    """Heartbeat and self-prompting settings."""
    enabled: bool = True
    interval: int = 3600
    quiet_hours: Dict[str, Any] = Field(default_factory=dict)
    triggers: list[Dict[str, Any]] = Field(default_factory=list)


class MessagingConfig(BaseModel):
    """Messaging platform configuration."""
    platform: str = "discord"
    discord: Dict[str, Any] = Field(default_factory=dict)


class LoggingConfig(BaseModel):
    """Logging and audit configuration."""
    level: str = "INFO"
    format: str = "json"
    audit: Dict[str, Any] = Field(default_factory=dict)


class SkillsConfig(BaseModel):
    """Skills configuration."""
    enabled_builtin_skills: list[str] = Field(default_factory=list)
    custom_skills_path: str = "~/.beatbot/custom_skills"
    skill_timeout: int = 300

    @validator('custom_skills_path')
    def expand_path(cls, v):
        return str(Path(v).expanduser())


class DevelopmentConfig(BaseModel):
    """Development settings."""
    debug_mode: bool = False
    mock_approvals: bool = False
    disable_sandbox: bool = False


class Settings(BaseModel):
    """Main settings container."""
    model: ModelConfig = Field(default_factory=ModelConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    heartbeat: HeartbeatConfig = Field(default_factory=HeartbeatConfig)
    messaging: MessagingConfig = Field(default_factory=MessagingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    development: DevelopmentConfig = Field(default_factory=DevelopmentConfig)


class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, config_path: Optional[str] = None, profile: str = "default"):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file (default: config/default_config.yaml)
            profile: Configuration profile to use (default, production, development)
        """
        self.profile = profile
        self.config_path = config_path or self._get_default_config_path()
        self.settings: Optional[Settings] = None
        self._load_config()
    
    def _get_default_config_path(self) -> str:
        """Get default configuration file path."""
        base_dir = Path(__file__).parent
        return str(base_dir / "default_config.yaml")
    
    def _load_config(self) -> None:
        """Load configuration from file and environment variables."""
        # Load environment variables
        load_dotenv()
        
        # Load YAML config
        config_data = {}
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config_data = yaml.safe_load(f) or {}
        
        # Apply environment variable overrides
        config_data = self._apply_env_overrides(config_data)
        
        # Apply profile-specific settings
        config_data = self._apply_profile(config_data)
        
        # Create Settings object
        self.settings = Settings(**config_data)
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        # Model settings
        if os.getenv('BEATBOT_MODEL_PROVIDER'):
            config.setdefault('model', {})['provider'] = os.getenv('BEATBOT_MODEL_PROVIDER')
        if os.getenv('BEATBOT_MODEL_DEFAULT'):
            config.setdefault('model', {})['default_model'] = os.getenv('BEATBOT_MODEL_DEFAULT')
        
        # Security settings
        if os.getenv('BEATBOT_SANDBOX_ENABLED'):
            config.setdefault('security', {})['sandbox_enabled'] = \
                os.getenv('BEATBOT_SANDBOX_ENABLED').lower() == 'true'
        if os.getenv('BEATBOT_REQUIRE_APPROVAL'):
            config.setdefault('security', {})['require_approval'] = \
                os.getenv('BEATBOT_REQUIRE_APPROVAL').lower() == 'true'
        
        # Storage settings
        if os.getenv('BEATBOT_DB_PATH'):
            config.setdefault('storage', {})['database_path'] = os.getenv('BEATBOT_DB_PATH')
        
        return config
    
    def _apply_profile(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply profile-specific settings."""
        if self.profile == "development":
            config.setdefault('development', {})['debug_mode'] = True
            config.setdefault('logging', {})['level'] = 'DEBUG'
        elif self.profile == "production":
            config.setdefault('development', {})['debug_mode'] = False
            config.setdefault('development', {})['mock_approvals'] = False
            config.setdefault('security', {})['require_approval'] = True
        elif self.profile == "minimal-security":
            # WARNING: Only for testing in controlled environments
            config.setdefault('security', {})['sandbox_enabled'] = False
            config.setdefault('security', {})['require_approval'] = False
        
        return config
    
    def reload(self) -> None:
        """Reload configuration from file."""
        self._load_config()
    
    def get(self) -> Settings:
        """Get current settings."""
        if self.settings is None:
            self._load_config()
        return self.settings
    
    def save(self, path: Optional[str] = None) -> None:
        """
        Save current configuration to file.
        
        Args:
            path: Path to save configuration (default: current config_path)
        """
        if self.settings is None:
            return
        
        save_path = path or self.config_path
        config_dict = self.settings.model_dump()
        
        with open(save_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def init_config(config_path: Optional[str] = None, profile: str = "default") -> ConfigManager:
    """
    Initialize global configuration.
    
    Args:
        config_path: Path to configuration file
        profile: Configuration profile to use
    
    Returns:
        ConfigManager instance
    """
    global _config_manager
    _config_manager = ConfigManager(config_path, profile)
    return _config_manager


def get_config() -> Settings:
    """
    Get current configuration.
    
    Returns:
        Settings object
    
    Raises:
        RuntimeError: If configuration not initialized
    """
    if _config_manager is None:
        raise RuntimeError("Configuration not initialized. Call init_config() first.")
    return _config_manager.get()


def reload_config() -> None:
    """Reload configuration from file."""
    if _config_manager is None:
        raise RuntimeError("Configuration not initialized. Call init_config() first.")
    _config_manager.reload()
