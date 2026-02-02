"""Example: Basic command execution with BeatBot"""

import asyncio
from config.settings import init_config
from security.sandbox import SandboxManager, SandboxConfig
from security.validator import CommandValidator, ValidationLevel
from security.permissions import PermissionManager, ApprovalManager
from core.executor import CommandExecutor, ExecutionContext


async def main():
    """Example of executing a command with full security."""
    
    # Initialize configuration
    init_config()
    
    # Setup security components
    sandbox_config = SandboxConfig(
        enabled=True,  # Enable sandboxing
        timeout=30,
        memory_limit="256m"
    )
    
    validator = CommandValidator(ValidationLevel.STRICT)
    permissions = PermissionManager()
    approvals = ApprovalManager()
    
    # Create executor
    executor = CommandExecutor(
        sandbox_config,
        validator,
        permissions,
        approvals
    )
    
    # Example 1: Validate a command without executing
    print("=" * 60)
    print("Example 1: Command Validation")
    print("=" * 60)
    
    test_command = "ls -la /tmp"
    validation = await executor.validate_only(test_command)
    
    print(f"\nCommand: {test_command}")
    print(f"Valid: {validation['is_valid']}")
    print(f"Permission: {validation['permission']}")
    print(f"Risk Level: {validation['risk_level']}")
    print(f"Needs Approval: {validation['needs_approval']}")
    
    # Example 2: Execute a safe command
    print("\n" + "=" * 60)
    print("Example 2: Safe Command Execution")
    print("=" * 60)
    
    context = ExecutionContext(
        command="echo 'Hello from BeatBot!'",
        user_id="example_user",
        require_approval=False  # Skip approval for demo
    )
    
    result = await executor.execute(context)
    
    print(f"\nCommand: {context.command}")
    print(f"Exit Code: {result.exit_code}")
    print(f"Output: {result.stdout}")
    
    # Example 3: Dangerous command (will be blocked)
    print("\n" + "=" * 60)
    print("Example 3: Dangerous Command (Blocked)")
    print("=" * 60)
    
    dangerous_context = ExecutionContext(
        command="rm -rf /important_files",
        user_id="example_user",
        require_approval=False
    )
    
    result = await executor.execute(dangerous_context)
    
    print(f"\nCommand: {dangerous_context.command}")
    print(f"Result: {result.error or 'Success'}")


if __name__ == "__main__":
    asyncio.run(main())
