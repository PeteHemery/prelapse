# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# genconfig/argument_parser.py

import os

from ..common import backup_prelapse_file, setup_logger, get_pwd
from ..configs import load_config, DEFAULT_CONFIG_FILE_NAME


_DEFAULT_LABELS_TIME = 5.0


def _add_parser_args(parser):
  parser.add_argument("-i", "--inpath", default=".",
                      help="relative path to directory containing images\n(default: %(default)s (current directory))")
  parser.add_argument("-o", "--outpath", default=DEFAULT_CONFIG_FILE_NAME,
                      help="relative path to output file\n(default: %(default)s (under INPATH))\n"
                      "NOTE: Must be on the same file system for relative paths to work in ffmpeg script.")
  parser.add_argument("-d", "--depth", default="1", type=int,
                      help="depth of subdirectory search for image files\n"
                      "(default: %(default)s)")
  parser.add_argument("-t", "--time", dest="bytime", action="store_true",
                      help="sort found images by time order, instead of name\n"
                      "(default: %(default)s)")
  parser.add_argument("-a", "--append", dest="append", action="store_true",
                      help="append existing output file if it already exists\n"
                      "(default: %(default)s)")
  parser.add_argument("-x", "--exclude", nargs='?', action="append",
                      help="exclude string for filenames")
  parser.add_argument("-l", "--labels", dest="labels",  nargs="?", type=str, const="labels.txt",
                      help="optional flag with option parameter. When used, generates an Audacity format labels file\n"
                      "(default: %(const)s (under INPATH))")
  parser.add_argument("-lt", "--labels-time", nargs='?', type=float, const=None,
                      help="Audacity labels format fps for each image\n(default: \"{}\")".format(_DEFAULT_LABELS_TIME))

  parser.set_defaults(bytime=False, append=False)
  return parser


def _parse_args(self, args):
  self.verbose = args.verbose
  self.dry_run = args.dry_run
  self.overwrite = args.overwrite
  self.logger = setup_logger("Configuration Generator", self.verbose)
  self.files = []
  pwd = get_pwd()
  # Sanity checks
  inpath = args.inpath if os.path.isabs(args.inpath) else \
    os.path.abspath(os.path.join(pwd, args.inpath))
  if not os.path.exists(inpath):
    raise RuntimeError("Input path appears to be invalid: '{}'".format(inpath))
  self.inpath = inpath
  outpath = os.path.normpath(os.path.join(inpath, args.outpath))
  if os.path.exists(outpath):
    # Could prompt the user to backup here, but wait until the config is being saved
    if args.append:
      self.files, _ = load_config(outpath)
  self.outpath = outpath
  self.root = os.path.dirname(outpath)
  depth = args.depth
  if depth < 0:
    raise RuntimeError("Subdirectory search depth must be a number 0 or higher")
  self.depth = depth
  self.bytime = args.bytime
  self.append = args.append
  self.labels = args.labels
  if args.labels is not None or args.labels_time is not None:
    self.labels = "labels.txt" if args.labels is None else args.labels
    self.labels_time = _DEFAULT_LABELS_TIME if args.labels_time is None else args.labels_time
    outpath = os.path.normpath(os.path.join(inpath, self.labels))
    if os.path.exists(outpath) and not self.dry_run and not self.overwrite:
      if not backup_prelapse_file(outpath):
        print("No backup will be made. Overwriting the labels file.")
    self.labels_outpath = outpath
  self.exclude = args.exclude if args.exclude is not None else None
