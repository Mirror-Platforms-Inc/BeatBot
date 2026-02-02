"""
System Information skill - Get system stats and info.
"""

import platform
import psutil
from typing import Dict, Any
from datetime import datetime

from skills.base import Skill, SkillResult, SkillContext, SkillCategory
from security.permissions import Permission, ResourceType, PermissionAction


class SystemInfoSkill(Skill):
    """Get system information like CPU, memory, disk usage."""
    
    name = "system_info"
    description = "Get system statistics (CPU, memory, disk, network)"
    category = SkillCategory.SYSTEM
    version = "1.0.0"
    
    # No dangerous permissions needed for read-only system info
    required_permissions = [
        Permission(
            resource_type=ResourceType.COMMAND,
            pattern="psutil.*",
            action=PermissionAction.ALLOW,
            description="Allow reading system information"
        )
    ]
    
    async def execute(self, context: SkillContext) -> SkillResult:
        """Get system information."""
        try:
            info_type = context.parameters.get('type', 'all')
            
            if info_type == 'cpu' or info_type == 'all':
                cpu_info = self._get_cpu_info()
            else:
                cpu_info = None
            
            if info_type == 'memory' or info_type == 'all':
                memory_info = self._get_memory_info()
            else:
                memory_info = None
            
            if info_type == 'disk' or info_type == 'all':
                disk_info = self._get_disk_info()
            else:
                disk_info = None
            
            if info_type == 'platform' or info_type == 'all':
                platform_info = self._get_platform_info()
            else:
                platform_info = None
            
            result_data = {
                'timestamp': datetime.now().isoformat(),
                'cpu': cpu_info,
                'memory': memory_info,
                'disk': disk_info,
                'platform': platform_info
            }
            
            # Remove None values
            result_data = {k: v for k, v in result_data.items() if v is not None}
            
            return SkillResult(
                success=True,
                data=result_data,
                message=f"Retrieved {info_type} information"
            )
            
        except Exception as e:
            return SkillResult(
                success=False,
                data=None,
                error=f"Failed to get system info: {str(e)}"
            )
    
    def _get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU information."""
        return {
            'percent': psutil.cpu_percent(interval=1),
            'count': psutil.cpu_count(),
            'count_logical': psutil.cpu_count(logical=True),
            'frequency': psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
        }
    
    def _get_memory_info(self) -> Dict[str, Any]:
        """Get memory information."""
        mem = psutil.virtual_memory()
        return {
            'total_gb': round(mem.total / (1024**3), 2),
            'available_gb': round(mem.available / (1024**3), 2),
            'used_gb': round(mem.used / (1024**3), 2),
            'percent': mem.percent
        }
    
    def _get_disk_info(self) -> Dict[str, Any]:
        """Get disk information."""
        disk = psutil.disk_usage('/')
        return {
            'total_gb': round(disk.total / (1024**3), 2),
            'used_gb': round(disk.used / (1024**3), 2),
            'free_gb': round(disk.free / (1024**3), 2),
            'percent': disk.percent
        }
    
    def _get_platform_info(self) -> Dict[str, Any]:
        """Get platform information."""
        return {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version()
        }
