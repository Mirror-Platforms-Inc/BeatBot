# Changelog

All notable changes to BeatBot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial release of BeatBot
- Model-agnostic LLM interface with LiteLLM support
- Docker-based command sandboxing
- OS keyring credential storage with AES-256 encryption
- Multi-layer validation (command patterns + prompt injection detection)
- Granular permission system with approval workflows
- Tamper-evident audit logging using hash chains
- Encrypted SQLite storage for conversations
- Persistent memory with context management
- Self-prompting heartbeat scheduler with cron support
- Interactive console mode
- Configuration system with YAML and environment variables
- Secret output filtering
- Rate limiting support

### Security
- All commands execute in isolated Docker containers by default
- Credentials stored in OS keyring (never plaintext)
- Prompt injection detection and blocking
- Command validation against dangerous patterns
- Comprehensive audit trail with hash chain verification
- Output filtering to prevent credential leakage

## [0.1.0] - 2026-01-31

### Added
- Initial alpha release
- Core security features implemented
- Basic documentation and examples

---

## Release Notes

### Version 0.1.0 - Alpha Release

**⚠️ This is an alpha release. While security has been a primary focus, please use with caution and report any issues.**

**Key Features:**
- 🔒 Security-first design with multiple protection layers
- 🤖 Works with any open-source LLM (Ollama, LM Studio, etc.)
- 🐳 Sandboxed execution in Docker containers
- 💾 Encrypted storage for conversations and credentials
- 📝 Comprehensive audit logging

**Known Limitations:**
- Messaging platform integrations (Discord, Slack) not yet implemented
- Browser automation not yet available
- No web UI (console only)
- Limited test coverage

**What's Next:**
- Discord/Slack integration
- Plugin system for custom skills
- Web UI dashboard
- Comprehensive test suite
- Performance optimizations

**Security Notice:**
This project aims to provide secure AI agent functionality. However, no system is 100% secure. Always:
- Review commands before approval
- Use sandbox mode in production
- Monitor audit logs regularly
- Keep Docker and dependencies updated
