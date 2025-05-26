# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# configs/__init__.py

from .configs import load_config, save_config, ImageGroup

DEFAULT_CONFIG_FILE_NAME = "prelapse_config.md"

__all__ = ["load_config", "save_config", "ImageGroup", "DEFAULT_CONFIG_FILE_NAME"]
