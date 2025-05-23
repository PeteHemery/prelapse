# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# __init__.py

from __future__ import print_function, division

import argparse
import os
import sys
sys.dont_write_bytecode = True # Try to stop the __pycache__ pollution

from .common._init_functions import prelapse_main, set_prelapse_epilog, __version__ # pylint: disable=wrong-import-position


__all__ = ["prelapse_main", "set_prelapse_epilog", "__version__"]


if __name__ == "__main__":
  prelapse_main()
