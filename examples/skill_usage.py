"""
Example: Using BeatBot with custom skills.
"""

import asyncio
from skills.builtin.system_info import SystemInfoSkill
from skills.base import SkillContext


async def main():
    """Demonstrate skill usage."""
    
    print("=" * 60)
    print("BeatBot Skills Example")
    print("=" * 60)
    
    # Create skill instance
    system_skill = SystemInfoSkill()
    
    # Display skill metadata
    metadata = system_skill.get_metadata()
    print(f"\nSkill: {metadata['name']}")
    print(f"Description: {metadata['description']}")
    print(f"Category: {metadata['category']}")
    print(f"Version: {metadata['version']}")
    
    # Execute skill - Get all system info
    context = SkillContext(
        user_id="demo_user",
        conversation_id="demo_conv",
        parameters={'type': 'all'}
    )
    
    print("\n" + "=" * 60)
    print("Getting System Information...")
    print("=" * 60)
    
    result = await system_skill.execute(context)
    
    if result.success:
        print("\n✅ Success!")
        print(f"\nMessage: {result.message}")
        print("\nData:")
        
        # Pretty print results
        for category, info in result.data.items():
            if category == 'timestamp':
                print(f"\n⏰ {category.upper()}: {info}")
            elif info:
                print(f"\n📊 {category.upper()}:")
                for key, value in info.items():
                    print(f"  {key}: {value}")
    else:
        print(f"\n❌ Error: {result.error}")
    
    # Example: Get only CPU info
    print("\n" + "=" * 60)
    print("Getting Only CPU Information...")
    print("=" * 60)
    
    cpu_context = SkillContext(
        user_id="demo_user",
        conversation_id="demo_conv",
        parameters={'type': 'cpu'}
    )
    
    cpu_result = await system_skill.execute(cpu_context)
    
    if cpu_result.success:
        print("\n✅ CPU Information:")
        for key, value in cpu_result.data['cpu'].items():
            print(f"  {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
