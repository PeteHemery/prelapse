# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# common/utility_functions.py

from __future__ import print_function, division

import datetime
import logging
import os
import re
import subprocess

from .._version import __version__


def shell_safe_path(path):
  if os.name == "posix":
    return path
  if os.name == "nt":
    return "'{}'".format("{}".format(os.sep * 2).join(path.split(os.sep))).replace(":", "\\:")
  raise RuntimeError("Unknown operating system")


def format_float(num, precision=6):
  return re.sub(r"(\.\d*?[1-9])0+$|\.0+$", r"\1", "{{:.{}f}}".format(precision).format(float(num)))


def setup_logger(component, verbose=False):
  """Setup logger with the given name."""
  logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)
  return logging.getLogger(component)


def parse_group_slice_index(group):
  index = None
  slice_index = None
  if any(x in group for x in [":", "[", "]"]):
    tmp = group.split("[")
    assert len(tmp) == 2
    assert tmp[1][-1] == "]"
    first_label = tmp[0]
    tmp = tmp[1][:-1].split(":")
    num_splits = len(tmp)
    if num_splits > 2:
      raise RuntimeError("Only one ':' char allowed in slice definition: {}".format(group))
    if num_splits < 1:
      raise RuntimeError("Invalid slice/index detected: {}".format(group))
    if num_splits == 1:
      try:
        index = int(tmp[0])
      except ValueError as e:
        raise ValueError("Invalid index detected: {}".format(tmp[0])) from e
    elif num_splits == 2:
      start = None
      stop = None
      try:
        start = int(tmp[0])
      except ValueError:
        pass
      try:
        stop = int(tmp[1])
      except ValueError:
        pass
      if not (start or stop):
        raise RuntimeError("Cannot parse invalid slice label, must provide start and stop values: {}".format(group))
      slice_index = (start, stop)
    else:
      raise RuntimeError("How did you get here?")
    group = first_label
  return group, index, slice_index


def group_append(self, group, index=None, slice_index=None):
  groupindex = self.config.index(group)

  thisgroup = {"name": group.group, "groupindex": groupindex}
  thisgroup["grouptype"] = "config"
  thisgroup["files"] = list(enumerate(self.config[groupindex].items))
  thisgroup["numfiles"] = len(thisgroup["files"])
  try:
    thisgroup["path"] = os.path.dirname(self.config[groupindex].items[0])
  except IndexError:
    self.logger.warning("Empty path in group '{}'".format(thisgroup["name"]))
    thisgroup["path"] = ""
  if index is not None:
    try:
      thisgroup["files"] = [thisgroup["files"][index],]
    except IndexError:
      self.logger.warning("Index {} not within range of group '{}': [0:{}]"
                          .format(index, thisgroup["name"], thisgroup["numfiles"] - 1))
      thisgroup["files"] = []
    thisgroup["grouptype"] = "index_{}".format(index)
    thisgroup["numfiles"] = len(thisgroup["files"])
  elif slice_index is not None:
    thisgroup["files"] = thisgroup["files"][slice_index[0]:slice_index[1]]
    if len(thisgroup["files"]) == 0:
      self.logger.warning("Slices {} not within range of group '{}' [0:{}]"
                          .format(slice_index, thisgroup["name"], thisgroup["numfiles"] - 1))

    thisgroup["grouptype"] = "slice_{}_{}".format(*slice_index)
    thisgroup["numfiles"] = len(thisgroup["files"])
  self.groups.append(thisgroup)


def parse_group_args(self, args):
  if hasattr(args, "allgroups") and not args.allgroups and not args.groups:
    raise RuntimeError("one of the arguments -a/--allgroups -g/--group is required. See -h")
  self.groups = []
  if "allgroups" in args and args.allgroups:
    for group in self.config:
      group_append(self, group)
  else:
    for group in args.groups:
      if group is None:
        raise RuntimeError("required group name not provided")
      group, index, slice_index = parse_group_slice_index(group)
      if group not in self.config:
        raise RuntimeError("group '{}' not in config '{}'".format(group, args.config))
      group_append(self, self.config[self.config.index(group)], index, slice_index)
    if not any(self.groups):
      raise RuntimeError("No groups found in config")


def gen_list_file(files, fps, jump):
  output = "ffconcat version 1.0\n\n"
  output += "stream\nexact_stream_id 0\n"
  inpoint = 0.0
  for file_time in files:
    if file_time[0][:2] == "# ":
      output += "{}\n".format(file_time[0])
      continue
    output += "# {:0.6f}\t{}\n".format(inpoint+jump, file_time[0])
    image = file_time[0].replace("'", "'\\''") # Cope with single quotes in filenames
    output += "file 'file:{}'\n".format(image)
    output += "duration {}\n".format(file_time[1])
    inpoint += float(file_time[1])
    last_file = image
  # One last frame of the last image to indicate EOF
  output += "file 'file:{}'\nduration {:0.03f}\n".format(last_file, 1 / fps)
  return output


def write_list_file(outpath, output, dry_run, fd=None):
  if dry_run:
    print("Dry Run. Generated output:\n\n{}\n".format(output))
  else:
    # Write the output file or temp file descriptor
    with os.fdopen(fd, "wb") if fd is not None else open(outpath, "wb") as f:
      f.write(output.encode("utf-8"))
    print("Written{} '{}'".format(" to fd {}".format(fd) if fd else "", outpath))


def backup_prelapse_file(file_path, overwrite=False):
  # from pdb import set_trace;set_trace()
  print("WARNING: prelapse file already exists:\n'{}'".format(file_path))
  print("Use '-y' to overwrite without being prompted to backup.", end="")
  print(" (Press Ctrl+C to avoid modifying any more files)")
  while True:
    response = input("Would you like to make a back up before over writing? (y/n): ").strip().lower()
    if response:
      if response[0] in ['N', 'n']:
        break
      if response[0] in ['Y', 'y']:
        # Create a timestamp string in local time, e.g. "2024-10-31_23-59-59_BST"
        timestamp = datetime.datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S_%Z")
        backup_path = "{}.{}.bak".format(file_path, timestamp)
        if os.path.exists(backup_path):
          raise RuntimeError("Backup file '{}' already exists.".format(backup_path))
        try:
          os.rename(file_path, backup_path)
          print("Backup created at '{}'".format(backup_path))
        except OSError as e:
          raise OSError("Failed to create backup") from e
        return True

  return False


def get_pwd():
  # Get logical (not physical) path of present working directory,
  # i.e. symlink path not realpath
  if os.name == "posix":
    with subprocess.Popen(["pwd", "-L"], stdout=subprocess.PIPE, shell=True) as proc:
      pwd = "".join(chr(x) for x in proc.communicate()[0].strip())
  elif os.name == "nt":
    with subprocess.Popen(["echo", "%cd%"], stdout=subprocess.PIPE, shell=True) as proc:
      pwd = "".join(chr(x) for x in proc.communicate()[0].strip())
  else:
    raise RuntimeError("Unhandled system, not posix or nt: {}".format(os.name))
  return pwd


def build_basic_ff_cmd(out_args, ffloglevel, verbose):
  cmd = "ffmpeg" if out_args else "ffplay -autoexit -noframedrop -fflags +genpts+fastseek"
  cmd += " -hide_banner -loglevel -repeat+{}".format(ffloglevel)
  cmd += " -{}stats".format(
    "" if verbose or ffloglevel not in ["quiet", "verbose", "debug", "trace"] else "no")

  return cmd.split()


def build_output_ff_cmd(out_args):
  overwrite, fps, codec, crf, audiofile, outpath = out_args

  cmd = " -fps_mode cfr"
  cmd += " -r {}".format(fps)
  cmd += " -framerate {}".format(fps)
  cmd += " -pixel_format yuv420p"


  if codec == "libx264":
    cmd += " -c:v {}".format(codec)
    cmd += " -preset slow"
    cmd += " -crf {}".format(crf)
    cmd += " -profile:v high"
    cmd += " -level:v 4.2"
    cmd += " -pix_fmt yuv420p"
    cmd += " -x264-params keyint=72:min-keyint=72:scenecut=0"
    cmd += " -movflags +faststart+frag_keyframe+empty_moov+default_base_moof"
  elif codec == "libx265":
    cmd += " -c:v {}".format(codec)
    cmd += " -x265-params b-pyramid=0:scenecut=0:crf={}".format(crf)
  elif codec == "social":
    cmd += " -c:v libx264"
    cmd += " -profile:v high"
    cmd += " -level:v 3.1"
    cmd += " -pix_fmt yuv420p"
    cmd += " -b:v 1275k"
    cmd += " -x264-params keyint=72:min-keyint=72:scenecut=0"
    cmd += " -movflags +faststart+frag_keyframe+empty_moov+default_base_moof"
  else:
    raise RuntimeError("Invalid codec selection: {}".format(codec))

  if audiofile:
    cmd += " -c:a aac -b:a 128k"

  if overwrite:
    cmd += " -y"

  runcmd = cmd.split()
  runcmd += ["-metadata:s:v:0", "encoder='{}'".format("prelapse {} by Pete Hemery".format(__version__))]
  runcmd += ["-metadata", "comment='{}'".format("Created with prelapse {}".format(__version__))]
  runcmd += ["-metadata", "title='{}'".format(".".join(os.path.basename(outpath).split(".")[:-1]))]
  runcmd += ["-metadata", "date='{}'".format(datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"))]

  return runcmd


def build_ff_cmd(ffloglevel, verbose, filter_complex, out_args):
  runcmd = build_basic_ff_cmd(out_args, ffloglevel, verbose)
  runcmd += ["-f", "lavfi"]
  if verbose:
    runcmd += ["-dumpgraph", "1"]
  runcmd += ["-i", '"{}"'.format(filter_complex)]
  # If there are output arguments, build the output-specific part
  if out_args:
    if isinstance(out_args, (tuple, list)) and len(out_args) > 2:
      runcmd += build_output_ff_cmd(out_args)
    elif out_args != "stab":
      raise RuntimeError("Unknown output args: '{}'".format(out_args))

  return runcmd
