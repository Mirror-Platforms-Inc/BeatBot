
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import random

# Import base classes (adjust path if running inside project structure)
from skills.base import Skill, SkillResult, SkillContext, SkillCategory
from security.permissions import Permission, ResourceType, PermissionAction

class CalendarSkill(Skill):
    """
    A skill to manage calendar events (mock implementation).
    """
    
    name = "calendar"
    description = "Manage calendar events (list, add, delete)"
    category = SkillCategory.PRODUCTIVITY
    version = "1.0.0"
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        # Mock database of events
        self.events = [
            {"id": "evt_1", "title": "Team Standup", "time": "2023-10-27 10:00:00", "duration": 30},
            {"id": "evt_2", "title": "Client Meeting", "time": "2023-10-27 14:00:00", "duration": 60},
        ]
        
    def get_required_permissions(self) -> List[Permission]:
        # Example: if this used a real API, we might need NETWORK permissions
        return []

    async def execute(self, context: SkillContext) -> SkillResult:
        """
        Execute calendar operations.
        
        Parameters:
            action: "list", "add", "delete"
            title: (for add) Event title
            time: (for add) Event time
            event_id: (for delete) Event ID
        """
        action = context.parameters.get("action")
        
        if action == "list":
            return self._list_events()
        elif action == "add":
            return self._add_event(context.parameters)
        elif action == "delete":
            return self._delete_event(context.parameters)
        else:
            return SkillResult(
                success=False, 
                data=None, 
                error=f"Unknown action: {action}. Supported: list, add, delete"
            )

    def _list_events(self) -> SkillResult:
        return SkillResult(
            success=True,
            data=self.events,
            message=f"Found {len(self.events)} events."
        )

    def _add_event(self, params: Dict[str, Any]) -> SkillResult:
        title = params.get("title")
        time_str = params.get("time") # e.g. "2023-10-28 10:00"
        
        if not title or not time_str:
            return SkillResult(success=False, data=None, error="Missing 'title' or 'time'")
            
        new_event = {
            "id": f"evt_{random.randint(1000,9999)}",
            "title": title,
            "time": time_str,
            "duration": params.get("duration", 60)
        }
        self.events.append(new_event)
        
        return SkillResult(
            success=True,
            data=new_event,
            message=f"Added event '{title}' at {time_str}"
        )

    def _delete_event(self, params: Dict[str, Any]) -> SkillResult:
        event_id = params.get("event_id")
        if not event_id:
            return SkillResult(success=False, data=None, error="Missing 'event_id'")
            
        initial_len = len(self.events)
        self.events = [e for e in self.events if e["id"] != event_id]
        
        if len(self.events) < initial_len:
            return SkillResult(success=True, data=None, message=f"Deleted event {event_id}")
        else:
            return SkillResult(success=False, data=None, error=f"Event {event_id} not found")
