# Contributing to Termux Master Ultra (TMU) 🐺

Welcome to the TMU Swarm! This project has evolved from simple scripts into a **Cyber-Physical Orchestrator** for Android/Termux environments. Because we are optimizing for finite thermal limits and battery chemistries, our contribution standards are strict.

## 🧠 Engineering Philosophy

1. **Physical > Logical**: A node's thermal state always overrides the scheduler queue.
2. **Fail-Closed Security**: Missing tokens, invalid signatures, or missing directories must explicitly abort processes, never silently skip.
3. **No Heavy Databases**: Stick to file-based mechanisms (.jsonl, .lock) to prevent memory/storage overhead on mobile hardware.
4. **Idempotency**: All execution and recovery actions must be safe to run multiple times (crash-resumption model).

## 🛠️ Local Development Setup

1. Clone the repository natively on an Android device running Termux, or use PRoot (Ubuntu).
2. Run `./deploy-tmu.sh install --dry-run` to verify paths.
3. Set your environment variables (e.g., `TM_DASHBOARD_TOKEN`).
4. Ensure pytest and flake8 are installed: `pip install pytest flake8`.

## 🚀 The TMU Roadmap (What's Next)

### Phase 8: Speculative Execution
* **Goal**: Duplicate slow tasks automatically. If a node is projected to hit the 45°C thermal limit in 2 minutes, preemptively spawn the same task on a cooler node and accept the first successful result.

### Phase 9: Gossip Protocol (True P2P)
* **Goal**: Remove reliance on a single MQTT broker. Implement a lightweight UDP/TCP gossip protocol so nodes can dynamically share state even if the leader drops offline temporarily.

### Phase 10: Android-Native Actuation
* **Goal**: Trigger physical device responses directly from DAG failures (e.g., Use `termux-vibrate` or `termux-torch` to physically page the operator when swarm health drops below 50%).

## 📝 Pull Request Checklist

- [ ] Code passes flake8 (0 errors, warnings are okay)
- [ ] pytest execution passes locally
- [ ] Handled `set -euo pipefail` gracefully in bash additions
- [ ] Includes the trademark Husky "D-Collar" representation in relevant UI changes
- [ ] Updated API documentation if endpoint behavior changed
- [ ] Tested on actual Android hardware (simulators may behave differently)

## 🔗 Resources

- API Docs: [`docs/API.md`](docs/API.md)
- Test Suite: [`tests/test_scoring.py`](tests/test_scoring.py)
- License: [`LICENSE`](LICENSE)
