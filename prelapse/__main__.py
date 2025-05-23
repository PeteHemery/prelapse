# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# __main__.py

from __future__ import print_function

import sys
sys.dont_write_bytecode = True

from . import prelapse_main # pylint: disable=wrong-import-position


if __name__ == "__main__":
  prelapse_main()
