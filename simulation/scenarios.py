"""Demo scenarios and the adaptive-switching timeline (spec Step 7 / Section 14).

Scenario conditions are SIMULATED workload/network conditions.
"""
from decision_engine.policy import Conditions

SCENARIOS = {
    "1. Speed priority":    Conditions("LOW",      0.1, 10,  10_000, 10_000),
    "2. Maximum security":  Conditions("CRITICAL", 25,  200, 100_000, 10_000),
    "3. Balanced workload": Conditions("MEDIUM",   5,   50,  20_000, 10_000),
    "4. Network constrained (after #3)": Conditions("MEDIUM", 5, 20, 300, 10_000),
}
TIMELINE = ["1. Speed priority", "2. Maximum security", "3. Balanced workload", "4. Network constrained (after #3)"]

# Intended qualitative outcome (spec Section 12.3). The real outcome is always computed by decide().
EXPECTED = {
    "1. Speed priority": "CLASSICAL",
    "2. Maximum security": "QUANTUM_SAFE",
    "3. Balanced workload": "HYBRID",
    "4. Network constrained (after #3)": "CLASSICAL",
}

STORIES = {
    "1. Speed priority": "Short-lived, low-sensitivity telemetry between HPC nodes with a strict 10 ms budget.",
    "2. Maximum security": "Critical data that must stay confidential for 25 years (harvest-now-decrypt-later risk).",
    "3. Balanced workload": "Medium-sensitivity research data, moderate budget, good network.",
    "4. Network constrained (after #3)": "Same workload as #3, but the link drops to 300 kbps and the budget tightens to 20 ms.",
}
