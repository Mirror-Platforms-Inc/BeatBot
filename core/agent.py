"""
Main agent orchestration engine.

Coordinates between model, memory, executor, and integrations.
"""

import asyncio
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime

from models.interface import ModelProvider, Message, MessageRole
from core.memory import MemoryManager
from core.executor import CommandExecutor, ExecutionContext
from storage.database import AuditLogger
from security.validator import PromptInjectionDetector


class Agent:
    """
    Main AI agent orchestration.
    
    Handles conversation flow, command execution, and self-prompting.
    """
    
    def __init__(
        self,
        model: ModelProvider,
        memory: MemoryManager,
        executor: CommandExecutor,
        audit_logger: AuditLogger,
        system_prompt: Optional[str] = None
    ):
        """
        Initialize agent.
        
        Args:
            model: Model provider
            memory: Memory manager
            executor: Command executor
            audit_logger: Audit logger
            system_prompt: System prompt for the agent
        """
        self.model = model
        self.memory = memory
        self.executor = executor
        self.audit = audit_logger
        self.injection_detector = PromptInjectionDetector()
        
        self.system_prompt = system_prompt or """You are BeatBot, a secure AI assistant with system-level access.

You can execute commands, manage files, and help users with various tasks.
When users request system operations, you should:
1. Explain what you're going to do
2. Request approval for potentially dangerous operations
3. Execute commands in a sandboxed environment
4. Report results clearly

Always prioritize security and user safety. If a command seems risky, explain why and ask for confirmation.

You have access to the following capabilities:
- Execute shell commands (in sandbox)
- Read and write files (with permissions)
- Search the web
- Manage schedules and reminders
- Send emails

Be helpful, secure, and transparent about your actions.

To execute a command, output a markdown code block with the language 'bash' or 'sh'.
Example:
I will list the files.
```bash
ls -la
```

To execute a skill, use the following XML format:
<call_skill>
{
  "name": "skill_name",
  "parameters": {
    "param1": "value1"
  }
}
</call_skill>

beatbot will execute the code and return the output.
"""
        self.current_user_id: Optional[str] = None
        self.max_autonomous_steps = 5  # Prevent infinite loops
        self.skill_manager = None

    def register_skill_manager(self, manager):
        """Register the skill manager."""
        self.skill_manager = manager
        
        # Update system prompt with available skills
        skills_info = "\nAvailable Skills:\n"
        for skill_meta in manager.list_skills():
            skills_info += f"- {skill_meta['name']}: {skill_meta['description']}\n"
            
        self.system_prompt += skills_info
    
    async def _get_default_system_prompt(self) -> str:
        """Get default system prompt."""
        return """You are BeatBot, a secure AI assistant with system-level access.

You can execute commands, manage files, and help users with various tasks.
When users request system operations, you should:
1. Explain what you're going to do
2. Request approval for potentially dangerous operations
3. Execute commands in a sandboxed environment
4. Report results clearly

Always prioritize security and user safety. If a command seems risky, explain why and ask for confirmation.

You have access to the following capabilities:
- Execute shell commands (in sandbox)
- Read and write files (with permissions)
- Search the web
- Manage schedules and reminders
- Send emails

Be helpful, secure, and transparent about your actions."""
    
    async def process_message(
        self,
        user_message: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        enable_autonomy: bool = True
    ) -> str:
        """
        Process a user message and generate response.
        
        Args:
            user_message: User's input
            user_id: User identifier
            conversation_id: Optional conversation ID
        
        Returns:
            Agent's response
        """
        # Check for prompt injection
        injection_check = self.injection_detector.detect_injection(user_message)
        if not injection_check.is_valid:
            self.audit.log(
                "prompt_injection_detected",
                f"Blocked: {injection_check.reason}",
                user_id=user_id,
                metadata={'message': user_message[:100]}
            )
            return f"⚠️ Security Warning: {injection_check.reason}. Message blocked for safety."
        
        # Start or continue conversation
        if not conversation_id:
            conversation_id = self.memory.start_conversation(user_id)
        else:
            self.memory.current_conversation_id = conversation_id
            self.memory.current_user_id = user_id
        
        self.current_user_id = user_id
        
        # Add user message to memory
        self.memory.add_message(MessageRole.USER, user_message)
        
        # Log interaction
        self.audit.log(
            "message_received",
            f"User message: {user_message[:50]}...",
            user_id=user_id,
            metadata={'conversation_id': conversation_id}
        )
        
        # Get conversation context
        context_messages = self.memory.get_context()
        
        # Add system prompt
        messages_with_system = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt)
        ] + context_messages
        
        try:
            # Generate response
            response = await self.model.generate(messages_with_system)
            
            # Add assistant response to memory
            self.memory.add_message(MessageRole.ASSISTANT, response.content)
            
            # Log response
            self.audit.log(
                "response_generated",
                f"Generated response ({response.usage['total_tokens']} tokens)",
                user_id=user_id,
                metadata={
                    'conversation_id': conversation_id,
                    'model': response.model,
                    'usage': response.usage
                }
            )
            
            # Check for commands in response
            if enable_autonomy:
                final_response = await self._autonomous_loop(
                    initial_response=response.content,
                    user_id=user_id,
                    conversation_id=conversation_id
                )
                return final_response
            
            return response.content
            
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            self.audit.log(
                "error",
                error_msg,
                user_id=user_id,
                metadata={'conversation_id': conversation_id}
            )
            return f"❌ {error_msg}"
    
    async def execute_command_from_string(
        self,
        command: str,
        user_id: str,
        require_approval: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a command and return results.
        
        Args:
            command: Command to execute
            user_id: User identifier
            require_approval: Whether to require user approval
        
        Returns:
            Dict with execution results
        """
        # Create execution context
        context = ExecutionContext(
            command=command,
            user_id=user_id,
            require_approval=require_approval,
            metadata=metadata
        )
        
        # Log command execution attempt
        self.audit.log(
            "command_execution_requested",
            f"Command: {command}",
            user_id=user_id,
            metadata={'require_approval': require_approval}
        )
        
        # Execute
        result = await self.executor.execute(context)
        
        # Log result
        self.audit.log(
            "command_executed",
            f"Exit code: {result.exit_code}",
            user_id=user_id,
            metadata={
                'command': command,
                'exit_code': result.exit_code,
                'timed_out': result.timed_out
            }
        )
        
        return {
            'success': result.exit_code == 0,
            'exit_code': result.exit_code,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'timed_out': result.timed_out,
            'error': result.error
        }
    
    async def stream_response(
        self,
        user_message: str,
        user_id: str,
        conversation_id: Optional[str] = None
    ):
        """
        Stream response tokens for real-time interaction.
        
        Args:
            user_message: User's input
            user_id: User identifier
            conversation_id: Optional conversation ID
        
        Yields:
            Response tokens
        """
        # Similar to process_message but with streaming
        if not conversation_id:
            conversation_id = self.memory.start_conversation(user_id)
        
        self.memory.add_message(MessageRole.USER, user_message)
        
        context_messages = self.memory.get_context()
        messages_with_system = [
            Message(role=MessageRole.SYSTEM, content=self.system_prompt)
        ] + context_messages
        
        full_response = ""
        
        async for token in self.model.stream(messages_with_system):
            full_response += token
            yield token
        
        # Save complete response
        self.memory.add_message(MessageRole.ASSISTANT, full_response)
    
    async def _autonomous_loop(
        self,
        initial_response: str,
        user_id: str,
        conversation_id: str
    ) -> str:
        """
        Run the autonomous thought-action-observation loop.
        """
        current_response = initial_response
        steps = 0
        
        while steps < self.max_autonomous_steps:
            # 1. Parse command or skill
            command = self._extract_command(current_response)
            skill_call = self._extract_skill_call(current_response)
            
            # If no command or skill, we're done
            if not command and not skill_call:
                return current_response
            
            steps += 1
            
            result_output = ""
            exit_code = 0
            
            if command:
                print(f"🔄 Autonomous Step {steps}: Executing command '{command}'")
                
                # 2a. Execute command
                result = await self.execute_command_from_string(
                    command, 
                    user_id, 
                    require_approval=True,
                    metadata={'conversation_id': conversation_id}
                )
                
                result_output = result['stdout'] + result['stderr']
                exit_code = result['exit_code']
                if result['error']:
                    result_output += f"\nError: {result['error']}"

            elif skill_call:
                print(f"🔄 Autonomous Step {steps}: Executing skill '{skill_call['name']}'")
                
                # 2b. Execute skill
                if self.skill_manager:
                    skill = self.skill_manager.get_skill(skill_call['name'])
                    if skill:
                        # Create context
                        from skills.base import SkillContext
                        context = SkillContext(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            parameters=skill_call['parameters']
                        )
                        
                        try:
                            # TODO: Permission check for skill?
                            # For now assuming skills check permissions internally or rely on underlying resources
                            skill_result = await skill.execute(context)
                            result_output = str(skill_result.data)
                            if not skill_result.success:
                                result_output = f"Skill Error: {skill_result.error}"
                        except Exception as e:
                            result_output = f"Skill Execution Exception: {str(e)}"
                            exit_code = 1
                    else:
                        result_output = f"Skill '{skill_call['name']}' not found."
                        exit_code = 1
                else:
                    result_output = "Skill Manager not initialized."
                    exit_code = 1
            
            # 3. Format observation
            observation = f"Action Result:\nExit Code: {exit_code}\nOutput:\n{result_output}"
            
            # 4. Add observation to memory
            self.memory.add_message(MessageRole.USER, f"System Action Result:\n{observation}")
            
            self.audit.log(
                "autonomous_step",
                f"Step {steps} complete",
                user_id=user_id,
                metadata={'command': command, 'exit_code': result['exit_code']}
            )
            
            # 5. Generate next thought
            context_messages = self.memory.get_context()
            messages_with_system = [
                Message(role=MessageRole.SYSTEM, content=self.system_prompt)
            ] + context_messages
            
            model_response = await self.model.generate(messages_with_system)
            current_response = model_response.content
            self.memory.add_message(MessageRole.ASSISTANT, current_response)
            
        return current_response

    def _extract_command(self, text: str) -> Optional[str]:
        """Extract bash command from markdown code block."""
        import re
        # Look for ```bash ... ``` or ```sh ... ```
        pattern = r"```(?:bash|sh)\n(.*?)\n```"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _extract_skill_call(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract skill call from XML block."""
        import re
        import json
        
        pattern = r"<call_skill>(.*?)</call_skill>"
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        return None

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get agent metrics.
        
        Returns:
            Dict with various metrics
        """
        model_metrics = self.model.get_metrics()
        
        return {
            'model': {
                'total_requests': model_metrics.total_requests,
                'total_tokens': model_metrics.total_tokens,
                'average_latency': model_metrics.average_latency,
                'error_count': model_metrics.error_count
            },
            'memory': {
                'current_conversation': self.memory.current_conversation_id,
                'context_window': self.memory.context_window
            }
        }
