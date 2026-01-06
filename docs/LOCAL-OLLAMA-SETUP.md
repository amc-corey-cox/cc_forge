# Local Server Ollama Configuration

This documents the Ollama setup on a local home server with Intel Arc GPU.

## Service Architecture

Four systemd services available, only one active at a time (all bind to port 11434):

```
/etc/systemd/system/
├── ollama.service          # Original stock Ollama (preserved as baseline)
├── ollama-cpu.service      # CPU only (default - works with all models)
├── ollama-ipex.service     # IPEX-LLM GPU (fast, but only for models ≤16GB)
├── ollama-vulkan.service   # Vulkan GPU (fallback)
```

OpenWebUI connects to `localhost:11434` and works with whichever service is active.

**Note:** Services bind to `127.0.0.1` (localhost only) by default for security. See [Network Access](#network-access) if you need remote access.

## Quick Reference

| Service | Best For | Use When |
|---------|----------|----------|
| `ollama-cpu` | All models | **Default** - works with everything, slower |
| `ollama-ipex` | Models ≤16GB | Want GPU speed, using smaller models |
| `ollama-vulkan` | Models ≤16GB | IPEX has issues, need GPU fallback |
| `ollama` | Baseline | Original config, troubleshooting |

### Switching Services

```bash
# Switch to CPU (default - works with all models)
sudo systemctl disable --now ollama ollama-ipex ollama-vulkan
sudo systemctl enable --now ollama-cpu

# Switch to IPEX (GPU, for small models only)
sudo systemctl disable --now ollama ollama-cpu ollama-vulkan
sudo systemctl enable --now ollama-ipex

# Switch to Vulkan (GPU fallback)
sudo systemctl disable --now ollama ollama-cpu ollama-ipex
sudo systemctl enable --now ollama-vulkan

# Switch to original stock Ollama
sudo systemctl disable --now ollama-cpu ollama-ipex ollama-vulkan
sudo systemctl enable --now ollama

# Check which is active
systemctl is-active ollama ollama-cpu ollama-ipex ollama-vulkan
```

## Recommendations

**Default:** Use `ollama-cpu` - it works with all models and won't fail unexpectedly.

**For performance:** Switch to `ollama-ipex` when you know you'll be using smaller models (≤16GB) and want GPU acceleration.

| Model Size | Recommended Service | Why |
|------------|---------------------|-----|
| Any / Mixed | `ollama-cpu` | Safe default, works with everything |
| ≤16GB only | `ollama-ipex` | GPU acceleration, ~2x faster |
| >16GB (70b) | `ollama-cpu` | Only option that works |

### Performance (llama3.1:latest 4.7GB)

| Backend | Prompt Eval | Generation |
|---------|-------------|------------|
| IPEX GPU | 147.6 tok/s | 39.0 tok/s |
| CPU | 47.6 tok/s | 18.1 tok/s |

IPEX provides ~2x faster generation and ~3x faster prompt processing.

**Workflow:**
1. Keep `ollama-cpu` as the default (works with everything)
2. Switch to `ollama-ipex` when doing intensive work with smaller models
3. Switch back to `ollama-cpu` when done or when you need 70b models

## Service Files

Service files are in `docs/` directory:

| File | Description |
|------|-------------|
| [`ollama-cpu.service`](ollama-cpu.service) | CPU only (default) - uses stock Ollama binary |
| [`ollama-ipex.service`](ollama-ipex.service) | IPEX-LLM GPU via SYCL/Level Zero |
| [`ollama-vulkan.service`](ollama-vulkan.service) | Vulkan GPU backend |

## Model Compatibility

| Model | Size | IPEX | CPU | Vulkan | Notes |
|-------|------|------|-----|--------|-------|
| llama3.1:latest | 4.7GB | ✅ Fast | ✅ Slow | ✅ Fast | Fits in VRAM |
| llama3.1:8b | 8.5GB | ✅ Fast | ✅ Slow | ✅ Fast | Fits in VRAM |
| llama2-uncensored | 3.8GB | ✅ Fast | ✅ Slow | ✅ Fast | Fits in VRAM |
| deepseek-r1:70b | 42GB | ❌ | ✅ Slow | ⚠️ Garbled | Use CPU |
| llama3.3:70b | 57GB | ❌ | ✅ Slow | ❌ OOM | Use CPU |

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

1. **No CPU+GPU split**: Neither IPEX nor Vulkan reliably supports partial offloading on Intel Arc
2. **Manual switching required**: Must switch services for different model sizes (see [Issue #1](https://github.com/amc-corey-cox/cc_forge/issues/1) for future proxy solution)
3. **Vulkan corruption**: Vulkan backend produces garbled output when splitting large models

## Files and Locations

| Path | Purpose |
|------|---------|
| `/etc/systemd/system/ollama.service` | Original stock Ollama (preserved) |
| `/etc/systemd/system/ollama-cpu.service` | CPU-only service (default) |
| `/etc/systemd/system/ollama-ipex.service` | IPEX GPU service |
| `/etc/systemd/system/ollama-vulkan.service` | Vulkan GPU service |
| `/opt/ipex-llm/` | IPEX-LLM installation |
| `/usr/share/ollama/.ollama/models/` | Downloaded models (ollama user) |
