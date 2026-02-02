"""
Base skill interface for BeatBot.

Skills extend the agent's capabilities with specific functionalities.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from security.permissions import Permission, ResourceType, PermissionAction


class SkillCategory(str, Enum):
    """Skill categories."""
    SYSTEM = "system"
    FILE = "file"
    WEB = "web"
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity"
    CUSTOM = "custom"


@dataclass
class SkillResult:
    """Result from skill execution."""
    success: bool
    data: Any
    message: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SkillContext:
    """Context provided to skills during execution."""
    user_id: str
    conversation_id: str
    parameters: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class Skill(ABC):
    """
    Base class for all BeatBot skills.
    
    Skills are modular capabilities that extend the agent's functionality.
    Each skill declares its required permissions and implements execution logic.
    """
    
    # Skill metadata (must be overridden)
    name: str = "base_skill"
    description: str = "Base skill interface"
    category: SkillCategory = SkillCategory.CUSTOM
    version: str = "0.1.0"
    
    # Required permissions
    required_permissions: List[Permission] = []
    
    # Configuration
    enabled: bool = True
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize skill.
        
        Args:
            config: Skill-specific configuration
        """
        self.config = config or {}
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate skill configuration. Override if needed."""
        pass
    
    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """
        Execute the skill.
        
        Args:
            context: Execution context with user info and parameters
        
        Returns:
            SkillResult with execution outcome
        """
        pass
    
    def get_required_permissions(self) -> List[Permission]:
        """
        Get permissions required by this skill.
        
        Returns:
            List of Permission objects
        """
        return self.required_permissions
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get skill metadata.
        
        Returns:
            Dict with skill information
        """
        return {
            'name': self.name,
            'description': self.description,
            'category': self.category.value,
            'version': self.version,
            'enabled': self.enabled,
            'required_permissions': [
                {
                    'resource_type': p.resource_type.value,
                    'pattern': p.pattern,
                    'action': p.action.value
                }
                for p in self.required_permissions
            ]
        }
    
    async def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """
        Validate execution parameters.
        
        Args:
            parameters: Parameters to validate
        
        Returns:
            True if valid, False otherwise
        """
        # Override in subclass for parameter validation
        return True
