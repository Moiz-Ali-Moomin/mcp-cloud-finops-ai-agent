# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and README.md
COPY pyproject.toml README.md ./

# Copy the package source
COPY opsyield/ ./opsyield/

# Install the package
RUN pip install --no-cache-dir .

# Expose the API port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the API server
CMD ["uvicorn", "opsyield.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
