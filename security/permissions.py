"""
Granular permission system for controlling agent actions.

Allows users to define which commands and operations are allowed,
with approval workflows.
"""

import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path


class PermissionAction(str, Enum):
    """Permission decision."""
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"  # Require user approval


class ResourceType(str, Enum):
    """Types of resources that can be permission-controlled."""
    COMMAND = "command"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    NETWORK = "network"
    BROWSER = "browser"
    ENV_VAR = "env_var"


@dataclass
class Permission:
    """A permission rule."""
    resource_type: ResourceType
    pattern: str  # Regex pattern or glob
    action: PermissionAction
    description: Optional[str] = None


class PermissionManager:
    """
    Manages permissions for agent operations.
    
    Implements a rule-based system where permissions are checked
    against a list of rules in order.
    """
    
    def __init__(self):
        """Initialize permission manager with empty ruleset."""
        self.rules: List[Permission] = []
        self._load_default_rules()
    
    def _load_default_rules(self) -> None:
        """Load default permission rules (deny dangerous operations)."""
        # Deny dangerous commands by default
        self.rules.extend([
            Permission(
                resource_type=ResourceType.COMMAND,
                pattern=r"rm\s+-rf\s+/",
                action=PermissionAction.DENY,
                description="Prevent recursive deletion of root"
            ),
            Permission(
                resource_type=ResourceType.COMMAND,
                pattern=r"mkfs",
                action=PermissionAction.DENY,
                description="Prevent filesystem formatting"
            ),
            Permission(
                resource_type=ResourceType.COMMAND,
                pattern=r"dd\s+if=",
                action=PermissionAction.DENY,
                description="Prevent disk writing"
            ),
            # Require approval for file system modifications
            Permission(
                resource_type=ResourceType.FILE_WRITE,
                pattern=r"/etc/.*",
                action=PermissionAction.ASK,
                description="System configuration files require approval"
            ),
            Permission(
                resource_type=ResourceType.FILE_WRITE,
                pattern=r"/sys/.*",
                action=PermissionAction.ASK,
                description="System files require approval"
            ),
        ])
    
    def add_rule(self, rule: Permission) -> None:
        """
        Add a permission rule.
        
        Rules are checked in order, so earlier rules take precedence.
        
        Args:
            rule: Permission rule to add
        """
        self.rules.append(rule)
    
    def add_rule_from_dict(self, rule_dict: Dict[str, Any]) -> None:
        """
        Add a rule from dictionary format.
        
        Args:
            rule_dict: Dictionary with keys: resource_type, pattern, action, description
        """
        rule = Permission(
            resource_type=ResourceType(rule_dict['resource_type']),
            pattern=rule_dict['pattern'],
            action=PermissionAction(rule_dict['action']),
            description=rule_dict.get('description')
        )
        self.add_rule(rule)
    
    def check_permission(
        self,
        resource_type: ResourceType,
        resource_value: str,
        default_action: PermissionAction = PermissionAction.ASK
    ) -> PermissionAction:
        """
        Check if an operation is permitted.
        
        Args:
            resource_type: Type of resource being accessed
            resource_value: Value to check (e.g., command string, file path)
            default_action: Action to take if no rules match
        
        Returns:
            PermissionAction (ALLOW, DENY, or ASK)
        """
        # Check rules in order
        for rule in self.rules:
            if rule.resource_type != resource_type:
                continue
            
            # Check if pattern matches
            if self._matches_pattern(rule.pattern, resource_value):
                return rule.action
        
        # No matching rule, use default
        return default_action
    
    def _matches_pattern(self, pattern: str, value: str) -> bool:
        """
        Check if value matches pattern (regex or glob).
        
        Args:
            pattern: Pattern to match (regex)
            value: Value to check
        
        Returns:
            True if matches
        """
        try:
            return bool(re.search(pattern, value))
        except re.error:
            # If regex is invalid, fall back to exact match
            return pattern == value
    
    def allow_command(self, command: str) -> None:
        """
        Add a rule to always allow a specific command.
        
        Args:
            command: Command pattern to allow
        """
        self.add_rule(Permission(
            resource_type=ResourceType.COMMAND,
            pattern=re.escape(command),
            action=PermissionAction.ALLOW,
            description=f"Auto-allowed: {command}"
        ))
    
    def deny_command(self, command: str) -> None:
        """
        Add a rule to always deny a specific command.
        
        Args:
            command: Command pattern to deny
        """
        self.add_rule(Permission(
            resource_type=ResourceType.COMMAND,
            pattern=re.escape(command),
            action=PermissionAction.DENY,
            description=f"Auto-denied: {command}"
        ))
    
    def allow_directory(self, directory: str, write: bool = False) -> None:
        """
        Allow access to a directory.
        
        Args:
            directory: Directory path to allow
            write: Whether to allow write access
        """
        dir_path = str(Path(directory).resolve())
        pattern = f"{re.escape(dir_path)}.*"
        
        self.add_rule(Permission(
            resource_type=ResourceType.FILE_READ,
            pattern=pattern,
            action=PermissionAction.ALLOW,
            description=f"Allowed directory read: {directory}"
        ))
        
        if write:
            self.add_rule(Permission(
                resource_type=ResourceType.FILE_WRITE,
                pattern=pattern,
                action=PermissionAction.ALLOW,
                description=f"Allowed directory write: {directory}"
            ))
    
    def export_rules(self, filepath: str) -> None:
        """
        Export permission rules to JSON file.
        
        Args:
            filepath: Path to save rules
        """
        rules_data = [
            {
                'resource_type': rule.resource_type.value,
                'pattern': rule.pattern,
                'action': rule.action.value,
                'description': rule.description
            }
            for rule in self.rules
        ]
        
        with open(filepath, 'w') as f:
            json.dump(rules_data, f, indent=2)
    
    def import_rules(self, filepath: str, append: bool = True) -> None:
        """
        Import permission rules from JSON file.
        
        Args:
            filepath: Path to rules file
            append: Whether to append to existing rules or replace
        """
        with open(filepath, 'r') as f:
            rules_data = json.load(f)
        
        if not append:
            self.rules = []
        
        for rule_dict in rules_data:
            self.add_rule_from_dict(rule_dict)
    
    def get_rules_for_resource(self, resource_type: ResourceType) -> List[Permission]:
        """
        Get all rules for a specific resource type.
        
        Args:
            resource_type: Resource type to filter by
        
        Returns:
            List of matching permissions
        """
        return [rule for rule in self.rules if rule.resource_type == resource_type]
    
    def clear_rules(self) -> None:
        """Clear all permission rules (except defaults)."""
        self.rules = []
        self._load_default_rules()


class ApprovalManager:
    """
    Manages user approval requests for operations.
    
    Tracks pending approvals and user responses.
    """
    
    def __init__(self, approval_timeout: int = 300):
        """
        Initialize approval manager.
        
        Args:
            approval_timeout: Timeout for approvals in seconds
        """
        self.approval_timeout = approval_timeout
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}
    
    def request_approval(
        self,
        operation_id: str,
        description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Request user approval for an operation.
        
        Args:
            operation_id: Unique ID for this operation
            description: Human-readable description
            context: Additional context information
        
        Returns:
            Approval request ID
        """
        self.pending_approvals[operation_id] = {
            'description': description,
            'context': context or {},
            'status': 'pending'
        }
        
        return operation_id
    
    def approve(self, operation_id: str) -> bool:
        """
        Approve an operation.
        
        Args:
            operation_id: Operation to approve
        
        Returns:
            True if approved successfully
        """
        if operation_id in self.pending_approvals:
            self.pending_approvals[operation_id]['status'] = 'approved'
            return True
        return False
    
    def deny(self, operation_id: str) -> bool:
        """
        Deny an operation.
        
        Args:
            operation_id: Operation to deny
        
        Returns:
            True if denied successfully
        """
        if operation_id in self.pending_approvals:
            self.pending_approvals[operation_id]['status'] = 'denied'
            return True
        return False
    
    def get_status(self, operation_id: str) -> Optional[str]:
        """
        Get approval status.
        
        Args:
            operation_id: Operation ID
        
        Returns:
            Status ('pending', 'approved', 'denied') or None
        """
        if operation_id in self.pending_approvals:
            return self.pending_approvals[operation_id]['status']
        return None
    
    def is_approved(self, operation_id: str) -> bool:
        """Check if operation is approved."""
        return self.get_status(operation_id) == 'approved'
    
    def is_denied(self, operation_id: str) -> bool:
        """Check if operation is denied."""
        return self.get_status(operation_id) == 'denied'
    
    def clear_approval(self, operation_id: str) -> None:
        """Clear an approval request."""
        if operation_id in self.pending_approvals:
            del self.pending_approvals[operation_id]
