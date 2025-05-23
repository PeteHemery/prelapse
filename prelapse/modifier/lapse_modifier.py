# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# modifier/lapse_modifier.py

from .image_modifier import run_mogrify_cmd
from .group_modifier import run_group
from .label_modifier import run_labels

from .argument_parser import _add_parser_args, _parse_args

class LapseModifier: # pylint: disable=too-few-public-methods
  """Main modifier class"""

  add_parser_args = staticmethod(_add_parser_args)
  parse_args = classmethod(_parse_args)

  def run_modifier(self, args):
    assert args.modcmd is not None, "Must select a sub-command. See usage with -h"
    opts = {
      "image": run_mogrify_cmd,
      "group": run_group,
      "labels": run_labels,
    }
    if args.modcmd not in opts:
      raise RuntimeError("Unknown mod command")
    opts[args.modcmd](self, args)
