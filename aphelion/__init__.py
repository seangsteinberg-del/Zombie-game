"""APHELION — hard-realism 2D space survival/engineering sim.

Architecture contract: design/13-architecture.md (binding module layout §3.2/§4.1).
Dependency rules: sim/ imports numpy only; render/ reads sim and never mutates it;
ui/ produces intents; core/ is engine-agnostic.
"""

__version__ = "0.0.1"
