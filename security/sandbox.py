"""
Docker-based command sandboxing for secure execution.

Addresses Moltbot's vulnerability of running commands directly on the host system.
"""

import asyncio
import docker
from docker.errors import DockerException, NotFound, APIError
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
import tempfile
import shutil


@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    enabled: bool = True
    timeout: int = 60
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    network_enabled: bool = False
    allowed_volume_mounts: List[str] = None
    
    def __post_init__(self):
        if self.allowed_volume_mounts is None:
            self.allowed_volume_mounts = []


@dataclass
class ExecutionResult:
    """Result of command execution."""
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False
    error: Optional[str] = None


class SandboxManager:
    """
    Manages Docker-based sandboxed command execution.
    
    Creates isolated containers for running potentially dangerous commands,
    with resource limits and network isolation.
    """
    
    SANDBOX_IMAGE = "beatbot-sandbox:latest"
    CONTAINER_NAME_PREFIX = "beatbot-sandbox-"
    
    def __init__(self, config: SandboxConfig):
        """
        Initialize sandbox manager.
        
        Args:
            config: Sandbox configuration
        """
        self.config = config
        self.docker_client = None
        self._sandbox_image_built = False
        
        if config.enabled:
            self._init_docker()
    
    def _init_docker(self) -> None:
        """Initialize Docker client."""
        try:
            self.docker_client = docker.from_env()
            # Test connection
            self.docker_client.ping()
        except DockerException as e:
            raise SandboxError(f"Failed to initialize Docker: {str(e)}")
    
    async def build_sandbox_image(self, force_rebuild: bool = False) -> None:
        """
        Build the sandbox Docker image.
        
        Args:
            force_rebuild: Force rebuild even if image exists
        """
        if not self.config.enabled:
            return
        
        # Check if image already exists
        if not force_rebuild and self._sandbox_image_built:
            try:
                self.docker_client.images.get(self.SANDBOX_IMAGE)
                return
            except NotFound:
                pass
        
        # Build minimal Alpine-based image
        dockerfile_content = """
FROM alpine:latest

# Install basic utilities
RUN apk add --no-cache \\
    bash \\
    coreutils \\
    python3 \\
    py3-pip \\
    curl \\
    git

# Create non-root user
RUN adduser -D -u 1000 sandboxuser

# Set working directory
WORKDIR /workspace

# Switch to non-root user
USER sandboxuser

CMD ["/bin/bash"]
"""
        
        # Create temporary directory for build context
        with tempfile.TemporaryDirectory() as build_dir:
            dockerfile_path = Path(build_dir) / "Dockerfile"
            dockerfile_path.write_text(dockerfile_content)
            
            try:
                # Build image
                self.docker_client.images.build(
                    path=build_dir,
                    tag=self.SANDBOX_IMAGE,
                    rm=True,
                    forcerm=True
                )
                self._sandbox_image_built = True
            except APIError as e:
                raise SandboxError(f"Failed to build sandbox image: {str(e)}")
    
    async def execute_command(
        self,
        command: str,
        working_dir: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """
        Execute a command in a sandboxed container.
        
        Args:
            command: Command to execute
            working_dir: Working directory inside container
            environment: Environment variables
            volumes: Volume mounts {host_path: container_path}
        
        Returns:
            ExecutionResult with command output
        """
        if not self.config.enabled:
            # Execute directly (unsafe, only for development)
            return await self._execute_direct(command)
        
        # Ensure sandbox image is built
        await self.build_sandbox_image()
        
        # Validate volume mounts
        if volumes:
            for host_path in volumes.keys():
                if not self._is_volume_allowed(host_path):
                    raise SandboxError(f"Volume mount not allowed: {host_path}")
        
        container = None
        try:
            # Create container
            container = self.docker_client.containers.create(
                image=self.SANDBOX_IMAGE,
                command=["bash", "-c", command],
                working_dir=working_dir or "/workspace",
                environment=environment or {},
                volumes=volumes or {},
                network_mode="none" if not self.config.network_enabled else "bridge",
                mem_limit=self.config.memory_limit,
                nano_cpus=int(self.config.cpu_limit * 1e9),
                detach=True,
                remove=False,  # We'll remove it manually
                user="sandboxuser",
            )
            
            # Start container
            container.start()
            
            # Wait for completion with timeout
            try:
                result = container.wait(timeout=self.config.timeout)
                exit_code = result['StatusCode']
                timed_out = False
            except Exception:
                # Timeout - kill container
                container.kill()
                exit_code = -1
                timed_out = True
            
            # Get logs
            logs = container.logs(stdout=True, stderr=True)
            logs_str = logs.decode('utf-8', errors='replace')
            
            # Split stdout and stderr (Docker combines them)
            # In practice, you'd need to capture them separately
            stdout = logs_str
            stderr = ""
            
            return ExecutionResult(
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                timed_out=timed_out
            )
            
        except DockerException as e:
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr="",
                error=f"Docker error: {str(e)}"
            )
        finally:
            # Clean up container
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
    
    async def _execute_direct(self, command: str) -> ExecutionResult:
        """
        Execute command directly without sandboxing.
        
        WARNING: Only use in development with mock_approvals!
        """
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.config.timeout
            )
            
            return ExecutionResult(
                exit_code=process.returncode,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                timed_out=False
            )
        except asyncio.TimeoutError:
            process.kill()
            return ExecutionResult(
                exit_code=-1,
                stdout="",
                stderr="",
                timed_out=True
            )
    
    def _is_volume_allowed(self, host_path: str) -> bool:
        """Check if a volume mount is allowed."""
        host_path = str(Path(host_path).resolve())
        
        for allowed_path in self.config.allowed_volume_mounts:
            allowed_path = str(Path(allowed_path).expanduser().resolve())
            if host_path.startswith(allowed_path):
                return True
        
        return False
    
    def cleanup_all_containers(self) -> int:
        """
        Clean up all sandbox containers.
        
        Returns:
            Number of containers removed
        """
        if not self.config.enabled:
            return 0
        
        count = 0
        try:
            containers = self.docker_client.containers.list(
                all=True,
                filters={"name": self.CONTAINER_NAME_PREFIX}
            )
            for container in containers:
                container.remove(force=True)
                count += 1
        except DockerException:
            pass
        
        return count


class SandboxError(Exception):
    """Raised when sandbox operations fail."""
    pass
