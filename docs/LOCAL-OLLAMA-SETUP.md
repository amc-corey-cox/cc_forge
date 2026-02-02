# Local Server Ollama Configuration

This documents the Ollama setup on a local home server with Intel Arc GPU.

## Service Architecture

**Recommended: Run both services simultaneously** on different ports:

```
/etc/systemd/system/
├── ollama-cpu.service      # CPU only, port 11434 (default)
├── ollama-vulkan.service   # Vulkan GPU (Intel Arc), port 11435
├── ollama-ipex.service     # IPEX-LLM GPU (legacy, port 11434)
├── ollama.service          # Original stock Ollama (preserved as baseline)
```

**Port assignments:**
- `localhost:11434` — CPU service (reliable, works with all model sizes)
- `localhost:11435` — Vulkan GPU service (fast, auto-splits large models)

**Note:** Services bind to `127.0.0.1` (localhost only) by default for security. See [Network Access](#network-access) if you need remote access.

## Quick Reference

| Service | Port | Best For | Notes |
|---------|------|----------|-------|
| `ollama-cpu` | 11434 | Large models (70B), baseline | Slower but reliable |
| `ollama-vulkan` | 11435 | Small/medium models | Fast GPU, auto-splits if needed |
| `ollama-ipex` | 11434 | Legacy IPEX setup | Older Ollama version, no Claude Code support |

### Recommended Setup (Both Services)

```bash
# Enable both services to run simultaneously
sudo systemctl enable --now ollama-cpu ollama-vulkan

# Verify both are running
systemctl is-active ollama-cpu ollama-vulkan

# Test each endpoint
curl http://localhost:11434/api/tags  # CPU
curl http://localhost:11435/api/tags  # GPU
```

### Using Each Service

```bash
# Use CPU service (port 11434 - default)
ollama run llama3.3:70b-instruct-q6_K "Hello"
OLLAMA_HOST=localhost:11434 ollama run ...

# Use Vulkan GPU service (port 11435)
OLLAMA_HOST=localhost:11435 ollama run llama3.1:latest "Hello"

# Claude Code with CPU (default)
ANTHROPIC_BASE_URL=http://localhost:11434 claude --model llama3.1

# Claude Code with GPU
ANTHROPIC_BASE_URL=http://localhost:11435 claude --model llama3.1
```

### Legacy: Single Service Mode

If you prefer only one service at a time (old behavior):

```bash
# Switch to CPU only
sudo systemctl disable --now ollama-vulkan ollama-ipex
sudo systemctl enable --now ollama-cpu

# Switch to Vulkan GPU only (change port to 11434 in service file first)
sudo systemctl disable --now ollama-cpu ollama-ipex
sudo systemctl enable --now ollama-vulkan

# Check which is active
systemctl is-active ollama ollama-cpu ollama-ipex ollama-vulkan
```

## Recommendations

**Best setup:** Run both `ollama-cpu` and `ollama-vulkan` simultaneously.

| Model Size | Recommended Port | Why |
|------------|------------------|-----|
| ≤16GB (7B-13B) | 11435 (Vulkan) | Full GPU acceleration |
| 16-48GB (30B-70B) | 11435 (Vulkan) | Auto-splits GPU+CPU |
| >48GB or reliability needed | 11434 (CPU) | Pure CPU, always works |

### Performance (llama3.1:latest 4.7GB)

| Backend | Prompt Eval | Generation |
|---------|-------------|------------|
| IPEX GPU | 147.6 tok/s | 39.0 tok/s |
| Vulkan GPU | TBD | TBD |
| CPU | 47.6 tok/s | 18.1 tok/s |

*Note: Vulkan benchmarks pending. IPEX has better performance than Vulkan for Intel Arc but requires older Ollama version without Claude Code support.*

### Model Size Behavior (Vulkan)

Ollama 0.15+ with Vulkan automatically handles models larger than VRAM:
1. **Fits in VRAM** → 100% GPU (fastest)
2. **Partially fits** → Splits layers between GPU and CPU (slower but works)
3. **Single layer too large** → Falls back to CPU only

**Workflow:**
1. Use port 11435 (Vulkan GPU) for most work — fast for small models, auto-splits large ones
2. Use port 11434 (CPU) when you need guaranteed reliability or GPU is busy

## Service Files

Service files are in `docs/` directory:

| File | Port | Description |
|------|------|-------------|
| [`ollama-cpu.service`](ollama-cpu.service) | 11434 | CPU only, stock Ollama 0.15+ |
| [`ollama-vulkan.service`](ollama-vulkan.service) | 11435 | Vulkan GPU (Intel Arc), stock Ollama 0.15+ |
| [`ollama-ipex.service`](ollama-ipex.service) | 11434 | IPEX-LLM GPU (legacy, older Ollama) |

## Model Compatibility

| Model | Size | Vulkan (11435) | CPU (11434) | Notes |
|-------|------|----------------|-------------|-------|
| llama3.1:latest | 4.7GB | ✅ Full GPU | ✅ Works | Fits in VRAM |
| qwen2.5-coder:7b | 4.7GB | ✅ Full GPU | ✅ Works | Fits in VRAM |
| llama3.1:8b-q8 | 8.5GB | ✅ Full GPU | ✅ Works | Fits in VRAM |
| llama2-uncensored | 3.8GB | ✅ Full GPU | ✅ Works | Fits in VRAM |
| deepseek-r1:70b | 42GB | ⚠️ GPU+CPU split | ✅ Works | Auto-splits, slower |
| llama3.3:70b | 57GB | ⚠️ GPU+CPU split | ✅ Works | Auto-splits, slower |

**Legend:**
- ✅ Full GPU = Entire model in VRAM, fastest
- ⚠️ GPU+CPU split = Partial offload, works but slower (5-30x slower than full GPU)
- ✅ Works = Reliable but CPU-speed

## Initial Setup

### Prerequisites

1. **Stock Ollama installed** at `/usr/local/bin/ollama`
2. **`ollama` system user** exists (created by Ollama installer)
3. **Level Zero runtime** installed (for IPEX GPU support)

### Install IPEX-LLM

Download and install IPEX-LLM to the system location:

```bash
# Check latest version at: https://github.com/intel/ipex-llm/releases
IPEX_VERSION="2.3.0"

# Download IPEX-LLM portable
cd /tmp
wget "https://github.com/intel/ipex-llm/releases/download/v${IPEX_VERSION}/ollama-ipex-llm-${IPEX_VERSION}-ubuntu.tar.gz"
tar -xzf ollama-ipex-llm-*.tar.gz

# Install to system location
sudo mkdir -p /opt/ipex-llm
sudo mv ollama-ipex-llm-*/* /opt/ipex-llm/
sudo chown -R ollama:ollama /opt/ipex-llm

# Verify
ls -la /opt/ipex-llm/ollama
```

**Trust note:** IPEX-LLM releases do not currently provide checksums or signatures. This installation trusts the GitHub release artifacts. Review the [IPEX-LLM repository](https://github.com/intel/ipex-llm) if you have concerns about supply chain security.

### Install Service Files

```bash
# 1. Stop and disable the original service (but keep the file as backup)
sudo systemctl stop ollama
sudo systemctl disable ollama

# 2. Copy the three new service files (from this repo's docs/ folder)
sudo cp ollama-ipex.service /etc/systemd/system/
sudo cp ollama-cpu.service /etc/systemd/system/
sudo cp ollama-vulkan.service /etc/systemd/system/

# 3. Reload systemd
sudo systemctl daemon-reload

# 4. Enable and start CPU service (recommended default)
sudo systemctl enable --now ollama-cpu

# 5. Verify
systemctl status ollama-cpu
ollama run llama3.1:latest "What is 2+2?"
```

**Note:** The original `ollama.service` is preserved as a known-working baseline for troubleshooting.

## Network Access

By default, services bind to `127.0.0.1` (localhost only) for security. If you need remote access (e.g., from OpenWebUI on another machine):

1. **Edit the service file** - change `OLLAMA_HOST=127.0.0.1:11434` to `OLLAMA_HOST=0.0.0.0:11434`
2. **Configure firewall** to restrict access to trusted IPs only:
   ```bash
   # Replace <YOUR_SUBNET> with your network (e.g., 192.168.1.0/24)
   sudo ufw allow from <YOUR_SUBNET> to any port 11434
   ```
3. **Reload the service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl restart ollama-cpu  # or whichever is active
   ```

## Troubleshooting

### Check which service is running

```bash
systemctl is-active ollama-ipex ollama-cpu ollama-vulkan
```

### Check logs

```bash
journalctl -u ollama-ipex -f
# or
journalctl -u ollama-cpu -f
# or
journalctl -u ollama-vulkan -f
```

### Port already in use

If you see "address already in use" errors, make sure only one service is enabled:

```bash
sudo systemctl stop ollama ollama-ipex ollama-cpu ollama-vulkan
sudo systemctl disable ollama ollama-ipex ollama-cpu ollama-vulkan
# Then enable just one
sudo systemctl enable --now ollama-cpu
```

### Library errors (IPEX)

If you see `libze_loader.so` or similar errors:

```bash
# Verify Level Zero is installed
dpkg -l | grep -i level-zero

# If missing, add Intel repo and install
# Detect Ubuntu codename (e.g., noble, jammy)
UBUNTU_CODENAME="$(. /etc/os-release && echo "${UBUNTU_CODENAME}")"

wget -qO - https://repositories.intel.com/gpu/intel-graphics.key | \
  sudo gpg --yes --dearmor --output /usr/share/keyrings/intel-graphics.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/intel-graphics.gpg] \
  https://repositories.intel.com/gpu/ubuntu ${UBUNTU_CODENAME} client" | \
  sudo tee /etc/apt/sources.list.d/intel-gpu-${UBUNTU_CODENAME}.list
sudo apt update
sudo apt install -y libze-intel-gpu1 libze1
```

**Trust note:** This adds Intel's official GPU repository. The GPG key is fetched over HTTPS from Intel's servers. See [Intel's GPU software documentation](https://dgpu-docs.intel.com/) for official installation instructions and key fingerprints.

### Permission errors (IPEX)

If IPEX service fails with permission errors:

```bash
# Ensure ollama user owns the installation
sudo chown -R ollama:ollama /opt/ipex-llm
```

## Known Limitations

1. **Anthropic API + Vulkan crash**: Ollama's `/v1/messages` endpoint crashes with Vulkan backend ([Issue #13949](https://github.com/ollama/ollama/issues/13949)). Use CPU or shim workaround.
2. **Claude Code large context**: Claude Code sends ~18KB system prompts. Local models process this slowly (60-90s first request).
3. **Vulkan slower than IPEX**: Vulkan backend is slower than IPEX-LLM, but IPEX is stuck on older Ollama without Anthropic API support.
4. **Partial offload performance**: When models split between GPU+CPU, performance drops 5-30x vs full GPU.
5. **SYCL support pending**: Native SYCL/oneAPI support for Intel Arc is [in PR #11160](https://github.com/ollama/ollama/pull/11160), not yet merged.

## Files and Locations

| Path | Purpose |
|------|---------|
| `/etc/systemd/system/ollama-cpu.service` | CPU service, port 11434 |
| `/etc/systemd/system/ollama-vulkan.service` | Vulkan GPU service, port 11435 |
| `/etc/systemd/system/ollama.service` | Original stock Ollama (preserved as baseline) |
| `/usr/local/bin/ollama` | Stock Ollama binary (0.15+) |
| `/usr/share/ollama/.ollama/models/` | Downloaded models (shared by all services) |

## Cleanup (Optional)

Legacy IPEX-LLM files can be removed to save ~450MB:

```bash
# Remove old IPEX service (if not using)
sudo systemctl disable ollama-ipex
sudo rm /etc/systemd/system/ollama-ipex.service

# Remove IPEX-LLM installation (saves ~450MB)
sudo rm -rf /opt/ipex-llm/

# Reload systemd
sudo systemctl daemon-reload
```

**Note**: Only remove IPEX if you're using Vulkan (stock Ollama 0.15+) for GPU acceleration. IPEX provides better performance but lacks Anthropic API support.

## Claude Code Integration

Ollama 0.15+ supports the Anthropic Messages API, enabling Claude Code with local models.

### Known Issue: Vulkan + Anthropic API

**Bug**: Ollama's Anthropic API (`/v1/messages`) crashes when used with Vulkan GPU backend. See [Issue #13949](https://github.com/ollama/ollama/issues/13949).

| Backend | Direct Ollama API | Anthropic API (Claude Code) |
|---------|-------------------|----------------------------|
| CPU (11434) | ✅ Works | ✅ Works |
| Vulkan GPU (11435) | ✅ Works | ❌ Crashes |

### Option 1: Use CPU Service (Simple)

```bash
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_BASE_URL=http://localhost:11434
claude --model llama3.1:latest -p "Hello"
```

Slower but reliable. Recommended for most use cases.

### Option 2: Use Shim for GPU (Advanced)

The [ollama-anthropic-shim](https://github.com/hilyin/ollama-anthropic-shim) translates Anthropic API → Ollama native API, bypassing the crash.

```bash
# Install and run shim (Docker with host networking)
cd /tmp && git clone https://github.com/hilyin/ollama-anthropic-shim.git
cd ollama-anthropic-shim
docker run -d --name ollama-shim --network=host \
  -e OLLAMA_BASE_URL=http://127.0.0.1:11435 \
  -e OLLAMA_MODEL=llama3.1:latest \
  -e SHIM_PORT=4001 \
  ollama-anthropic-shim-shim:latest

# Use Claude Code through shim → GPU
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_BASE_URL=http://localhost:4001
claude --model llama3.1:latest -p "Hello"
```

**Note**: First request is slow (~80s) due to Claude Code's large system prompt (~18KB). Subsequent requests are faster.

### Performance Expectations

Claude Code sends massive system prompts (tool definitions, context). Local 7B models struggle with this:
- **First request**: 60-90 seconds (processing system prompt)
- **Subsequent**: Faster if model stays loaded
- **Quality**: Much weaker than cloud Claude - good for simple tasks only

For complex coding tasks, consider Aider (designed for local models) or cloud Claude.

### Quick Reference

```bash
# CPU service (simple, reliable)
export ANTHROPIC_BASE_URL=http://localhost:11434

# GPU via shim (faster inference, complex setup)
export ANTHROPIC_BASE_URL=http://localhost:4001

# Run Claude Code
claude --model qwen2.5-coder:7b-instruct-q4_K_M -p "Hello"
```

See [AGENT-FRAMEWORK-EVALUATION.md](AGENT-FRAMEWORK-EVALUATION.md) for more details.
