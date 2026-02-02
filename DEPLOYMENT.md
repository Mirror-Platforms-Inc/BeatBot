# Quick Deployment Guide

## Option 1: Docker Compose (Recommended)

The easiest way to run BeatBot with Ollama:

```bash
# Pull and start services
docker-compose up -d

# Pull a model in Ollama
docker-compose exec ollama ollama pull llama3.2

# Attach to BeatBot
docker-compose exec beatbot python main.py --mode interactive
```

## Option 2: Local Python

For development:

```bash
# Install dependencies
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Install Docker for sandboxing
# Download from: https://www.docker.com/

# Build sandbox image
docker build -f docker/sandbox/Dockerfile -t beatbot-sandbox:latest docker/sandbox/

# Install Ollama (optional, for LLMs)
# Download from: https://ollama.ai
ollama pull llama3.2

# Run BeatBot
python main.py --mode interactive
```

## Option 3: Standalone Docker

Run BeatBot in a container:

```bash
# Build image
docker build -t beatbot:latest .

# Run with Docker socket mounted
docker run -it --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v beatbot-data:/data \
  -e BEATBOT_MODEL_DEFAULT=ollama/llama3.2 \
  beatbot:latest
```

## Option 4: Discord Deployment
For 24/7 remote operation:
1. Set up your Discord Bot Token in `DISCORD_SETUP.md`.
2. Run in a persistent session (using `tmux`, `screen`, or a systemd service):
```bash
python main.py --mode discord
```

## Configuration

Edit `config/default_config.yaml` or use environment variables:

```bash
export BEATBOT_MODEL_PROVIDER=litellm
export BEATBOT_MODEL_DEFAULT=ollama/llama3.2
export BEATBOT_SANDBOX_ENABLED=true
export BEATBOT_REQUIRE_APPROVAL=true
```

## Security Checklist

Before production deployment:

- [ ] Sandbox is enabled
- [ ] Approval required for commands
- [ ] Allowed directories are minimal
- [ ] Database encryption is enabled
- [ ] Credentials in OS keyring (not config)
- [ ] Docker is updated
- [ ] Audit logging enabled
- [ ] Rate limiting configured

## Troubleshooting

**Docker socket permission denied:**
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

**SQLCipher import error:**
```bash
# Install system package
sudo apt-get install sqlcipher libsqlcipher-dev  # Ubuntu/Debian
brew install sqlcipher  # macOS
```

**Keyring backend not available:**
```bash
# Linux: Install gnome-keyring or use environment variables
export BEATBOT_CREDENTIAL_DB_ENCRYPTION_KEY=your-key-here
```

## Production Recommendations

1. **Use secrets management**: Store credentials in proper secret management (not env vars)
2. **Set resource limits**: Configure Docker limits in production
3. **Monitor logs**: Set up log aggregation and monitoring
4. **Regular updates**: Keep Docker images and dependencies updated
5. **Backup data**: Regular backups of `/data` volume
6. **Network isolation**: Run in isolated network if possible

## Getting Help

- [Documentation](README.md)
- [Security Policy](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [GitHub Issues](https://github.com/YOUR_USERNAME/BeatBot/issues)
