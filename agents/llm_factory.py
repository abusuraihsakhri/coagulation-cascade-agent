"""
Deterministic mock inference adapter used by the demonstration supervisor.
"""
from typing import Dict, Any, Optional
from .base import PHIGuard


class MockLLM:
    def __init__(self, system_name: str = "Coagulation Cascade Agent"):
        self.system_name = system_name

    def invoke(self, prompt: str) -> str:
        PHIGuard.assert_no_phi(prompt)
        return f"[{self.system_name} mock]: received query '{prompt[:60]}...'. No external model or clinical validation was performed."


class LLMFactory:
    """Create the deterministic mock adapter; external providers are not implemented."""

    @staticmethod
    def create(provider: str = "mock", system_name: str = "Coagulation Cascade Agent"):
        prov = str(provider).lower()
        if prov in ["mock", "deterministic", "test"]:
            return MockLLM(system_name)
        raise ValueError(f"Unsupported model provider: {provider!r}. Only the deterministic mock provider is implemented.")
