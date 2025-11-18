FROM node:24.8.0-bookworm

# Ensure the requested npm version is available.
RUN npm install -g npm@11.6.0

# Install Python 3.11, venv tooling, and pip.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3.11 \
      python3.11-venv \
      python3-pip \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pre-copy manifests so Docker can cache dependency installation.
COPY package*.json ./
COPY mcp-security-demo/frontend/package*.json ./mcp-security-demo/frontend/
COPY mcp-security-demo/backend/requirements.txt ./mcp-security-demo/backend/requirements.txt

# Pull the rest of the source.
COPY . .

# Install Node dependencies for the orchestrator and frontend.
RUN npm install \
 && npm install --prefix mcp-security-demo/frontend

# Set up the backend virtualenv and install Python dependencies.
RUN cd mcp-security-demo/backend \
 && python3.11 -m venv .venv \
 && . .venv/bin/activate \
 && pip install --upgrade pip \
 && pip install -r requirements.txt

# Ensure the orchestrator can find the virtualenv interpreter.
ENV PATH="/app/mcp-security-demo/backend/.venv/bin:${PATH}"

# Bind to all interfaces and expose the proxy on port 80 (fronting the 5173 dev server).
ENV CHILD_HOST=127.0.0.1 \
    PROXY_HOST=0.0.0.0 \
    BACKEND_PORT=8001 \
    FRONTEND_PORT=5174 \
    PROXY_PORT=80 \
    NODE_ENV=production

EXPOSE 80

CMD ["npm", "run", "start"]

