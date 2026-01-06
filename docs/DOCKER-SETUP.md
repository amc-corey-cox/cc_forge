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

## Architecture Notes

Docker is used for the CC Forge agent system:

- **Agent containers**: Isolated environments for dev/test/review agents
- **Full network access**: Agents can access Ollama, GitHub, and external resources
- **Scoped GitHub tokens**: Agents have limited permissions (create PRs, no admin)
- **Branch protection**: Agents cannot push directly to main

See [Issue #4](https://github.com/amc-corey-cox/cc_forge/issues/4) for the agent architecture design.

## Security Considerations

- Users in the `docker` group effectively have root-equivalent access
- Only add trusted users to the docker group
- Containers protect the host system from agent actions
- GitHub branch protection prevents direct pushes to main
