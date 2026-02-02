
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from core.agent import Agent
from models.interface import ModelResponse, MessageRole

@pytest.fixture
def mock_dependencies():
    model = MagicMock()
    model.generate = AsyncMock()
    model.get_metrics = MagicMock(return_value=MagicMock())
    
    memory = MagicMock()
    memory.get_context = MagicMock(return_value=[])
    
    executor = MagicMock()
    executor.execute = AsyncMock()
    
    audit = MagicMock()
    
    return model, memory, executor, audit

class TestAgentAutonomy:
    """Test the autonomous loop capabilities of the Agent."""

    def test_extract_command(self, mock_dependencies):
        model, memory, executor, audit = mock_dependencies
        agent = Agent(model, memory, executor, audit)
        
        # Test standard bash block
        text = "I will list files.\n```bash\nls -la\n```"
        cmd = agent._extract_command(text)
        assert cmd == "ls -la"
        
        # Test sh block
        text = "Executing script:\n```sh\n./script.sh\n```"
        cmd = agent._extract_command(text)
        assert cmd == "./script.sh"
        
        # Test no command
        text = "Just chatting here."
        cmd = agent._extract_command(text)
        assert cmd is None
        
        # Test multiple blocks (should take first? or specifically designed?)
        # Current regex takes first match
        text = "First:\n```bash\ncmd1\n```\nSecond:\n```bash\ncmd2\n```"
        cmd = agent._extract_command(text)
        assert cmd == "cmd1"

    @pytest.mark.asyncio
    async def test_autonomous_loop_execution(self, mock_dependencies):
        model, memory, executor, audit = mock_dependencies
        agent = Agent(model, memory, executor, audit)
        
        # Mock executor response
        executor.execute.return_value = MagicMock(
            exit_code=0, 
            stdout="file1.txt", 
            stderr="", 
            timed_out=False, 
            error=None
        )
        
        # Mock model response sequence
        # 1. loop starts with "initial_response" (containing a command)
        # 2. agent executes command, observes output
        # 3. agent prompts model with observation -> model returns "Task complete" (no command)
        model.generate.return_value = ModelResponse(
            content="Task complete.", 
            model="test", 
            usage={"total_tokens": 10},
            finish_reason="stop"
        )

        initial_response = "I need to check files.\n```bash\nls\n```"
        
        final_response = await agent._autonomous_loop(
            initial_response=initial_response,
            user_id="test_user",
            conversation_id="test_conv"
        )
        
        # Verify command was executed
        assert executor.execute.called
        call_args = executor.execute.call_args[0][0] # ExecutionContext
        assert call_args.command == "ls"
        
        # Verify loop terminated and returned final response
        assert final_response == "Task complete."
        
        # Verify memory was updated with system observation
        # We expect a call to add_message with USER role containing "System Action Result"
        calls = memory.add_message.call_args_list
        system_obs_call = [args for args in calls if "System Action Result" in args[0][1]]
        assert len(system_obs_call) > 0
