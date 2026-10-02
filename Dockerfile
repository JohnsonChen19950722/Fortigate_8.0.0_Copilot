# Start with Python installed in a small Debian Linux image.
FROM python:3.13.15-slim-bookworm

# Copy a specific version of uv into the image.
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /usr/local/bin/uv

# Use /app as the working directory inside the image.
WORKDIR /app

# Show Python output promptly in container logs.
ENV PYTHONUNBUFFERED=1

# Copy project metadata and application source.
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install the application and its runtime dependencies.
RUN uv sync --locked --no-dev --python /usr/local/bin/python

# Run the installed startup command when a container starts.
CMD ["/app/.venv/bin/fortigate-8-0-0-copilot"]