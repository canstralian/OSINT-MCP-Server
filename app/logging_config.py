#!/usr/bin/env python3
# app/logging_config.py
# -*- coding: utf-8 -*-
"""
Structured logging configuration.
"""

import logging
from typing import NoReturn


def configure_logging() -> NoReturn:
    """Configure root logger for the application."""
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=logging.INFO,
    )
