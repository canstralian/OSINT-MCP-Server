#!/usr/bin/env python3
# app/routes/__init__.py
# -*- coding: utf-8 -*-
"""
Routes module for OSINT MCP Server.
"""

from app.routes.tools import router as tools_router

__all__ = ["tools_router"]
