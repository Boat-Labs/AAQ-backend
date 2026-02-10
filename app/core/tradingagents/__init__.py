"""TradingAgents package — fix internal import resolution.

The tradingagents submodules use `from tradingagents.xxx import ...` which
requires the parent directory (app/core/) to be on sys.path.
"""
import os
import sys

_core_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _core_dir not in sys.path:
    sys.path.insert(0, _core_dir)
