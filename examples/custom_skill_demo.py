"""
Example of creating a custom skill for BeatBot.

This skill demonstrates:
1. Extending the base Skill class
2. Defining permission requirements
3. Implementing execution logic
4. Returning structured results
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from skills.base import Skill, SkillResult, SkillContext, SkillCategory
from security.permissions import Permission, ResourceType, PermissionAction


class GreetingSkill(Skill):
    """A simple skill that greets the user and reports the time."""
    
    # Metadata
    name = "greeting_skill"
    description = "Greets the user and tells them the current time"
    category = SkillCategory.CUSTOM
    version = "1.0.0"
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.default_greeting = self.config.get("default_greeting", "Hello")
        
    def get_required_permissions(self):
        """No special permissions needed for this skill."""
        return []

    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute the greeting logic."""
        from datetime import datetime
        
        user_name = context.parameters.get("name", "User")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"{self.default_greeting}, {user_name}! The current time is {current_time}."
        
        print(f"   [GreetingSkill] Executed for user: {context.user_id}")
        
        return SkillResult(
            success=True,
            data={"time": current_time, "greeting": message},
            message=message
        )


async def main():
    print("🤖 Demonstrating Custom Skill: GreetingSkill")
    
    # 1. Initialize skill
    skill = GreetingSkill(config={"default_greeting": "Greetings and Salutations"})
    print(f"   Initialized skill: {skill.name} (v{skill.version})")
    
    # 2. Create context
    context = SkillContext(
        user_id="demo_user",
        conversation_id="demo_conv_123",
        parameters={"name": "Alice"}
    )
    
    # 3. Execute
    print("   Executing skill...")
    result = await skill.execute(context)
    
    # 4. Show results
    if result.success:
        print(f"   ✅ Success: {result.message}")
        print(f"   Data: {result.data}")
    else:
        print(f"   ❌ Failed: {result.error}")

if __name__ == "__main__":
    asyncio.run(main())
