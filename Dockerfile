# syntax=docker/dockerfile:1
FROM python:3.11-slim

# Install system dependencies for Playwright + Node.js
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x for frontend build
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency manifests first (layer caching)
COPY requirements.txt pyproject.toml package.json ./
COPY .tmp-build/package.json ./.tmp-build/package.json
RUN pip install --no-cache-dir -r requirements.txt
RUN npm install

# Copy source
COPY . .

# Install Playwright Chromium
RUN python -m playwright install chromium

# Build frontend (canonical flow from root package.json)
RUN npm run build

# Expose ports for API (8000) and TUI (8080)
EXPOSE 8000 8080

# Default: run API server
CMD ["python", "-m", "src.server"]
