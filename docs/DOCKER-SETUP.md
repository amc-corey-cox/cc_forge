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
echo "deb [arch="$(dpkg --print-architecture)" signed-by=/usr/share/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
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

## Architecture Notes

Docker is used for the cc_forge agent system:

- **Gitea**: Local git server for agent workspaces
- **Agent containers**: Isolated environments for dev/test/review agents
- **Network isolation**: Agents cannot access internet directly

See [AGENT-CONTAINERS.md](AGENT-CONTAINERS.md) for the agent architecture (when created).

## Security Considerations

- Users in the `docker` group effectively have root-equivalent access
- Only add trusted users to the docker group
- Agent containers run with restricted network access
- Agents push to local Gitea, not directly to GitHub
