# Architecture Overview

This document describes the internal architecture of BeatBot.

## System Architecture

```
┌─────────────────────────────────────────────────┐
│                                                 │
│              User Interface Layer               │
│     (Console, Discord, Slack, Web UI)          │
│                                                 │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│                                                 │
│            Agent Orchestration                  │
│  ┌──────────────────────────────────────────┐  │
│  │  - Message Processing                    │  │
│  │  - Context Management                    │  │
│  │  - Prompt Injection Detection            │  │
│  │  - Response Generation                   │  │
│  └──────────────────────────────────────────┘  │
│                                                 │
└─────┬──────────────────────────┬────────────────┘
      │                          │
      │                          │
┌─────▼──────────┐      ┌────────▼────────────────┐
│                │      │                         │
│  Model Layer   │      │    Executor Layer       │
│                │      │                         │
│  ┌──────────┐ │      │  ┌──────────────────┐  │
│  │ LiteLLM  │ │      │  │   Validation     │  │
│  │ Provider │ │      │  │   + Permissions  │  │
│  └──────────┘ │      │  └────────┬─────────┘  │
│                │      │           │             │
│  ┌──────────┐ │      │  ┌────────▼─────────┐  │
│  │  Ollama  │ │      │  │  Docker Sandbox  │  │
│  │ Provider │ │      │  │  + Output Filter │  │
│  └──────────┘ │      │  └──────────────────┘  │
│                │      │                         │
└────────────────┘      └─────────────────────────┘
         │                         │
         │                         │
         └──────────┬──────────────┘
                    │
         ┌──────────▼──────────┐
         │                     │
         │   Storage Layer     │
         │                     │
         │  ┌───────────────┐ │
         │  │  Encrypted DB │ │
         │  │  (SQLCipher)  │ │
         │  └───────────────┘ │
         │                     │
         │  ┌───────────────┐ │
         │  │  Audit Logger │ │
         │  │ (Hash Chain)  │ │
         │  └───────────────┘ │
         │                     │
         │  ┌───────────────┐ │
         │  │  Credentials  │ │
         │  │  (OS Keyring) │ │
         │  └───────────────┘ │
         │                     │
         └─────────────────────┘
```

## Component

s

### 1. User Interface Layer
- **Console Interface**: Interactive terminal mode
- **Discord Bot**: Secure remote operations with interactive approvals
- **Future**: Slack integration, Web UI dashboard

### 2. Agent Orchestration (`core/agent.py`)
Coordinates all components:
- Receives user messages
- Detects prompt injection
- Manages conversation context
- Generates responses via model
- Executes commands through executor
- Logs all actions

### 3. Model Layer (`models/`)
Model-agnostic interface:
- **Abstract Interface**: Defines common API
- **LiteLLM Provider**: Supports 100+ models
- **Ollama Provider**: Direct Ollama integration
- Fallback chains for reliability
- Metrics tracking

### 4. Executor Layer (`core/executor.py`, `security/`)
Secure command execution pipeline:
1. **Sanitization**: Remove null bytes, trim whitespace
2. **Validation**: Check against dangerous patterns
3. **Permission Check**: Rule-based access control
4. **Approval**: User confirmation (if needed)
5. **Sandbox Execution**: Run in Docker container
6. **Output Filtering**: Remove secrets from output

### 5. Security Components (`security/`)
- **Validator**: Command and prompt validation
- **Permissions**: Granular access control
- **Sandbox**: Docker-based isolation
- **Credentials**: OS keyring storage

### 6. Storage Layer (`storage/`)
- **Database**: Encrypted SQLite with SQLCipher
- **Audit Logger**: Tamper-evident hash chains
- **Memory Manager**: Context and conversation history

### 7. Skills System (`skills/`)
- **Base Interface**: Extensible capability framework
- **Built-in Skills**: System info, file ops, etc.
- **Custom Skills**: User-defined extensions

## Data Flow

### User Message Processing

```
User Input
    ↓
Prompt Injection Detection
    ↓
Add to Conversation History
    ↓
Get Context from Memory
    ↓
Generate Response (Model)
    ↓
Save Response to Memory
    ↓
Return to User
```

### Command Execution

```
Command Request
    ↓
Sanitize Input
    ↓
Validate Command
    ↓
Check Permissions
    ↓
Request Approval (if needed)
    ↓
Execute in Docker Sandbox
    ↓
Filter Output for Secrets
    ↓
Log to Audit Trail
    ↓
Return Result
```

BeatBot implements defense in depth with 6 layers:

1. **Input Layer**: Prompt injection detection, sanitization
2. **Authorization Layer**: Permission checks, approval workflows
3. **Validation Layer**: Command validation, parameter checking
4. **Execution Layer**: Sandboxed containers, resource limits
5. **Output Layer**: Secret filtering, output sanitization
6. **Audit Layer**: Comprehensive logging, tamper detection

## Extensibility

### Adding a New Skill

```python
from skills.base import Skill, SkillResult, SkillContext

class MySkill(Skill):
    name = "my_skill"
    description = "What it does"
    
    async def execute(self, context: SkillContext) -> SkillResult:
        # Implementation
        return SkillResult(success=True, data=result)
```

### Adding a New Model Provider

```python
from models.interface import ModelProvider, ModelResponse

class MyProvider(ModelProvider):
    async def generate(self, messages, **kwargs) -> ModelResponse:
        # Implementation
        pass
```

## Configuration

Configuration is layered:
1. Default config (`config/default_config.yaml`)
2. Environment variables (override defaults)
3. Profile-specific settings (dev, production)

## Deployment Options

1. **Docker Compose**: Full stack with Ollama
2. **Standalone Docker**: Single container
3. **Local Python**: Development mode
4. **Kubernetes**: Production orchestration (future)

## Performance Considerations

- **Async/await**: Non-blocking I/O throughout
- **Connection pooling**: Database connections
- **Context window**: Configurable message history
- **Resource limits**: Sandbox CPU/memory caps
- **Caching**: Model response caching (future)

## Security Considerations

- **Minimal privileges**: Sandbox runs as non-root
- **Network isolation**: Sandboxes have no network by default
- **Encrypted storage**: All data at rest encrypted
- **Secure defaults**: Strict mode enabled
- **Audit trail**: All actions logged with hash chain
