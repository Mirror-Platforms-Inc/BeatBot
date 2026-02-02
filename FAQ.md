# Frequently Asked Questions (FAQ)

## General Questions

### What is BeatBot?
BeatBot is a secure, open-source AI agent with system-level access. It's built as a safer alternative to Moltbot, addressing critical security vulnerabilities while maintaining powerful autonomous capabilities.

### How is BeatBot different from other AI agents?
- **Security-first design**: Multiple layers of protection (sandboxing, validation, encryption)
- **Model-agnostic**: Works with any open-source LLM (Ollama, LM Studio, etc.)
- **Interactive Approvals**: You control exactly what the bot does via Discord or Terminal.
- **Transparent**: Comprehensive audit logging and open-source code
- **Extensible**: Plugin system for custom capabilities
- **No vendor lock-in**: Your data stays local

### Is BeatBot free?
Yes! BeatBot is completely free and open-source under the MIT License. You can use, modify, and distribute it freely.

## Security Questions

### Is it safe to give an AI system-level access?
BeatBot implements multiple security layers to mitigate risks:
1. Commands run in isolated Docker containers
2. Dangerous operations require explicit approval (via interactive Discord buttons or console)
3. All actions are validated and logged
4. Credentials are encrypted (never plaintext)
5. Output is filtered for secrets

However, **no system is 100% secure**. Always review commands before approval and follow security best practices.

### How does the sandboxing work?
Every command executes in a minimal Alpine Linux Docker container that:
- Runs as a non-root user
- Has no host network access by default
- Has limited CPU and memory resources
- Uses temporary filesystems (destroyed after execution)
- Only sees explicitly mounted directories

### What if Docker has a vulnerability?
Docker vulnerabilities are rare and quickly patched. To minimize risk:
- Keep Docker updated to the latest version
- Use the strict security profile
- Limit allowed directories to minimum needed
- Monitor audit logs for suspicious activity

### Can the AI escape the sandbox?
BeatBot uses Docker for isolation, which is industry-standard. While no sandbox is perfect:
- Keep Docker updated
- Use resource limits (enabled by default)
- Don't disable security features
- Report any suspicious behavior

## Setup & Configuration

### What LLMs can I use?
Any LLM supported by LiteLLM (100+ providers):
- **Ollama**: llama3.2, mistral, qwen, gemma, etc.
- **LM Studio**: Any locally-hosted model
- **vLLM**: High-performance inference
- **Any OpenAI-compatible API**: Custom endpoints

### Do I need a GPU?
No, but it helps for faster local inference. You can:
- Use CPU-only models (smaller models like llama3.2:3b)
- Use cloud APIs (OpenRouter, Together.AI)
- Use remote Ollama instance

### How much disk space do I need?
- BeatBot itself: < 100 MB
- Docker images: ~500 MB
- LLM models: 2-20 GB depending on model size
- Database: Grows with conversation history

### Can I run this on Windows/Mac/Linux?
Yes! BeatBot works on all platforms with:
- Python 3.11+
- Docker Desktop (Windows/Mac) or Docker Engine (Linux)

## Usage Questions

### How do I approve commands?
When BeatBot wants to run a sensitive command, it will:
1. Explain what it wants to do
2. Show you the exact command
3. Wait for your explicit approval

You can pre-approve safe commands in the permission rules.

### Can BeatBot browse the web?
Browser automation (Playwright) support is planned but not yet implemented. Currently, BeatBot can make HTTP requests but can't interact with web pages.

### Can I connect BeatBot to Discord/Slack?
Discord integration is **fully supported**! You can run BeatBot as a server-side bot that responds to your commands and sends approval requests as interactive cards. See `DISCORD_SETUP.md`.
Slack integration is planned for a future release.

### How do I add custom skills?
```python
from skills.base import Skill, SkillResult

class MySkill(Skill):
    name = "my_skill"
    description = "What it does"
    
    async def execute(self, context):
        # Your code
        return SkillResult(success=True, data=result)
```

See `skills/builtin/system_info.py` for a complete example.

## Data & Privacy

### Where is my data stored?
All data is stored locally in an encrypted SQLite database:
- Location: `~/.beatbot/data/` (configurable)
- Encryption: SQLCipher/Fernet (AES)
- No cloud sync (unless you configure it)

### Are my conversations sent to the cloud?
Only if you use a cloud LLM provider. With Ollama or local models, **everything stays on your machine**.

### Can I delete my conversation history?
Yes! Use the memory manager:
```python
memory.delete_conversation(conversation_id)
```

Or manually delete conversations older than N days via config.

### How are my API keys stored?
API keys are stored in your OS keyring:
- **Windows**: Windows Credential Manager
- **macOS**: Keychain
- **Linux**: Secret Service (gnome-keyring)

They're encrypted and never stored in plaintext files.

## Troubleshooting

### "Docker socket permission denied"
**Linux:**
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

**Windows/Mac:** Ensure Docker Desktop is running.

### "SQLCipher import error"
Install system package:
```bash
# Ubuntu/Debian
sudo apt-get install sqlcipher libsqlcipher-dev

# macOS
brew install sqlcipher

# Then reinstall Python package
pip install sqlcipher3 --force-reinstall
```

### "Keyring backend not available"
**Linux:** Install gnome-keyring or use environment variables:
```bash
export BEATBOT_CREDENTIAL_DB_ENCRYPTION_KEY=your-key-here
```

### "Model connection timeout"
- Check if Ollama is running: `ollama list`
- Verify model is pulled: `ollama pull llama3.2`
- Check config model name matches exactly

### Commands are very slow
- Sandboxing adds ~1-2 second overhead
- For development, you can disable sandboxing (not recommended for production)
- Use local models to avoid network latency

## Performance

### How fast is it?
Response time depends on:
- **LLM**: Local models (2-10s), cloud APIs (1-5s)
- **Sandboxing**: +1-2s overhead per command
- **Hardware**: GPU vs CPU, RAM, disk speed

### Can I speed up command execution?
- Pre-approve safe commands (skips approval step)
- Use persistent Docker containers (WIP feature)
- Disable sandboxing for development only

### How much memory does it use?
- **Base**: ~100-200 MB
- **With LLM loaded**: +2-8 GB (model dependent)
- **Sandboxes**: ~50 MB each while running

## Contributing

### How can I contribute?
See [CONTRIBUTING.md](CONTRIBUTING.md). We welcome:
- Bug reports and fixes
- Security improvements
- New skills/plugins
- Documentation improvements
- Platform integrations

### I found a security vulnerability
Please report it responsibly via [SECURITY.md](SECURITY.md). **Do not** create public issues for security vulnerabilities.

### Can I use this commercially?
Yes! MIT License allows commercial use. Attribution appreciated but not required.

## Comparison

### BeatBot vs ChatGPT
- ChatGPT: Cloud-based, can't execute commands on your system
- BeatBot: Local, has system access, works with any model

### BeatBot vs Moltbot
See the comparison table in [README.md](README.md#-comparison-with-moltbot). TL;DR: BeatBot addresses all major security vulnerabilities in Moltbot.

### BeatBot vs AutoGPT
- AutoGPT: Runs commands directly on host, vendor-locked to OpenAI
- BeatBot: Sandboxed execution, model-agnostic, security-focused, remote management via Discord.

## Getting Help

- **Documentation**: [README.md](README.md), [ARCHITECTURE.md](ARCHITECTURE.md)
- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/BeatBot/issues)
- **Security**: [SECURITY.md](SECURITY.md)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Didn't find your answer?** [Open an issue](https://github.com/YOUR_USERNAME/BeatBot/issues/new) or start a [discussion](https://github.com/YOUR_USERNAME/BeatBot/discussions).
