# Security Policy

## 🔒 Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub issues.**

BeatBot is designed to be secure, but if you discover a vulnerability, we want to know about it so we can fix it promptly.

### How to Report

**Email:** security@beatbot.ai *(Configure this email for your deployment)*

Or use GitHub's private security advisory feature:
1. Go to the Security tab
2. Click "Report a vulnerability"
3. Fill out the form

### What to Include

- **Description** of the vulnerability
- **Steps to reproduce** the issue
- **Potential impact** (what an attacker could do)
- **Suggested fix** (if you have one)
- **Your contact information** (for follow-up)

### What to Expect

- **Acknowledgment** within 48 hours
- **Initial assessment** within 1 week
- **Regular updates** on progress
- **Credit** in the security advisory (if desired)

## 🛡️ Security Features

BeatBot includes multiple security layers:

- ✅ **Encrypted credential storage** (OS keyring + AES-256)
- ✅ **Docker-based sandboxing** for command execution
- ✅ **Prompt injection detection** and filtering
- ✅ **Granular permission system** with approval workflows
- ✅ **Tamper-evident audit logging** using hash chains
- ✅ **Secret output filtering** to prevent leakage
- ✅ **Rate limiting** to prevent abuse

## 🔍 Security Best Practices

When using BeatBot:

1. **Always use sandbox mode** (`sandbox_enabled: true`)
2. **Require approval for commands** (`require_approval: true`)
3. **Use strict validation level** (default setting)
4. **Limit allowed directories** to minimum needed
5. **Regularly audit logs** for suspicious activity
6. **Keep Docker updated** for sandbox security
7. **Use strong encryption keys** for database
8. **Don't disable security features** in production
9. **Review permission rules** periodically
10. **Monitor resource usage** for unusual patterns

## 📋 Security Checklist for Deployment

Before deploying BeatBot:

- [ ] Sandbox is enabled
- [ ] Approval is required for commands
- [ ] Allowed directories are minimal
- [ ] Dangerous commands are blacklisted
- [ ] Audit logging is enabled
- [ ] Database encryption is enabled
- [ ] Credentials are in keyring (not plaintext)
- [ ] Docker is installed and updated
- [ ] Rate limiting is configured
- [ ] Quiet hours are set (if using heartbeat)

## 🚨 Known Limitations

While BeatBot is designed with security in mind, be aware of:

1. **Sandbox escapes:** Docker provides strong isolation but is not perfect. Keep Docker updated.
2. **Model behavior:** LLMs can be unpredictable. Always review commands before approval.
3. **Prompt injection:** While we detect many patterns, new attack vectors may emerge.
4. **Resource exhaustion:** Malicious users could attempt DoS through excessive requests.
5. **Social engineering:** Users could be tricked into approving dangerous commands.

## 🔄 Security Updates

- Security patches are released as soon as possible
- Check releases regularly for updates
- Subscribe to GitHub security advisories
- Enable Dependabot alerts

## 📝 Disclosure Policy

- **30-day embargo** for critical vulnerabilities
- Public disclosure after patch is available
- Credit given to security researchers (with permission)
- Security advisories published on GitHub

## 🏆 Hall of Fame

Security researchers who responsibly disclose vulnerabilities will be listed here:

*No vulnerabilities reported yet*

## 📚 Security Resources

- [OWASP AI Security and Privacy Guide](https://owasp.org/www-project-ai-security-and-privacy-guide/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Prompt Injection Primer](https://github.com/HumanCompatibleAI/prompt-injection-links)

## ⚖️ Responsible Disclosure

We follow responsible disclosure practices and ask that you:

- Give us reasonable time to fix vulnerabilities
- Don't exploit vulnerabilities beyond proof-of-concept
- Don't access or modify other users' data
- Don't perform DoS attacks
- Act in good faith

Thank you for helping keep BeatBot and its users safe! 🔒
