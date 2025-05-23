# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# info/argument_parser.py

from __future__ import print_function, division

from ..common import setup_logger, parse_group_args
from ..configs import load_config, DEFAULT_CONFIG_FILE_NAME

def _add_parser_args(parser):
  parser.add_argument("-c", "--config", default=DEFAULT_CONFIG_FILE_NAME,
                      help="Required Markdown config file describing the picture groups\n(default: %(default)s)")
  parser.add_argument("-a", "--allgroups", action="store_true",
                      help="access all groups\n(default: %(default)s)")
  parser.add_argument("-g", "--group", dest="groups", nargs='?', action="append",
                      help="group name within config\n"
                      "(Can use index or slice, e.g. -g groupA[10] -g groupB[55:100])")
  parser.add_argument("-d", "--details", action="store_true",
                      help="show details for requested groups\n(default: %(default)s)")
  parser.add_argument("-i", "--filename", nargs='?', action="append",
                      help="show details for image filename within requested groups")
  parser.add_argument("-f", "--filepaths-only", action="store_true",
                      help="display only the full paths to all files within specified groups. "
                           "If no groups are specified, default to all\n(default: %(default)s)")

  parser.set_defaults(allgroups=False, details=False, filepaths_only=False)
  return parser


def _parse_args(self, args):
  self.verbose = args.verbose
  self.dry_run = args.dry_run
  self.overwrite = args.overwrite
  self.logger = setup_logger("Show Info", self.verbose)
  self.config, _ = load_config(args.config)
  self.details = args.details
  self.filepaths_only = args.filepaths_only
  if not args.allgroups and not args.groups:
    args.allgroups = True
    if not args.filepaths_only:
      print("No group name or '--allgroups' arguments provided. Defaulting to allgroups=True")
  parse_group_args(self, args)
  self.printgroup = True
  if args.filename is not None:
    self.imagefiles = args.filename
    self.printgroup = False
