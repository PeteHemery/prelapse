# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# common/shell.py

from __future__ import print_function, division

import os
import subprocess
import sys


def call_shell_command(cmd, exit_on_error=True, dry_run=False):
  if dry_run:
    print("Dry run, not executing command:\n{}".format(" ".join(cmd)))
    return 0

  print("Running:\n{}\n".format(" ".join(cmd)))
  set_env_for_command(cmd)
  # Filter out the quotes around the -i parameter,
  # only used for the print above
  # and subprocess doesn't like them there
  cmd = sanitize_command(cmd)
  try:
    with subprocess.Popen(cmd, stderr=subprocess.PIPE, stdin=sys.stdin) as process:
      try:
        process_command_output(process)
        handle_process_exit(process, cmd, exit_on_error)
      except KeyboardInterrupt:
        handle_keyboard_interrupt(process, cmd)
  except Exception as e: # pylint: disable=broad-exception-caught
    print("Encountered error:\n{}".format(e))
    return 1
  return process.returncode


def set_env_for_command(cmd):
  # Force colored output while piping to stderr
  if cmd[0] in ["ffmpeg", "ffplay"] and os.name != "nt":
    os.environ["AV_LOG_FORCE_COLOR"] = "1"


def sanitize_command(cmd):
  return [c.replace('"', '') if '"' in c else c for c in cmd]


def process_command_output(process):
  output = ""
  while True:
    char = process.stderr.read(1).decode("utf-8", errors="replace")
    if char == "" and process.poll() is not None:
      if output:
        sys.stdout.write("\n")
      sys.stdout.flush()
      break
    if char:
      output += char
      if char in ["\n", "\r"]:
        handle_special_output(output, process)
        output = ""


def handle_special_output(output, process):
  # Catch pixel format change, avoid hanging.
  if "Format changed yuvj" in output:
    handle_pixel_format_change(output, process)
  # Avoid printing annoying warning, that can be ignored anyway
  elif "deprecated pixel format used" not in output and "EOF timestamp not reliable" not in output:
    sys.stdout.write(output)
    sys.stdout.flush()


def handle_pixel_format_change(output, process):
  #First line clears formatting of the terminal from aborted command
  sys.stdout.write("""
{}\033[00m
\033[31m WARNING: Incompatible pixel format detected. \033[00m

ffconcat requires all input images in a group to have matching pixel formats,
including chroma subsampling (e.g., YCbCr4:2:0 vs YCbCr4:4:4).
Inconsistent formats cause ffplay to repeatedly log errors and consume CPU,
leading to a potential hang.

To resolve:

1. Identify the problematic group at the timestamp above.

2. Inspect image metadata using e.g. exiftool on Linux:
     exiftool "image.jpg"
   Look for the line:
     Y Cb Cr Sub Sampling

   Common values include:
     - YCbCr4:4:4 (1 1)
     - YCbCr4:2:0 (2 2)

3. Normalize pixel formats:
   a. Modify files in-place:
        {1}mogrify -sampling-factor 4:2:0 "image.jpg"
   b. Or, to preserve originals:
        mkdir resampled
        {1}mogrify -path resampled -sampling-factor 4:2:0 "image.jpg"

   Then update the group's path to include "/resampled".


See this link for information about chroma subsampling:
  https://matthews.sites.wfu.edu/misc/jpg_vs_gif/JpgCompTest/JpgChromaSub.html

Aborting to prevent repeated error spam and excessive CPU usage.

""".format(output, "magick " if os.name == "nt" else ""))
  sys.stdout.flush()
  process.terminate()
  raise RuntimeError("Unresolvable pixel format mismatch")


def handle_process_exit(process, cmd, exit_on_error):
  if process.returncode != 0:
    exit_msg = "Process:\n{}\nterminated with status: {}".format(" ".join(cmd), process.returncode)
    print(exit_msg)
    if exit_on_error:
      # raise RuntimeError(exit_msg)
      sys.exit(process.returncode)


def handle_keyboard_interrupt(process, cmd):
  if process.returncode != 0:
    raise RuntimeError("Process:\n{}\nterminated with status: {}".format(" ".join(cmd), process.returncode))
  sys.exit()
