"""
Command and input validation to prevent injection attacks.

Implements multi-layer validation including prompt injection detection.
"""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ValidationLevel(str, Enum):
    """Validation strictness level."""
    STRICT = "strict"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"


@dataclass
class ValidationResult:
    """Result of validation check."""
    is_valid: bool
    reason: Optional[str] = None
    risk_level: str = "low"  # low, medium, high, critical


class CommandValidator:
    """
    Validates commands before execution to prevent injection attacks.
    """
    
    # Dangerous command patterns
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf",
        r"mkfs",
        r"dd\s+if=",
        r":\(\)\{.*\|.*&.*\}",  # Fork bomb
        r">\s*/dev/sd[a-z]",  # Write to disk device
        r"curl.*\|\s*bash",  # Pipe to shell
        r"wget.*\|\s*sh",
        r"nc\s+-e",  # Netcat backdoor
        r"chmod\s+777",
        r"chown\s+root",
    ]
    
    # Suspicious shell operators
    SUSPICIOUS_OPERATORS = [
        "&&", "||", ";", "|", ">", ">>", "<", "$(", "`"
    ]
    
    # Command whitelist for auto-approval
    SAFE_COMMANDS = {
        "ls", "pwd", "whoami", "date", "echo", "cat", "head", "tail",
        "grep", "find", "wc", "sort", "uniq", "diff"
    }
    
    def __init__(self, level: ValidationLevel = ValidationLevel.STRICT):
        """
        Initialize command validator.
        
        Args:
            level: Validation strictness level
        """
        self.level = level
    
    def validate_command(self, command: str, blacklist: Optional[List[str]] = None) -> ValidationResult:
        """
        Validate a command before execution.
        
        Args:
            command: Command to validate
            blacklist: Additional blacklisted patterns
        
        Returns:
            ValidationResult
        """
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return ValidationResult(
                    is_valid=False,
                    reason=f"Command matches dangerous pattern: {pattern}",
                    risk_level="critical"
                )
        
        # Check custom blacklist
        if blacklist:
            for pattern in blacklist:
                if pattern.lower() in command.lower():
                    return ValidationResult(
                        is_valid=False,
                        reason=f"Command contains blacklisted pattern: {pattern}",
                        risk_level="high"
                    )
        
        # Check for suspicious operators (strict mode)
        if self.level == ValidationLevel.STRICT:
            for op in self.SUSPICIOUS_OPERATORS:
                if op in command:
                    return ValidationResult(
                        is_valid=False,
                        reason=f"Command contains suspicious operator: {op}",
                        risk_level="medium"
                    )
        
        # Check command length (potential buffer overflow)
        if len(command) > 10000:
            return ValidationResult(
                is_valid=False,
                reason="Command exceeds maximum length",
                risk_level="medium"
            )
        
        return ValidationResult(is_valid=True)
    
    def is_safe_command(self, command: str) -> bool:
        """
        Check if command is in the safe whitelist.
        
        Args:
            command: Command to check
        
        Returns:
            True if command is safe for auto-approval
        """
        # Extract base command
        base_cmd = command.strip().split()[0] if command.strip() else ""
        return base_cmd in self.SAFE_COMMANDS
    
    def sanitize_command(self, command: str) -> str:
        """
        Sanitize a command by removing potentially dangerous elements.
        
        Args:
            command: Command to sanitize
        
        Returns:
            Sanitized command
        """
        # Remove null bytes
        sanitized = command.replace('\0', '')
        
        # Remove ANSI escape sequences
        sanitized = re.sub(r'\x1b\[[0-9;]*m', '', sanitized)
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        return sanitized


class PromptInjectionDetector:
    """
    Detects potential prompt injection attacks in user input.
    
    Uses pattern matching and heuristics to identify suspicious content.
    """
    
    # Patterns that might indicate prompt injection
    INJECTION_PATTERNS = [
        r"ignore\s+(previous|all|above)\s+(instructions|prompts|rules)",
        r"disregard\s+(your|the)\s+(instructions|programming|guidelines)",
        r"you\s+are\s+now\s+a\s+different",
        r"new\s+(instructions|role|personality)",
        r"system\s*:\s*",  # Fake system message
        r"assistant\s*:\s*",  # Fake assistant message
        r"___\s*END\s*___",
        r"STOP\s+EXECUTING",
        r"reveal\s+(your|the)\s+(system|prompt|instructions)",
        r"what\s+are\s+your\s+(instructions|rules)",
        r"\[SYSTEM\]",
        r"\[ADMIN\]",
    ]
    
    # Suspicious token sequences
    SUSPICIOUS_TOKENS = [
        "```system", "```instructions", "```ignore",
        "<!-- OVERRIDE -->", "<!-- SYSTEM -->",
    ]
    
    def detect_injection(self, user_input: str) -> ValidationResult:
        """
        Detect potential prompt injection in user input.
        
        Args:
            user_input: User-provided input to check
        
        Returns:
            ValidationResult
        """
        # Check for injection patterns
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                return ValidationResult(
                    is_valid=False,
                    reason=f"Potential prompt injection detected: matches pattern '{pattern}'",
                    risk_level="high"
                )
        
        # Check for suspicious tokens
        for token in self.SUSPICIOUS_TOKENS:
            if token.lower() in user_input.lower():
                return ValidationResult(
                    is_valid=False,
                    reason=f"Suspicious token detected: {token}",
                    risk_level="medium"
                )
        
        # Check for unusual repetition (might be attempting overflow)
        words = user_input.split()
        if len(words) > 10:
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            max_freq = max(word_freq.values())
            if max_freq > len(words) * 0.3:  # More than 30% repetition
                return ValidationResult(
                    is_valid=False,
                    reason="Unusual repetition detected",
                    risk_level="medium"
                )
        
        # Check for excessively long input
        if len(user_input) > 50000:
            return ValidationResult(
                is_valid=False,
                reason="Input exceeds maximum length",
                risk_level="low"
            )
        
        return ValidationResult(is_valid=True)
    
    def sanitize_input(self, user_input: str) -> str:
        """
        Sanitize user input by removing potentially harmful content.
        
        Args:
            user_input: Input to sanitize
        
        Returns:
            Sanitized input
        """
        # Remove null bytes
        sanitized = user_input.replace('\0', '')
        
        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Remove suspicious markdown code blocks
        sanitized = re.sub(r'```(system|instructions|ignore).*?```', '', sanitized, flags=re.DOTALL)
        
        # Trim
        sanitized = sanitized.strip()
        
        return sanitized


class OutputFilter:
    """
    Filters output to prevent credential and secret leakage.
    """
    
    # Patterns that look like secrets
    SECRET_PATTERNS = [
        (r'[A-Za-z0-9+/]{40,}', 'Base64-encoded secret'),
        (r'xox[baprs]-[0-9]{10,12}-[0-9]{10,12}-[A-Za-z0-9]{24,}', 'Slack token'),
        (r'ghp_[A-Za-z0-9]{36}', 'GitHub token'),
        (r'sk-[A-Za-z0-9]{48}', 'OpenAI API key'),
        (r'AIza[0-9A-Za-z_-]{35}', 'Google API key'),
        (r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', 'UUID/API key'),
        (r'-----BEGIN .* PRIVATE KEY-----', 'Private key'),
    ]
    
    def filter_secrets(self, text: str) -> Tuple[str, List[str]]:
        """
        Filter potential secrets from output.
        
        Args:
            text: Text to filter
        
        Returns:
            Tuple of (filtered_text, list_of_detected_secrets)
        """
        filtered = text
        detected_secrets = []
        
        for pattern, secret_type in self.SECRET_PATTERNS:
            matches = re.finditer(pattern, filtered)
            for match in matches:
                secret_value = match.group(0)
                detected_secrets.append(secret_type)
                # Replace with asterisks
                filtered = filtered.replace(secret_value, '*' * min(len(secret_value), 20))
        
        return filtered, detected_secrets
    
    def redact_patterns(self, text: str, patterns: List[str]) -> str:
        """
        Redact specific patterns from text.
        
        Args:
            text: Text to redact from
            patterns: Regex patterns to redact
        
        Returns:
            Redacted text
        """
        redacted = text
        for pattern in patterns:
            redacted = re.sub(pattern, '[REDACTED]', redacted)
        
        return redacted
