# Local Server Ollama Configuration

This documents the Ollama setup on a local home server with a Vulkan-capable consumer GPU.

## Service Architecture

A single Ollama service is sufficient on 0.30.x. The Ollama daemon's bundled `llama.cpp` runtime auto-detects a Vulkan-compatible GPU when present and offloads what fits to VRAM, with the rest staying on CPU. There's nothing to configure per service — the same daemon transparently does what the two-service pattern on 0.15.x had to be told explicitly.

```
/etc/systemd/system/
├── ollama-cpu.service      # The service we run (port 11434)
├── ollama.service          # Stock unit; disabled (see "Stock ollama.service Reactivation" below)
└── ollama-vulkan.service   # Legacy from 0.15.x; disabled — see notes
```

The IPEX-LLM legacy path (`ollama-ipex.service.legacy`) is provided in this repo for reference if anyone wants to compare against the older Intel-specific runtime, but it lacks Claude Code's Anthropic API support and is not part of the current setup.

**Why `ollama-cpu` despite the name?** The name is historical. On 0.15.x it really did mean CPU-only — the service file set `OLLAMA_NUM_GPU=0`. On 0.30.x that env var is silently ignored by `llama-server`, so the service is now actually CPU+GPU. The name stayed because forge has hard-coded the port (11434) into a lot of places; renaming the unit would create more churn than it saves. Treat the name as "the service forge depends on," not as a backend constraint.

**Why `ollama-vulkan` is now redundant.** The original purpose was to provide a Vulkan-accelerated path on a separate port (11435) for clients that wanted GPU. With auto-detection in 0.30.x, the port-11434 service already offers that. Two services running simultaneously means two daemons competing for the same finite VRAM — a real OOM risk if both load models. Disable it: `sudo systemctl disable --now ollama-vulkan.service`.

**Port:** In this setup the service is configured to bind `0.0.0.0:11434` so forge's agent containers can reach it across the docker bridge. (Ollama's stock default is `127.0.0.1:11434` — localhost-only. See [Network Access](#network-access) for why we change it and the firewall implications.)

## Quick Reference

| Service | Port | Status | Notes |
|---------|------|--------|-------|
| `ollama-cpu` | 11434 | **active** | The one forge depends on. Auto-offloads to GPU under 0.30.x despite the name. |
| `ollama-vulkan` | 11435 | **disabled** | Legacy from the 0.15.x two-service pattern; redundant on 0.30.x. |
| `ollama-ipex` | 11434 | not installed | Legacy IPEX-LLM path; no Anthropic API support. Reference only. |
| `ollama` (stock) | 11434 | **disabled** | Resurrected by official installer upgrades; see ["Stock ollama.service Reactivation"](#stock-ollamaservice-reactivation-after-upgrades). |

### Setup

```bash
# Enable and start the service
sudo systemctl enable --now ollama-cpu.service

# Verify
systemctl is-active ollama-cpu
curl http://localhost:11434/api/tags | head -5

# Sanity-check GPU offload (under 0.30.x, expect a CPU/GPU split)
ollama run qwen3-coder-32k "Reply with OK."
ollama ps   # PROCESSOR column should show a CPU/GPU split, not 100% CPU
```

### Using the service

```bash
# Local Ollama CLI (defaults to localhost:11434)
ollama run qwen3-coder-32k "Hello"

# Claude Code via Anthropic API endpoint
ANTHROPIC_BASE_URL=http://localhost:11434 claude --model qwen3-coder-32k

# Forge agent containers reach the same service via the docker-bridge alias
# (configured in docker-compose.yml as `forge-ollama-proxy`)
```

## Recommendations

`ollama-cpu` handles all model sizes. The daemon auto-splits the model between VRAM and CPU RAM based on what fits, so the only practical constraint is whether a model loads at all (and how fast it runs once loaded). For a consumer-class GPU with a moderate VRAM budget (the forge host's class):

| Model size | Behavior on 0.30.x | Notes |
|------------|--------------------|-------|
| ≤14 GB (fits VRAM) | Full GPU | Fastest — see qwen3 probe results in [`CLAUDE-CODE-LOCAL-MODELS.md`](CLAUDE-CODE-LOCAL-MODELS.md#headline-1--10x-speedup-most-of-it-is-gpu-offload-not-just-newer-inference-code) |
| 14-40 GB | Auto-split GPU+CPU | Useful chunk in VRAM; rest in RAM. Most of forge's recommended models live here. |
| >40 GB | Mostly CPU | Slower but works. `qwen:72b` and `llama3.3:70b` end up here. |

### Performance (legacy 0.15.x measurements)

These benchmarks predate the 0.30.x upgrade and the architecture switch to `llama-server`. They're preserved as historical baseline; current performance is roughly 10x better wall-clock for full eval tasks (see the post-upgrade observations doc).

| Backend | Prompt Eval | Generation |
|---------|-------------|------------|
| IPEX GPU (legacy) | 147.6 tok/s | 39.0 tok/s |
| Vulkan GPU (0.15.x) | TBD | TBD |
| CPU only (0.15.x) | 47.6 tok/s | 18.1 tok/s |

### Model Size Behavior

llama.cpp's Vulkan backend handles VRAM-overflow gracefully:
1. **Fits in VRAM** → 100% GPU (fastest)
2. **Partially fits** → Splits layers between GPU and CPU (slower but works)
3. **Single layer too large** → Falls back to CPU only

## Service Files

Service files are in `docs/` directory:

| File | Port | Description |
|------|------|-------------|
| [`ollama-cpu.service`](ollama-cpu.service) | 11434 | The service forge depends on. Despite the name, auto-offloads to GPU under Ollama 0.30.x. |
| [`ollama-vulkan.service`](ollama-vulkan.service) | 11435 | Legacy from the 0.15.x two-service pattern. Keep disabled — the cpu service already does GPU offload on 0.30.x. |
| [`ollama-ipex.service.legacy`](ollama-ipex.service.legacy) | 11434 | IPEX-LLM GPU path; reference only. Lacks Anthropic API support. |

## Ollama Version Requirements

| Capability | Required version | Evidence |
|------------|------------------|----------|
| Anthropic Messages API (`/v1/messages`) | **0.15+** | Required for `forge` agent containers and Claude Code; matrix 1 ran successfully on 0.15.4. |
| `Gemma 4` 12B chat template | **0.30+** | The pulled variant was unrecognized on 0.15.4 (matrix 2 fell back to Gemma 3); recognized and runs on 0.30.10. |
| Auto GPU offload (Vulkan, no per-service config) | **0.30+** | On 0.15.x, GPU offload required the separate `ollama-vulkan.service`. On 0.30.x the bundled `llama-server` auto-detects Vulkan and uses it from any service, regardless of `OLLAMA_NUM_GPU` env vars. |

### Current recommendation

Run the latest stable Ollama release on the forge host. The strict minimum is 0.15 (Anthropic API), but every measured improvement we care about — the ~10x speedup from GPU offload, `Gemma 4` availability, and the simpler single-service architecture — lives at 0.30+.

### What changing Ollama version does *not* fix

We tested the hypothesis "newer Ollama's matured chat-template handling unsticks Devstral/Granite's single-turn-narration failure" in matrix 2's post-upgrade retest, and it didn't pan out. Both models fail in the same shape on 0.30.10 as on 0.15.4 — just faster. The constraint there isn't a version-bound template issue; it lives somewhere deeper in Ollama's Anthropic API translation or in how those models emit tool calls natively. See the post-upgrade observations in [`CLAUDE-CODE-LOCAL-MODELS.md`](CLAUDE-CODE-LOCAL-MODELS.md) for details.

### How to check

```bash
ollama --version
```

## Stock `ollama.service` Reactivation After Upgrades

**Problem.** Ollama's official installer (`curl https://ollama.ai/install.sh | sh`) always (re)creates `/etc/systemd/system/ollama.service` — a vanilla unit file that:

- Binds to `localhost:11434` only (no remote access)
- Has no GPU/CPU constraint
- Lacks the model-retention and load-timeout tuning that `ollama-cpu.service` provides

When this stock service starts, it grabs port 11434 and `ollama-cpu.service` (the one we actually want) starts failing with `bind: address already in use` and cycles in `auto-restart` forever. **Forge's agent containers reach Ollama through a docker bridge, so a localhost-only Ollama is unreachable to them** — the symptom in a forge session is a 3-minute `UND_ERR_SOCKET` timeout per request.

This is **not** caused by Ubuntu/apt updates — the Ollama binary lives in `/usr/local/bin/`, outside apt's reach. Reactivation specifically comes from re-running the installer script during upgrades.

### One-time cleanup

Run once when the system is in the conflict state:

```bash
sudo systemctl disable --now ollama.service
sudo mv /etc/systemd/system/ollama.service /etc/systemd/system/ollama.service.bak
sudo systemctl daemon-reload
sudo systemctl enable --now ollama-cpu.service
```

The `.bak` rename preserves the original file content for reference — systemd only loads files ending in `.service`.

> **Note for the "Files and Locations" table below:** that table documents the *initial* layout (before any cleanup). Once you've run this procedure, `/etc/systemd/system/ollama.service` is at `…/ollama.service.bak` instead. Subsequent post-upgrade runs add timestamps to avoid overwriting prior backups.

### Post-upgrade ritual

Run after every Ollama installer upgrade:

```bash
sudo systemctl disable --now ollama.service && \
sudo mv /etc/systemd/system/ollama.service /etc/systemd/system/ollama.service.bak.$(date +%Y%m%d-%H%M%S) && \
sudo systemctl daemon-reload && \
sudo systemctl restart ollama-cpu.service
```

### Cleaner alternative: upgrade by tarball extraction

Skip the installer; extract the release tarball directly so the systemd unit files are never touched. Ollama releases ship as `.tar.zst` archives containing `bin/ollama` plus a `lib/ollama/` tree of inference backends — a single-file binary swap is no longer enough.

Find the current release asset URL on the [Ollama GitHub releases page](https://github.com/ollama/ollama/releases) (the linux-amd64 build is `ollama-linux-amd64.tar.zst`; the `-rocm` and `-mlx` variants are for AMD GPUs and Apple Silicon respectively).

```bash
# 1. Download (no sudo needed; ~1.4 GB for v0.30.10)
mkdir -p ~/tmp/ollama-upgrade && cd ~/tmp/ollama-upgrade
curl -fL -o ollama-linux-amd64.tar.zst \
  https://github.com/ollama/ollama/releases/download/v0.30.10/ollama-linux-amd64.tar.zst

# 2. Stop services (do both if you run vulkan as well — they share the binary)
sudo systemctl stop ollama-cpu.service ollama-vulkan.service

# 3. Back up the old install
sudo cp /usr/local/bin/ollama /usr/local/bin/ollama.$(ollama --version | awk '{print $NF}')
sudo mv /usr/local/lib/ollama /usr/local/lib/ollama.$(ollama --version | awk '{print $NF}')

# 4. Extract the new tarball over /usr/local
sudo tar --zstd -xf ollama-linux-amd64.tar.zst -C /usr/local/

# 5. Confirm and start (only the cpu service — vulkan service is legacy on 0.30.x)
/usr/local/bin/ollama --version
sudo systemctl start ollama-cpu.service
systemctl is-active ollama-cpu
```

Why the two backups (binary + lib dir): the lib dir contains inference backends (CUDA variants, CPU microarchitecture variants, libggml-base versioned suffixes). Newer tarballs introduce new files but don't remove old ones — extracting on top leaves stale libs lying around. Moving the old lib dir aside gives a clean install and a one-step rollback (`sudo mv` it back, restore the binary backup).

Disk cost: each `.tar.zst` is ~1.4 GB and each extracted `lib/ollama` is roughly 6 GB (the CUDA libs are the bulk). Keeping the previous version's lib dir around as `lib/ollama.<old-version>/` doubles that until you're confident the new install works and prune the backup.

### Detecting the problem

`ollama-cpu.service` cycling in `auto-restart` state with `bind: address already in use` in `journalctl -u ollama-cpu` means the stock `ollama.service` is back. [Issue #57](https://github.com/amc-corey-cox/cc_forge/issues/57) (`forge doctor` pre-flight check) will surface this automatically once implemented.

## Post-Upgrade Verification (forge-specific)

After upgrading Ollama, the service-reactivation ritual above gets the daemon running again, but it doesn't confirm that forge itself still works against the new version. These checks are cheap and catch breakage early.

### 1. Confirm the new version

```bash
ollama --version
```

Cross-check against the requirements table above.

### 2. Confirm `ollama list` survived the upgrade

```bash
ollama list
```

Compare against a snapshot taken before the upgrade (`ollama list > ~/.ollama-list.pre-upgrade.txt`). Ollama major version jumps occasionally rewrite the model-store format; missing entries here mean something to investigate before going further.

### 3. Confirm forge's reach to Ollama

Forge's agent containers reach Ollama via the `forge-ollama-proxy` alias on the `forge-network` docker bridge. The alias is only resolvable from inside containers attached to that network — not from the host OS. Two ways to smoke-test:

```bash
# From inside a container on forge-network (mirrors what an agent does)
docker run --rm --network forge-network curlimages/curl:latest \
    -s http://forge-ollama-proxy:11434/api/tags | head -20

# Or from the host, hitting the daemon directly on localhost
curl -s http://localhost:11434/api/tags | head -20
```

A populated JSON model list from either path confirms the upgraded daemon is up. The first path additionally confirms the docker-bridge route forge agents actually use is intact.

### 4. Re-run the matrix 2 pre-flight check

```bash
cd ~/Code/cc_forge && ./scripts/eval/screening-matrix-2.sh --check
```

This re-checks `tools` capability for each candidate. Any model that flipped from rejected to accepted (or vice versa) is a finding — record it in the post-upgrade observations section of `docs/CLAUDE-CODE-LOCAL-MODELS.md`.

### 5. Baseline-model probe

Confirm the known-good model still drives Claude Code end-to-end against the full capability suite:

```bash
RUN_ID="post-upgrade-smoke-$(date -u +%Y%m%dT%H%M%SZ)" \
MODELS="qwen3-coder-32k" \
TASKS_DIR=./scripts/eval/tasks \
OLLAMA_URL="http://forge-ollama-proxy:11434" \
./scripts/eval/run-matrix.sh
```

This runs the full 6-task matrix (sanity probe + 5 capability tasks) against `qwen3-coder-32k`. Expected: 5/5 PASS, total wall-clock around 17 minutes on a host with GPU offload available, longer on CPU-only. A timeout or failure here means the upgrade regressed something forge depends on — investigate before letting agents loose.

If you want a faster smoke check before committing to the full suite, point `TASKS_DIR` at a directory containing just one task: `mkdir -p ~/tmp/smoke && ln -sf $(pwd)/scripts/eval/tasks/02-fix-typo ~/tmp/smoke/` then re-run with `TASKS_DIR=~/tmp/smoke`. The matrix runner iterates whatever subdirectories live under `TASKS_DIR`, so a single-task directory gives a single-task run.

### 6. Optional: regression check for non-forge models

If the host runs Ollama for purposes outside cc_forge (e.g., the `vanilj/midnight-miqu-70b-v1.5` and `qwen:72b` workloads), confirm they still respond:

```bash
ollama run vanilj/midnight-miqu-70b-v1.5 "Reply with just OK."
ollama run qwen:72b "Reply with just OK."
```

Major Ollama version jumps occasionally retire support for very old quantization formats or chat templates; a non-trivial response here is the cheapest signal that nothing in the broader Ollama installation regressed.

### 7. Capture findings in `CLAUDE-CODE-LOCAL-MODELS.md`

When the upgrade reveals anything that changes matrix interpretation — newly accepted models, fixed tool-call emission, regressions, etc. — append a "Post-Ollama-upgrade observations" subsection to `docs/CLAUDE-CODE-LOCAL-MODELS.md`. The eval doc is the canonical record of what works against which Ollama version; the setup doc shouldn't accumulate those findings inline.

## Model Compatibility

Under Ollama 0.30.x with the single `ollama-cpu` service, the daemon auto-splits each model between VRAM and CPU RAM based on what fits. The column that mattered on 0.15.x (which port/service to use) no longer applies — there's only one service, and it decides.

| Model | Size | Behavior on 0.30.x | Notes |
|-------|------|--------------------|-------|
| llama3.1:latest | 4.7 GB | Full GPU | Fits comfortably in VRAM |
| qwen2.5-coder:7b | 4.7 GB | Full GPU | Fits comfortably in VRAM |
| llama3.1:8b-q8 | 8.5 GB | Full GPU | Fits in VRAM |
| llama2-uncensored | 3.8 GB | Full GPU | Fits comfortably in VRAM |
| qwen3-coder-32k | 18 GB | GPU+CPU split | Majority of working set in VRAM, rest in RAM (per `ollama ps`) |
| qwen3-coder-64k | 18 GB | GPU+CPU split | Same model size, larger KV cache pushes more to CPU |
| deepseek-r1:70b | 42 GB | GPU+CPU split | Most weight in RAM; useful chunk in VRAM |
| llama3.3:70b | 57 GB | Mostly CPU | Slower; VRAM holds only a small fraction |

**Behavior categories:**
- **Full GPU** — Entire model in VRAM, fastest
- **GPU+CPU split** — Partial offload, works at intermediate speed; specifics depend on the model's KV-cache size at the active context window
- **Mostly CPU** — Working set exceeds VRAM enough that most layers stay on CPU; usable but slower

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

1. **Anthropic API + Vulkan crash** *(likely resolved in 0.30.x)*: Ollama's `/v1/messages` endpoint historically crashed with Vulkan backend ([Issue #13949](https://github.com/ollama/ollama/issues/13949)) on 0.15.x. Under 0.30.x, forge's path (Claude Code → `forge-ollama-proxy` → port 11434 → auto-Vulkan-offload llama-server) was observed working cleanly during the post-upgrade verification — no crashes during the qwen3-coder-32k probe or matrix-2 retest. Whether the underlying Ollama bug is properly fixed or our path simply doesn't hit it is unclear. The "use CPU service or shim" workaround documented below is preserved as fallback if the crash reappears.
2. **Claude Code large context**: Claude Code sends ~18KB system prompts. On 0.15.x this took 60-90s for first request on CPU; on 0.30.x with GPU offload it's faster but still the dominant cost for short tasks. See post-upgrade observations in [`CLAUDE-CODE-LOCAL-MODELS.md`](CLAUDE-CODE-LOCAL-MODELS.md).
3. **Vulkan slower than IPEX**: Vulkan backend is slower than IPEX-LLM, but IPEX is stuck on older Ollama without Anthropic API support.
4. **Partial offload performance**: When models split between GPU+CPU, performance drops vs full GPU. Empirically (qwen3-coder-32k on the forge host's GPU class): the share of inference on GPU roughly tracks the share of weights that fit in VRAM — a meaningful speed bump but not full-GPU speed.
5. **`OLLAMA_NUM_GPU=0` no longer honored**: The env var that the legacy `ollama-cpu.service` set to keep its service CPU-only is silently ignored by 0.30.x's llama-server backend. Auto-offload to GPU happens regardless. No known clean way to genuinely disable GPU offload at the service level on 0.30.x.
6. **SYCL support pending**: Native SYCL/oneAPI support for Intel Arc is [in PR #11160](https://github.com/ollama/ollama/pull/11160), not yet merged at time of writing.

## Files and Locations

| Path | Purpose |
|------|---------|
| `/etc/systemd/system/ollama-cpu.service` | The active service forge uses (port 11434) — name is historical; under 0.30.x it auto-offloads to GPU. |
| `/etc/systemd/system/ollama-vulkan.service` | Legacy unit from the 0.15.x two-service pattern; keep disabled on 0.30.x. |
| `/etc/systemd/system/ollama.service[.bak]` | Stock unit; renamed `.bak` after the reactivation ritual. |
| `/usr/local/bin/ollama` | Ollama binary. |
| `/usr/local/bin/ollama.<old-version>` | Binary backup from the last `ollama` upgrade (created by the tarball-extraction procedure above). Safe to delete once the new version is confirmed working. |
| `/usr/local/lib/ollama/` | Ollama inference backends (CPU microarchitecture variants, `vulkan/`, `cuda_v12/`, `cuda_v13/`). Multi-file install since 0.16-ish. |
| `/usr/local/lib/ollama.<old-version>/` | Lib-dir backup from the last upgrade. Same disposition as the binary backup. |
| `/usr/share/ollama/.ollama/models/` | Downloaded model blobs (shared across services and ollama users). |

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

**Bug** (on Ollama 0.15.x): Ollama's Anthropic API (`/v1/messages`) crashed when used with the Vulkan GPU backend. See [Issue #13949](https://github.com/ollama/ollama/issues/13949).

| Backend | Direct Ollama API | Anthropic API (Claude Code) |
|---------|-------------------|----------------------------|
| CPU (11434) on 0.15.x | ✅ Works | ✅ Works |
| Vulkan GPU (11435) on 0.15.x | ✅ Works | ❌ Crashes |
| `ollama-cpu` on 0.30.x (auto-offloads to Vulkan) | ✅ Works | ✅ **Observed working** during the post-upgrade verification |

The 0.30.x observation suggests either the underlying bug is fixed or the new llama-server's Anthropic-API path takes a different route. The workarounds below are preserved for anyone still on 0.15.x or in case the crash reappears.

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
# Clone and build the shim
cd /tmp && git clone https://github.com/hilyin/ollama-anthropic-shim.git
cd ollama-anthropic-shim

# Option A: Use their script (builds and runs via docker-compose)
echo 'OLLAMA_BASE_URL=http://127.0.0.1:11435' > .env
echo 'OLLAMA_MODEL=llama3.1:latest' >> .env
echo 'SHIM_PORT=4001' >> .env
./up.sh  # Note: uses docker-compose, may need network adjustments on Linux

# Option B: Build and run manually with host networking
docker build -t ollama-shim:local .
docker run -d --name ollama-shim --network=host \
  -e OLLAMA_BASE_URL=http://127.0.0.1:11435 \
  -e OLLAMA_MODEL=llama3.1:latest \
  -e SHIM_PORT=4001 \
  ollama-shim:local

# Use Claude Code through shim → GPU
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_BASE_URL=http://localhost:4001
claude --model llama3.1:latest -p "Hello"
```

**Security note**: `--network=host` exposes the shim on all interfaces. Since Ollama binds to 127.0.0.1, this is needed for the container to reach it. Ensure your firewall blocks external access to port 4001 if needed.

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
