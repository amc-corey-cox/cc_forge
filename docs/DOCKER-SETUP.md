# Docker Setup

Docker installation and configuration for the local server.

## Installation

Installed via official Docker repository (not Ubuntu's docker.io package).

### Components Installed
- `docker-ce` - Docker Engine
- `docker-ce-cli` - Command line interface
- `containerd.io` - Container runtime
- `docker-buildx-plugin` - Extended build capabilities
- `docker-compose-plugin` - Multi-container orchestration (v2, not standalone docker-compose)

### Installation Commands

```bash
# Prerequisites
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /usr/share/keyrings/docker.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group (avoids sudo for docker commands)
sudo usermod -aG docker ${USER}
newgrp docker  # or log out and back in

# Enable on boot
sudo systemctl enable docker

# Verify
docker run hello-world
```

## Post-Installation

### Verify Installation

```bash
docker --version
docker compose version
docker run hello-world
```

### Useful Commands

```bash
# List running containers
docker ps

# List all containers (including stopped)
docker ps -a

# List images
docker images

# View container logs
docker logs -f <container_name>

# Clean up unused resources
docker system prune
```

## How forge uses Docker

This doc covers installing Docker itself. For how forge *uses* it — the agent
container, the Forgejo + Ollama-proxy services, and the safety model — see
[DESIGN.md](../DESIGN.md) and [docker/README.md](../docker/README.md). In short: the
agent runs in an isolated container that clones from Forgejo, with **no host mount and
no GitHub credentials handed to it**; reviewed work reaches GitHub only via
`forge promote`, run on the host.

## Security Considerations

- Users in the `docker` group effectively have root-equivalent access on the host — only
  add trusted users to it.
- The agent container has no host filesystem mount and isn't handed GitHub credentials.
  See [DESIGN.md](../DESIGN.md) for the full safety model and its limits — notably, there
  is no network egress control yet.
