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
| ≤16GB only | `ollama-ipex` | GPU acceleration, much faster |
| >16GB (70b) | `ollama-cpu` | Only option that works |

**Workflow:**
1. Keep `ollama-cpu` as the default (works with everything)
2. Switch to `ollama-ipex` when doing intensive work with smaller models
3. Switch back to `ollama-cpu` when done or when you need 70b models

## Service Files

### ollama-ipex.service (GPU via SYCL/Level Zero)

```ini
[Unit]
Description=Ollama Service (IPEX-LLM SYCL Backend)
After=network-online.target

[Service]
ExecStart=/home/corey/ipex-ollama/ollama-ipex-llm-2.3.0b20250612-ubuntu/ollama serve
User=corey
Group=corey
Restart=always
RestartSec=3
WorkingDirectory=/home/corey/ipex-ollama/ollama-ipex-llm-2.3.0b20250612-ubuntu

# IPEX-LLM environment
Environment="OLLAMA_NUM_GPU=999"
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="no_proxy=localhost,127.0.0.1"
Environment="ZES_ENABLE_SYSMAN=1"
Environment="SYCL_CACHE_PERSISTENT=1"
Environment="SYCL_PI_LEVEL_ZERO_USE_IMMEDIATE_COMMANDLISTS=1"

# Use bundled SYCL libraries
Environment="LD_LIBRARY_PATH=/home/corey/ipex-ollama/ollama-ipex-llm-2.3.0b20250612-ubuntu"

[Install]
WantedBy=default.target
```

### ollama-cpu.service (CPU only, for large models)

Uses stock Ollama binary (IPEX binary doesn't have proper CPU-only mode).

```ini
[Unit]
Description=Ollama Service (CPU Only)
After=network-online.target

[Service]
# Use stock Ollama binary - IPEX binary doesn't have proper CPU fallback
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3

# Force CPU only - disable all GPU backends
Environment="OLLAMA_NUM_GPU=0"
Environment="OLLAMA_HOST=0.0.0.0:11434"

[Install]
WantedBy=default.target
```

### ollama-vulkan.service (Vulkan GPU, fallback)

```ini
[Unit]
Description=Ollama Service (Vulkan Backend)
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3

Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_VULKAN=1"

[Install]
WantedBy=default.target
```

## Model Compatibility

| Model | Size | IPEX | CPU | Vulkan | Notes |
|-------|------|------|-----|--------|-------|
| llama3.1:latest | 4.7GB | ✅ Fast | ✅ Slow | ✅ Fast | Fits in VRAM |
| llama3.1:8b | 8.5GB | ✅ Fast | ✅ Slow | ✅ Fast | Fits in VRAM |
| llama2-uncensored | 3.8GB | ✅ Fast | ✅ Slow | ✅ Fast | Fits in VRAM |
| deepseek-r1:70b | 42GB | ❌ | ✅ Slow | ⚠️ Garbled | Use CPU |
| llama3.3:70b | 57GB | ❌ | ✅ Slow | ❌ OOM | Use CPU |

## Initial Setup

Run these commands on the local server to set up the services:

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
wget -qO - https://repositories.intel.com/gpu/intel-graphics.key | \
  sudo gpg --yes --dearmor --output /usr/share/keyrings/intel-graphics.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/intel-graphics.gpg] \
  https://repositories.intel.com/gpu/ubuntu noble client" | \
  sudo tee /etc/apt/sources.list.d/intel-gpu-noble.list
sudo apt update
sudo apt install -y libze-intel-gpu1 libze1
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
| `~/ipex-ollama/` | IPEX-LLM portable installation |
| `~/.ollama/models/` | Downloaded models |
