# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# runner/argument_parser.py

import os
import tempfile

from ..common import setup_logger, get_pwd
from ..configs import load_config, DEFAULT_CONFIG_FILE_NAME


def _add_parser_args(parser, run=False, out=False):
  parser.add_argument("-c", "--config", default=DEFAULT_CONFIG_FILE_NAME,
            help="Required Markdown config file describing the picture groups\n(default: %(default)s)")
  parser.add_argument("-l", "--labels", default="labels.txt",
            help="path to input Audacity labels file\n(default: %(default)s)")
  parser.add_argument("-f", "--ffconcatfile", nargs="?", type=str, const="prelapse.ffconcat",
            help="Optional flag to specify path to output list file used by ffmpeg concat.\n"
                "Image paths will be relative to list file.\nIf not specified, no file will be produced\n"
                "(default: %(const)s)")
  parser.add_argument("-fd", "--ffconcatfile-fd", nargs="?", type=int, const=0,
            help="Optional flag to specify temporary file descriptor (used for testing)")

  parser.add_argument("-d", "--delimiter", default="|",
            help="delimiter used in labels to separate instructions (default: '%(default)s')\n"
                "NOTE: Cannot use letters or any of the following: '[]:\\/#.'")
  parser.add_argument("-R", "--relative", dest="relative", action="store_false",
            help="disable relative paths and use absolute paths\n(default: %(default)s)")

  parser.add_argument("--ignore-files-dont-exist", dest="enforce_files_exist", action="store_false",
            help="flag to disable the checks that files exist during config parsing")
  parser.set_defaults(relative=True, enforce_files_exist=True)
  parser.add_argument("-V", "--ffloglevel", type=str, default="warning",
    choices=["quiet", "panic", "fatal", "error", "warning", "info", "verbose", "debug", "trace"],
    help="log level for ffplay/ffmpeg\n(default: %(default)s)")
  if run or out:
    parser.add_argument("-a", "--audiofile", help="path to audio file (optional)")
    parser.add_argument("-r", "--fps", "--framerate", dest="fps", default="25", type=float,
              help="output file frames per second rate\n(default: %(default)s)")
    parser.add_argument("-w", "--width", default="1280", type=int,
              help="output scaled width in pixels\n(default: %(default)s)")
    parser.add_argument("-x", "--aspectratio", default="4/3", type=str,
              help="output aspect ratio (width/height) in form '1.778' or '16/9'\n(default: %(default)s)")
    parser.add_argument("-t", "--tempo", default="1.0", type=float,
              help="output tempo adjustment\n(default: %(default)s)")
    parser.add_argument("-j", "--jump", default="0.0", type=float,
              help="number of seconds into file to jump before playing\n(default: %(default)s)")
    parser.add_argument("-H", "--histogram", dest="histogram", action="store_true",
              help="stack a visual representation of the audio under the video\n(default: %(default)s)")
    parser.add_argument("-M", "--metadata-string", action="store_true",
              help="Optional flag providing string for formatting drawn metadata text over the video.")
    parser.set_defaults(audiofile=None, histogram=False, metadata_string=False)
  if out:
    parser.add_argument("-C", "--codec", default="libx264",
              choices=["libx264", "libx265", "social"],
              help="output file codec\n(default: %(default)s)")
    parser.add_argument("-Q", "--crf", default="18", type=int,
              help="constant Rate Factor. Quality value between 0-51, "
                  "lowest value being highest quality\n(default: %(default)s)")
    parser.add_argument("-o", "--outpath", type=str, required=True, help="path to encoded output file")
    parser.set_defaults(outpath=None)
  return parser


def _parse_aspect_ratio(aspectratio):
  if "/" in aspectratio:
    tmp = aspectratio.split("/")
    if len(tmp) != 2:
      raise RuntimeError("Cannot parse aspect ratio: {}".format(aspectratio))
    try:
      return float(tmp[0]) / float(tmp[1])
    except ValueError:
      pass
  try:
    return float(aspectratio)
  except ValueError:
    pass
  raise RuntimeError("Cannot parse aspect ratio: {}".format(aspectratio))


def _parse_args(self, args, run=False, out=False): # pylint: disable=too-many-branches,too-many-statements
  self.verbose = args.verbose
  self.dry_run = args.dry_run
  self.overwrite = args.overwrite
  self.logger = setup_logger("Runner", self.verbose)
  self.enforce_files_exist = args.enforce_files_exist
  self.config, _ = load_config(args.config, self.enforce_files_exist)
  if not os.path.exists(args.labels):
    raise RuntimeError("Could not find input labels file '{}'".format(args.labels))
  self.labels = args.labels
  pwd = get_pwd()
  if self.dry_run:
    self.ffconcatfile_fd, self.ffconcatfile = int(args.ffconcatfile_fd), args.ffconcatfile
  elif args.ffconcatfile is None:
    self.ffconcatfile_fd, self.ffconcatfile = tempfile.mkstemp(suffix=".ffconcat", dir=pwd)
  else:
    if os.path.exists(args.ffconcatfile):
      self.logger.warning("Overwriting existing ffconcat file: '{}'".format(args.ffconcatfile))
    if os.path.isabs(args.ffconcatfile):
      self.ffconcatfile = args.ffconcatfile
    else:
      self.ffconcatfile = os.path.abspath(os.path.join(pwd, args.ffconcatfile))
    self.ffconcatfile_fd = None
  self.ffloglevel = args.ffloglevel
  self.delimiter = args.delimiter
  self.relative = args.relative
  self.fps = args.fps
  self.histogram = args.histogram
  self.metadata_string = args.metadata_string

  if run or out:
    aspectratio = _parse_aspect_ratio(args.aspectratio)
    height = int((((args.width / aspectratio) * 2) + 0.5) / 2) # Round height to power of 2
    width = int((((height * aspectratio) * 2) + 0.5) / 2) # Recalculate the width
    if width != args.width:
      self.logger.warning("Recalculated width does not match requested width: {0} != {1}\n"
                          "Aspect ratio: {3}, WxH: {1}x{2}".format(args.width, width, height, aspectratio))
    self.aspectratio = aspectratio
    self.height = height
    self.width = width
    self.tempo = args.tempo
    self.jump = args.jump
    if args.audiofile is not None and not os.path.exists(args.audiofile):
      raise RuntimeError("Could not find audio file '{}'".format(args.audiofile))
    self.audiofile = args.audiofile
  if out:
    outpath = args.outpath
    if outpath and os.path.exists(outpath):
      if not self.overwrite:
        raise RuntimeError("Output file already exists '{}'\n"
                            "Add '-y' to enable automatic over writing".format(outpath))
    self.outpath = outpath
    crf = args.crf
    if crf < 0 or crf > 51:
      raise RuntimeError("Invalid crf value. Must be between 0 and 51: {}".format(crf))
    self.crf = crf
    self.codec = args.codec
  else:
    self.outpath = None
    self.codec = None
    self.crf = None
