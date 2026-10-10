# Adaptive Quantum Cryptography for Low-Latency Hybrid Computing

> **Track 2 — Quantum Security & Cryptography** · Round 1 Implementation  
> Working Prototype: **AdaptiveCrypt**  
> Architecture: `Conditions → Decision Engine → Crypto Suite → Benchmark → Dashboard`

---

## 1. Project Overview

Future quantum computers running Shor’s algorithm will break standard asymmetric cryptography (RSA, Diffie-Hellman, and elliptic curves like X25519). Today, attackers can record encrypted network traffic to decrypt it years later when quantum computers become available (**Harvest Now, Decrypt Later / HNDL**).

NIST’s standardized Post-Quantum Cryptography (PQC)—such as **ML-KEM-768 (FIPS 203)**—addresses this vulnerability, but introduces substantial communication overhead (~35× larger public keys and ciphertexts than X25519). In low-latency High-Performance Computing (HPC) connected to Quantum Computing (QC) services, blindly enforcing post-quantum security everywhere degrades latency-critical operations, while sticking to classical cryptography leaves long-lived data exposed.

**AdaptiveCrypt** is a software framework that continuously evaluates workload constraints and network conditions to automatically select the optimal cryptographic mode:
- **`CLASSICAL`**: X25519 + AES-256-GCM (ultra-low latency, small wire size, standard security)
- **`QUANTUM_SAFE`**: ML-KEM-768 + AES-256-GCM (post-quantum key establishment, long-term confidentiality)
- **`HYBRID`**: X25519 + ML-KEM-768 + AES-256-GCM (combined secret derivation; an attacker must break *both* to breach confidentiality)

Every decision is deterministic, transparent, and accompanied by human-readable justifications and guard rails.

---

## 2. Honest Security Scope & Terminology

| Component | Nature | Description |
|---|---|---|
| **Cryptographic Primitives** | **REAL** | Real key generation, X25519 ECDH, ML-KEM-768 encapsulation/decapsulation, HKDF-SHA256 key derivation, and AES-256-GCM authenticated encryption. |
| **Local Timings & Sizes** | **REAL** | Measured on this machine with `time.perf_counter()` and byte counts of actual protocol payloads. |
| **PQC Backend** | **REAL** | Standardized ML-KEM-768 via OpenSSL-backed `cryptography>=50` (hardened, constant-time) with automatic fallback to `kyber-py` if needed. |
| **Network Link & Workloads** | **SIMULATED** | Network bandwidth (kbps/Mbps), link transfer delays, HPC-QC workloads, and data sensitivity lifetime sliders. |

> **Disclaimer:** This prototype uses post-quantum software algorithms designed to run on classical hardware. It does **not** require quantum hardware, nor does it claim "quantum encryption" or unhackable guarantees.

---

## 3. Implemented Round 1 Core Features

### Feature 1 — Adaptive Security Decision Engine (`decision_engine/`)
- Function `decide(conditions, profile) -> Decision`
- **Security Need Score** (0–100): $0.60 \times \text{Sensitivity} + 0.40 \times \text{Lifetime}$
- **Performance Pressure Score** (0–100): $0.65 \times \text{Latency Pressure} + 0.35 \times \text{Bandwidth Pressure}$
- **Net Score**: $\text{Need} - \text{Pressure}$
  - $\text{Net} \ge +25 \implies \text{QUANTUM\_SAFE}$
  - $\text{Net} \le -25 \implies \text{CLASSICAL}$
  - Otherwise $\implies \text{HYBRID}$
- **Safety Floor**: High/Critical data with lifetime $\ge 10$ years is never permitted in Classical mode.
- **Feasibility Check**: Uses locally measured benchmark timings to verify if post-quantum key establishment can complete within the latency budget over the current link bandwidth; downgrades with an explicit warning if budget is exceeded.

### Feature 2 — Real Performance Benchmarking (`benchmarking/`)
- Executes repeated measurements (200 runs + 10 warm-up runs per mode) using `time.perf_counter()`.
- Records median, mean, p95 handshake times, exact handshake byte sizes, and AES-256-GCM throughput.
- Saves output directly to `benchmarking/results.json`. **No fake or hardcoded numbers.**

### Feature 3 — Interactive Streamlit Dashboard (`dashboard/`)
- Live parameter adjustments: Data sensitivity, data lifetime (years), latency budget (ms), link bandwidth, and data payload size.
- Real-time decision indicator badge with color coding, icons, and algorithm specifications.
- Net score policy gauge chart showing the decision zones.
- Component-level overhead breakdown chart comparing measured compute, simulated transfer, and AES encryption times against the latency budget.
- Live encryption button: Executes true key establishment, AES-256-GCM encryption, and decryption, confirming `Decrypted correctly: True` with exact millisecond timings and ciphertext inspection.

### Feature 4 — Adaptive Switching Demonstration (`simulation/`)
- Four standardized scenarios:
  1. **Speed Priority**: LOW sensitivity, 0.1 yr lifetime, 10 ms budget, 10 Mbps link $\rightarrow$ **CLASSICAL**
  2. **Maximum Security**: CRITICAL sensitivity, 25 yr lifetime, 200 ms budget, 100 Mbps link $\rightarrow$ **QUANTUM-SAFE**
  3. **Balanced Workload**: MEDIUM sensitivity, 5 yr lifetime, 50 ms budget, 20 Mbps link $\rightarrow$ **HYBRID**
  4. **Network Constrained**: MEDIUM sensitivity, 5 yr lifetime, 20 ms budget, 300 kbps link $\rightarrow$ **CLASSICAL** (feasibility downgrade with warning)
- Interactive timeline stepper demonstrating visible, automatic mode transitions with human-readable rationale.

---

## 4. Project Structure

```text
adaptive-quantum-crypto/
├── README.md                    # Project documentation & execution guide
├── Cypher.md                    # Specification & source of truth
├── requirements.txt             # Dependencies
├── pytest.ini                   # Pytest test suite configuration
├── crypto_suite/                # Cryptographic operations
│   ├── __init__.py
│   ├── common.py                # HKDF key derivation & AES-256-GCM encryption/decryption
│   ├── classical.py             # X25519 elliptic-curve Diffie-Hellman
│   ├── pqc.py                   # ML-KEM-768 (FIPS 203) with safe backend chain
│   ├── hybrid.py                # X25519 + ML-KEM-768 dual secret combination
│   └── suite.py                 # Unified interface: establish() & secure_roundtrip()
├── decision_engine/             # Explainable decision logic
│   ├── __init__.py
│   └── policy.py                # Scoring algorithm, safety floor & feasibility checks
├── benchmarking/                # Empirical measurement suite
│   ├── __init__.py
│   ├── run_benchmarks.py        # Benchmark harness producing results.json
│   └── results.json             # Measured timings on this local hardware
├── simulation/                  # Workload & network simulation
│   ├── __init__.py
│   ├── network.py               # Handshake transfer time estimator
│   └── scenarios.py             # 4 preset evaluation scenarios
├── dashboard/                   # Interactive demonstration UI
│   └── app.py                   # Streamlit dashboard
├── tests/                       # Automated test suite (485 tests)
│   ├── __init__.py
│   ├── test_crypto.py           # Key establishment & AES correctness / tamper tests
│   ├── test_policy.py           # Scoring formulas, guard rails & edge cases
│   ├── test_scenarios.py        # Integration & adaptive switching tests
│   └── test_dashboard.py        # Headless Streamlit AppTest verification
└── docs/
    └── screenshots/             # Visual demo captures
```

---

## 5. Quickstart / How to Run

### Step 1: Environment Setup
Ensure Python 3.10+ is installed:
```bash
# Clone or enter workspace
cd /Users/agl.kirti/Documents/Q-Hack-Cypher-

# Activate virtual environment
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Step 2: Run Real Benchmarks
Measure local machine performance and generate `benchmarking/results.json`:
```bash
python -m benchmarking.run_benchmarks
```

### Step 3: Run the Test Suite
Execute the 485 automated tests verifying crypto, policy, scenarios, and UI:
```bash
pytest -v
```

### Step 4: Launch the Interactive Dashboard
Launch Streamlit:
```bash
streamlit run dashboard/app.py
```
Open your browser at `http://localhost:8501`.

---

## 6. Live Benchmark Measurements (This Machine)

Hardware: **Apple M4 (arm64)** | OS: **macOS 26.6.2** | Python: **3.14.8**  
PQC Backend: **`cryptography/OpenSSL (ML-KEM-768, hardened)`**

| Security Mode | Algorithms | Median Handshake | Mean Handshake | p95 Handshake | Handshake Bytes |
|---|---|---|---|---|---|
| **CLASSICAL** | X25519 + AES-256-GCM | **0.128 ms** | 0.132 ms | 0.150 ms | **64 bytes** |
| **QUANTUM-SAFE** | ML-KEM-768 + AES-256-GCM | **0.167 ms** | 0.171 ms | 0.192 ms | **2,272 bytes** |
| **HYBRID** | X25519 + ML-KEM-768 + AES-256-GCM | **0.293 ms** | 0.299 ms | 0.331 ms | **2,336 bytes** |

- **AES-256-GCM Encryption Throughput**: **3,927 MB/s**
- **AES-256-GCM Decryption Throughput**: **3,833 MB/s**
