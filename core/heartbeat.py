"""
Heartbeat scheduler for self-prompting behavior.

Allows the agent to initiate actions independently.
"""

import asyncio
from typing import Callable, Awaitable, List, Dict, Any, Optional
from datetime import datetime, time
from dataclasses import dataclass
from croniter import croniter


@dataclass
class HeartbeatTask:
    """A scheduled heartbeat task."""
    id: str
    name: str
    schedule: str  # Cron expression
    action: Callable[[], Awaitable[Any]]
    enabled: bool = True
    lastRun: Optional[datetime] = None


class HeartbeatScheduler:
    """
    Manages self-prompting heartbeat tasks.
    
    Allows the agent to execute periodic tasks like:
    - Checking for reminders
    - Sending daily briefings
    - Monitoring system conditions
    """
    
    def __init__(
        self,
        enabled: bool = True,
        quiet_hours_start: Optional[time] = None,
        quiet_hours_end: Optional[time] = None
    ):
        """
        Initialize heartbeat scheduler.
        
        Args:
            enabled: Whether heartbeat is enabled
            quiet_hours_start: Start of quiet hours (no self-prompting)
            quiet_hours_end: End of quiet hours
        """
        self.enabled = enabled
        self.quiet_hours_start = quiet_hours_start
        self.quiet_hours_end = quiet_hours_end
        
        self.tasks: List[HeartbeatTask] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    def add_task(
        self,
        task_id: str,
        name: str,
        schedule: str,
        action: Callable[[], Awaitable[Any]]
    ) -> None:
        """
        Add a heartbeat task.
        
        Args:
            task_id: Unique task identifier
            name: Human-readable name
            schedule: Cron expression (e.g., "0 9 * * *" for daily at 9 AM)
            action: Async function to execute
        """
        # Validate cron expression
        try:
            croniter(schedule)
        except Exception as e:
            raise ValueError(f"Invalid cron expression '{schedule}': {str(e)}")
        
        task = HeartbeatTask(
            id=task_id,
            name=name,
            schedule=schedule,
            action=action
        )
        
        self.tasks.append(task)
    
    def remove_task(self, task_id: str) -> bool:
        """
        Remove a heartbeat task.
        
        Args:
            task_id: Task to remove
        
        Returns:
            True if removed, False if not found
        """
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                self.tasks.pop(i)
                return True
        return False
    
    def _is_quiet_hours(self) -> bool:
        """Check if currently in quiet hours."""
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        now = datetime.now().time()
        
        # Handle quiet hours that span midnight
        if self.quiet_hours_start < self.quiet_hours_end:
            return self.quiet_hours_start <= now <= self.quiet_hours_end
        else:
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end
    
    async def _check_and_run_tasks(self) -> None:
        """Check all tasks and run those that are due."""
        if not self.enabled or self._is_quiet_hours():
            return
        
        now = datetime.now()
        
        for task in self.tasks:
            if not task.enabled:
                continue
            
            # Check if task should run
            cron = croniter(task.schedule, task.last_run or now)
            next_run = cron.get_next(datetime)
            
            if next_run <= now:
                try:
                    await task.action()
                    task.last_run = now
                except Exception as e:
                    # Log error but continue
                    print(f"Error executing heartbeat task '{task.name}': {str(e)}")
    
    async def _heartbeat_loop(self) -> None:
        """Main heartbeat loop."""
        while self._running:
            await self._check_and_run_tasks()
            # Check every minute
            await asyncio.sleep(60)
    
    def start(self) -> None:
        """Start the heartbeat scheduler."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
    
    async def stop(self) -> None:
        """Stop the heartbeat scheduler."""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
    
    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get all heartbeat tasks."""
        return [
            {
                'id': task.id,
                'name': task.name,
                'schedule': task.schedule,
                'enabled': task.enabled,
                'last_run': task.last_run.isoformat() if task.last_run else None
            }
            for task in self.tasks
        ]
