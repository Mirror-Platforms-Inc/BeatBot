# How to Create Custom Skills for BeatBot

BeatBot's power comes from its extensibility. This guide will walk you through creating a **Calendar Skill** to let the bot manage your schedule.

## 1. The Skill Structure
All skills live in `~/.beatbot/custom_skills/` (default). A skill is a Python file that defines a subclass of `Skill`.

Here is the basic template:

```python
from skills.base import Skill, SkillResult, SkillContext, SkillCategory

class MySkill(Skill):
    name = "my_skill"
    description = "Does something useful"
    category = SkillCategory.CUSTOM
    
    async def execute(self, context: SkillContext) -> SkillResult:
        # Your logic here
        result = "Success!"
        return SkillResult(True, data=result)
```

## 2. Example: Calendar Manager
We've provided a full example in `examples/calendar_skill.py`. To install it:

1.  Create the directory:
    ```bash
    mkdir -p ~/.beatbot/custom_skills
    ```
2.  Copy the example:
    ```bash
    cp examples/calendar_skill.py ~/.beatbot/custom_skills/
    ```
3.  Restart BeatBot.

## 3. Using the Skill
Once loaded, tell BeatBot:
> "Add an event to my calendar for 'Team Lunch' at 12pm tomorrow."

BeatBot will recognize the intent and call the skill autonomously:
```xml
<call_skill>
{
  "name": "calendar",
  "parameters": {
    "action": "add",
    "title": "Team Lunch",
    "time": "tomorrow 12pm"
  }
}
</call_skill>
```

## 4. Connecting to Real APIs (Google Calendar)
To make this real, you'll need to use the Google Calendar API.

1.  **Install Library**: `pip install google-api-python-client google-auth-oauthlib`
2.  **Get Credentials**: Go to Google Cloud Console -> Create Project -> Enable Calendar API -> Create OAuth Client ID -> Download `credentials.json`.
3.  **Update verify `execute` method**:
    ```python
    def _get_service(self):
        # Load credentials from file or keyring
        creds = ... 
        return build('calendar', 'v3', credentials=creds)

    async def execute(self, context):
        service = self._get_service()
        if action == "add":
            event = service.events().insert(...).execute()
    ```

## 5. Testing
You can test skills in **Interactive Mode** before deploying to Discord:
```bash
python main.py --mode interactive
```
Then type:
```
> List my calendar events
```
You should see:
```
Executing skill 'calendar'...
Found 2 events: Team Standup...
```
