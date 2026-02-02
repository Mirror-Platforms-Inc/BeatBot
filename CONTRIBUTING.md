# Contributing to BeatBot

Thank you for your interest in contributing to BeatBot! This document provides guidelines for contributing.

## 🔒 Security First

BeatBot is a security-focused project. All contributions must maintain or improve the security posture. If you're unsure about security implications, ask before submitting.

## 🐛 Reporting Bugs

- Check existing issues first
- Use the bug report template
- Include steps to reproduce
- Specify your environment (OS, Python version, Docker version)
- **Never include credentials or sensitive data in issues**

## 💡 Suggesting Features

- Use the feature request template
- Explain the use case and benefits
- Consider security implications
- Discuss breaking changes

## 🔧 Pull Request Process

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Follow the code style:**
   - Use type hints
   - Add docstrings for public functions
   - Follow PEP 8
   - Keep functions focused and small

4. **Write tests:**
   - Add unit tests for new functionality
   - Ensure existing tests pass
   - Aim for >80% coverage on new code

5. **Update documentation:**
   - Update README if needed
   - Add docstrings
   - Update CHANGELOG.md

6. **Security review:**
   - Run security checks: `bandit -r .`
   - Check dependencies: `safety check`
   - Consider threat model

7. **Commit with clear messages:**
   ```
   feat: Add new permission rule type
   fix: Prevent sandbox escape via volume mount
   docs: Update configuration examples
   test: Add prompt injection test cases
   ```

8. **Submit PR:**
   - Reference related issues
   - Describe changes clearly
   - Wait for review

## 🧪 Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/beatbot.git
cd beatbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dev dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio bandit safety

# Run tests
pytest tests/

# Run security checks
bandit -r .
safety check
```

## 📝 Code Style

- **Type hints:** All functions should have type hints
- **Docstrings:** Use Google-style docstrings
- **Naming:** descriptive_names, not abbreviations
- **Imports:** Organize with isort
- **Format:** Use black for formatting (optional but recommended)

## ✅ Checklist Before Submitting

- [ ] Code follows project style guidelines
- [ ] Added/updated tests
- [ ] All tests pass locally
- [ ] Updated documentation
- [ ] No security vulnerabilities introduced
- [ ] No hardcoded credentials or secrets
- [ ] Commit messages are clear
- [ ] Updated CHANGELOG.md

## 🚫 What NOT to Contribute

- Code that weakens security
- Hardcoded credentials or API keys
- Undocumented breaking changes
- Code without tests (for new features)
- Copyrighted code you don't own
- Malicious code or backdoors

## 🤝 Code of Conduct

This project follows a Code of Conduct. By participating, you agree to uphold it.

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## ❓ Questions?

- Open a discussion on GitHub
- Check existing issues and PRs
- Read the documentation

## 🎉 Recognition

Contributors will be acknowledged in:
- CHANGELOG.md
- README.md (for significant contributions)
- GitHub's contributor graph

Thank you for making BeatBot better and safer! 🔒
