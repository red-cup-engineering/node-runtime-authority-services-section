"""
Web interface for the Relationing Research Program Repository.

This is a thin bootstrap that registers modular API routers.
All endpoint logic lives under rrp/api/*.

The repository is the research. This web interface helps navigate it.
"""

from rrp.webapp import app
