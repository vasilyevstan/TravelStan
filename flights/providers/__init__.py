"""Provider boundary.

Only the synthetic provider implements the normalized protocol. No live
provider adapter, registry hook, credential, or fallback exists.
"""

from .base import FlightProvider
from .synthetic import SyntheticDemoProvider, get_provider

__all__ = ["FlightProvider", "SyntheticDemoProvider", "get_provider"]
