# Minimal Alpine-based sandbox container for BeatBot command execution
FROM alpine:latest

# Install basic utilities
RUN apk add --no-cache \
    bash \
    coreutils \
    python3 \
    py3-pip \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/cache/apk/*

# Create non-root user for sandbox
RUN adduser -D -u 1000 -s /bin/bash sandboxuser

# Set working directory
WORKDIR /workspace

# Ensure proper permissions
RUN chown -R sandboxuser:sandboxuser /workspace

# Switch to non-root user
USER sandboxuser

# Default command
CMD ["/bin/bash"]
