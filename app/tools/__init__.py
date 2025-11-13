#!/usr/bin/env python3
# app/tools/__init__.py
# -*- coding: utf-8 -*-
"""
Tool registry for MCP server.
"""

from typing import Dict, Optional

from app.tools.base import OSINTTool
from app.tools.domain_recon import DomainReconTool

_TOOLS: Dict[str, OSINTTool] = {
    DomainReconTool.name: DomainReconTool(),
}


def get_tool(name: str) -> Optional[OSINTTool]:
    """Retrieve a tool instance by name."""
    return _TOOLS.get(name)
