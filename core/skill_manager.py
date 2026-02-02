
import importlib
import inspect
import os
import sys
from pathlib import Path
from typing import Dict, List, Type, Any

from skills.base import Skill, SkillCategory

class SkillManager:
    """
    Manages loading, registration, and access to skills.
    """
    
    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        
    def register_skill(self, skill: Skill):
        """Register a skill instance."""
        if skill.name in self.skills:
            print(f"Warning: Overwriting existing skill '{skill.name}'")
        self.skills[skill.name] = skill
        
    def get_skill(self, name: str) -> Skill:
        """Get a skill by name."""
        return self.skills.get(name)
        
    def list_skills(self) -> List[Dict[str, Any]]:
        """List all registered skills metadata."""
        return [skill.get_metadata() for skill in self.skills.values()]

    def load_from_directory(self, directory: str):
        """Load all skills from a directory."""
        path = Path(directory)
        if not path.exists():
            return
            
        sys.path.append(str(path.parent))
        
        for file in path.glob("*.py"):
            if file.name.startswith("_"):
                continue
                
            module_name = file.stem
            try:
                spec = importlib.util.spec_from_file_location(module_name, file)
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                
                # Find Skill subclasses
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, Skill) and 
                        obj != Skill):
                        
                        # Instantiate and register
                        try:
                            skill_instance = obj()
                            self.register_skill(skill_instance)
                            print(f"Loaded skill: {skill_instance.name}")
                        except Exception as e:
                            print(f"Failed to instantiate {name}: {e}")
                            
            except Exception as e:
                print(f"Error loading module {module_name}: {e}")
