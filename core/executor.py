"""
Command executor with security integration.

Combines sandboxing, validation, and permission checks.
"""

import asyncio
import uuid
from typing import Optional, Dict, Any
from dataclasses import dataclass

from security.sandbox import SandboxManager, SandboxConfig, ExecutionResult
from security.validator import CommandValidator, ValidationLevel, OutputFilter
from security.permissions import PermissionManager, ApprovalManager, ResourceType, PermissionAction


@dataclass
class ExecutionContext:
    """Context for command execution."""
    command: str
    user_id: str
    sandbox_enabled: bool = True
    require_approval: bool = True
    working_dir: Optional[str] = None
    environment: Optional[Dict[str, str]] = None
    volumes: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class CommandExecutor:
    """
    Secure command executor that integrates all security features.
    
    Validates, checks permissions, requests approval, and executes
    commands in a sandboxed environment.
    """
    
    def __init__(
        self,
        sandbox_config: SandboxConfig,
        validator: CommandValidator,
        permission_manager: PermissionManager,
        approval_manager: ApprovalManager
    ):
        """
        Initialize command executor.
        
        Args:
            sandbox_config: Sandbox configuration
            validator: Command validator
            permission_manager: Permission manager
            approval_manager: Approval manager
        """
        self.sandbox = SandboxManager(sandbox_config)
        self.validator = validator
        self.permissions = permission_manager
        self.approvals = approval_manager
        self.output_filter = OutputFilter()
    
    async def execute(self, context: ExecutionContext) -> ExecutionResult:
        """
        Execute a command with full security checks.
        
        Args:
            context: Execution context
        
        Returns:
            ExecutionResult
        """
        # Step 1: Sanitize command
        command = self.validator.sanitize_command(context.command)
        
        # Step 2: Validate command
        validation = self.validator.validate_command(command)
        if not validation.is_valid:
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr="",
                error=f"Command validation failed: {validation.reason}"
            )
        
        # Step 3: Check permissions
        permission = self.permissions.check_permission(
            ResourceType.COMMAND,
            command,
            default_action=PermissionAction.ASK if context.require_approval else PermissionAction.ALLOW
        )
        
        if permission == PermissionAction.DENY:
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr="",
                error="Command denied by permission rules"
            )
        
        # Step 4: Request approval if needed
        if permission == PermissionAction.ASK and context.require_approval:
            approval_id = str(uuid.uuid4())
            self.approvals.request_approval(
                approval_id,
                description=f"Execute command: {command}",
                context={
                    'command': command, 
                    'user_id': context.user_id,
                    **(context.metadata or {})
                }
            )
            
            # Wait for approval (or timeout)
            approved = await self._wait_for_approval(approval_id)
            if not approved:
                return ExecutionResult(
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    error="Command execution not approved or timed out"
                )
        
        # Step 5: Execute command in sandbox
        result = await self.sandbox.execute_command(
            command=command,
            working_dir=context.working_dir,
            environment=context.environment,
            volumes=context.volumes
        )
        
        # Step 6: Filter output for secrets
        filtered_stdout, secrets = self.output_filter.filter_secrets(result.stdout)
        filtered_stderr, _ = self.output_filter.filter_secrets(result.stderr)
        
        return ExecutionResult(
            exit_code=result.exit_code,
            stdout=filtered_stdout,
            stderr=filtered_stderr,
            timed_out=result.timed_out,
            error=result.error
        )
    
    async def _wait_for_approval(self, approval_id: str) -> bool:
        """
        Wait for user approval.
        
        Args:
            approval_id: Approval request ID
        
        Returns:
            True if approved, False if denied or timeout
        """
        timeout = self.approvals.approval_timeout
        elapsed = 0
        poll_interval = 1  # Check every second
        
        while elapsed < timeout:
            status = self.approvals.get_status(approval_id)
            
            if status == 'approved':
                self.approvals.clear_approval(approval_id)
                return True
            elif status == 'denied':
                self.approvals.clear_approval(approval_id)
                return False
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        # Timeout
        self.approvals.clear_approval(approval_id)
        return False
    
    async def validate_only(self, command: str) -> Dict[str, Any]:
        """
        Validate a command without executing it.
        
        Args:
            command: Command to validate
        
        Returns:
            Dict with validation results
        """
        # Sanitize
        sanitized = self.validator.sanitize_command(command)
        
        # Validate
        validation = self.validator.validate_command(sanitized)
        
        # Check permissions
        permission = self.permissions.check_permission(
            ResourceType.COMMAND,
            sanitized
        )
        
        # Check if it's a safe command
        is_safe = self.validator.is_safe_command(sanitized)
        
        return {
            'original': command,
            'sanitized': sanitized,
            'is_valid': validation.is_valid,
            'validation_reason': validation.reason,
            'risk_level': validation.risk_level,
            'permission': permission.value,
            'is_safe': is_safe,
            'needs_approval': permission == PermissionAction.ASK
        }
