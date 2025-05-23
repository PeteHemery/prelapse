# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# modifier/image_modifier.py

from __future__ import print_function, division

import mimetypes
import os

from pprint import pformat

from ..common import parse_group_args, gen_list_file, write_list_file, \
  call_shell_command, build_ff_cmd, shell_safe_path
from ..configs import save_config, ImageGroup


def build_suffix_from_instruction(instruction, args):
  if not args.outmod:
    return ""

  if any(x in instruction for x in ["resize", "scale", "crop"]):
    return _build_custom_suffix(instruction, args, {
      "geometry": "-G{}".format(args.geometry),
      "max": "-m{}".format(args.max),
      "percent": "-p{}".format(args.percent),
    })
  if instruction == "color":
    # For color, do not break so that multiple options might be appended.
    return _build_custom_suffix(instruction, args, {
      "normalize": "-normalize",
      "autolevel": "-autolevel",
      "autogamma": "-autogamma",
    }, False)
  if instruction == "rotate":
    return _build_custom_suffix(instruction, args, {
      "autoorient": "-autoorient",
      "clockwise": "-clockwise",
      "anticlockwise": "-anticlockwise",
      "degrees": "-degrees",
    })
  raise RuntimeError("Unknown instruction: {}".format(instruction))


def _build_custom_suffix(instruction, args, mapping, mutex=True):
  suffix = instruction

  # Loop over the provided keys in the mapping. Use the first one that applies (if mutex).
  for key, val in mapping.items():
    if hasattr(args, key) and getattr(args, key):
      suffix += val
      if mutex:
        break
  else:
    # If none of the keys were set on args, we fail.
    raise RuntimeError("Unknown {} option".format(instruction))
  return suffix


def get_size_amount(instruction, args):
  # For resize/scale/crop instructions
  options = {
    "geometry": "{}".format(args.geometry),
    "max": "{0}x{0}>".format(args.max),
    "percent": "{}%".format(args.percent)
  }
  for key, val in options.items():
    if key in args.__dict__ and getattr(args, key):
      return val
  raise RuntimeError("Unknown {} option".format(instruction))


def get_color_options(args):
  # For color instruction options
  color_opts = {
    "normalize": "-normalize",
    "autolevel": "-autolevel",
    "autogamma": "-autogamma"
  }
  opts = []
  for key, val in color_opts.items():
    if key in args.__dict__ and getattr(args, key):
      opts.append(val)
  if not opts:
    raise RuntimeError("No color action requested. See -h for usage")
  return opts


def get_rotate_options(args):
  # For rotate instruction options
  rotate_opts = {
    "autoorient": ["-auto-orient"],
    "clockwise": ["-rotate", "90"],
    "anticlockwise": ["-rotate", "-90"],
    "degrees": ["-background", "black", "-rotate", args.degrees]
  }
  for key, val in rotate_opts.items():
    if key in args.__dict__ and getattr(args, key):
      return val
  raise RuntimeError("Unknown rotate option")


def build_cmd_for_group(self, group, instruction, args, suffix):
  """
  Build the mogrify command for a single group.
  Returns the command list.
  """
  cmd = ["mogrify", "-verbose"]
  if os.name == "nt":
    cmd = ["magick"] + cmd
  group_name = group["name"]
  if suffix:
    group_name += "-{}".format(suffix)


  print("Processing group '{}':\n{}".format(group_name, pformat(group)))

  if args.outmod:
    modpath = os.path.join(group["path"], "mod-{}".format(suffix))
    if not self.dry_run:
      os.makedirs(modpath, exist_ok=True)
    cmd += ["-path", modpath]
    group["modpath"] = modpath

  # Add instruction-specific options.
  if instruction in ["resize", "scale", "crop"]:
    size_amount = get_size_amount(instruction, args)
    if instruction == "scale" and not args.max:
      # The scale case requires background and extent modification.
      cmd += ["-{}".format(instruction), size_amount,
          "-background", "black", "-extent", size_amount]
    else:
      cmd += ["-{}".format(instruction), size_amount]
  elif instruction == "color":
    cmd += get_color_options(args)
  elif instruction == "rotate":
    cmd += get_rotate_options(args)
  else:
    # For instructions that are not a special case, add directly.
    if not any(x in instruction for x in ["color", "rotate"]):
      cmd += ["-{}".format(instruction)]

  # Gravity parameter is common to many instructions.
  cmd += ["-gravity", args.gravity]
  for f in group["files"]:
    full_path = os.path.join(group["path"], f[1])
    cmd.append(full_path)
  return cmd, group_name


def process_generated_group(self, group, group_name):
  """
  After running the mogrify command, process the generated images.
  Update self.config accordingly and save the config file.
  """
  gen_files = []
  dirlist = sorted(os.listdir(group["modpath"]))
  for item in dirlist:
    item_full_path = os.path.join(group["modpath"], item)
    if os.path.isfile(item_full_path):
      type_guess = mimetypes.guess_type(item)
      if type_guess[0] and type_guess[0].startswith("image"):
        gen_files.append(item)
  if group_name in self.config:
    # Update existing group in the config
    index = self.config.index(group_name)
    this_group = self.config[index]
    # Assuming this_group.items is a list of file paths.
    for f in gen_files:
      fullpath = os.path.join(group["modpath"], f)
      if fullpath not in this_group.items:
        this_group.items.append(fullpath)
    this_group.items = sorted(this_group.items)
  else:
    # Create a new group.
    new_group = ImageGroup(group_name)
    new_group.items = [os.path.join(group["modpath"], x) for x in gen_files]
    self.config.append(new_group)
  save_config(self.configfile, self.config, overwrite=True)
  print("Written new group '{}' to config file {}".format(group_name, self.configfile))


def run_mogrify_cmd(self, args):
  self.parse_args(args, "Image Modifier")
  # Validate sub-command
  if args.modimg is None:
    raise RuntimeError("Must select a sub-command. See usage with -h")

  if args.modimg == "stab":
    self.logger.info("parsed stab")
    run_image_stab(self, args)
    return

  # Only log allowed commands.
  for cmd in ["resize", "scale", "crop", "color", "rotate"]:
    if args.modimg == cmd:
      self.logger.info("parsed {}".format(cmd))
      break
  self.logger.info(args)

  # Process group arguments
  parse_group_args(self, args)
  instruction = args.modimg

  # Specific check for color instruction.
  if instruction == "color" and not any([args.normalize, args.autolevel, args.autogamma]):
    raise RuntimeError("No color action requested. See -h for usage")

  suffix = build_suffix_from_instruction(instruction, args)

  # Process each group.
  for group in self.groups:
    cmd, group_name = build_cmd_for_group(self, group, instruction, args, suffix)
    if self.dry_run:
      self.logger.warning("Dry run: Not running command:\n '{}' \nNot writing new group '{}' to config {}"
                .format(" ".join(cmd), group_name, self.configfile))
    else:
      shell_ret = call_shell_command(cmd)
      if shell_ret:
        print("Shell command failed with return code: {}".format(shell_ret))
        return
      if args.outmod:
        process_generated_group(self, group, group_name)


def run_image_stab(self, args):
  if args.modstabphase is None:
    raise RuntimeError("Must select a sub-command. See usage with -h")
  self.logger.info("Image Stabilization Modifier")
  parse_group_args(self, args)
  for group in self.groups:
    if "1" in args.modstabphase:
      shell_ret = call_shell_command(build_phase1_cmd(self, args, group))
      if shell_ret:
        print("Shell command failed with return code: {}".format(shell_ret))
        return
      self.logger.info("parsed stab 1")
    if "2" in args.modstabphase:
      shell_ret = call_shell_command(build_phase2_cmd(self, args, group))
      if shell_ret:
        print("Shell command failed with return code: {}".format(shell_ret))
        return
      self.logger.info("parsed stab 2")


def handle_list_file(self, files, fps, list_file):
  list_file_content = gen_list_file([[f[1], 1.0 / fps] for f in files], fps, 0)
  write_list_file(list_file, list_file_content, self.dry_run)
  self.logger.info("Written list file: {}".format(list_file))


def build_phase1_cmd(self, args, group):
  list_file = os.path.join(group["path"], group["name"] + ".ffconcat")
  if not self.dry_run:
    handle_list_file(self, group["files"], args.fps, list_file)

  options_string = "movie={}:f=ffconcat:si=0:format_opts='safe=0\\:auto_convert=0',".format(shell_safe_path(list_file))
  options_string += "fps={:0.3f}:eof_action=pass,".format(args.fps)
  options_string += "vidstabdetect="
  if args.result:
    options_string += "result={}".format(args.result)
  else:
    transforms_path = os.path.join(
      group["path"], "stable", "transforms.trf")
    options_string += "result={}".format(transforms_path)
    if not self.dry_run:
      os.makedirs(os.path.dirname(transforms_path), exist_ok=True)
  options_string += ":shakiness={}".format(args.shakiness)
  options_string += ":accuracy={}".format(args.accuracy)
  options_string += ":stepsize={}".format(args.stepsize)
  options_string += ":mincontrast={}".format(args.mincontrast)
  options_string += ":tripod={}".format(args.tripod)
  options_string += ":show={}".format(args.show)

  cmd = build_ff_cmd(args.ffloglevel, args.verbose, options_string, None if args.play else "stab")
  if not args.play:
    cmd += ["-f", "null", "-"]
  return cmd


def build_phase2_cmd(self, args, group):
  outpath = group["path"]
  list_file = os.path.join(outpath, group["name"] + "_stabilize.ffconcat")
  if not self.dry_run:
    handle_list_file(self, group["files"], args.fps, list_file)

  options_string = "movie={}:f=ffconcat:si=0:format_opts='safe=0\\:auto_convert=0',".format(shell_safe_path(list_file))
  options_string += "fps={:0.3f}:eof_action=pass,".format(args.fps)
  options_string += "vidstabtransform="
  if args.input:
    transforms_path = args.input
  else:
    transforms_path = os.path.join(outpath, "stable", "transforms.trf")
  if not os.path.exists(transforms_path):
    raise RuntimeError("transforms file does not exist: {}"
                        .format(transforms_path))
  options_string += "input={}".format(transforms_path)
  options_string += ":smoothing={}".format(args.smoothing)
  options_string += ":optalgo={}".format(args.optalgo)
  options_string += ":maxshift={}".format(args.maxshift)
  options_string += ":maxangle={}".format(args.maxangle)
  options_string += ":crop={}".format(args.crop)
  options_string += ":invert={}".format(args.invert)
  options_string += ":relative={}".format(args.relative)
  options_string += ":zoom={}".format(args.zoom)
  options_string += ":optzoom={}".format(args.optzoom)
  options_string += ":zoomspeed={}".format(args.zoomspeed)
  options_string += ":interpol={}".format(args.interpol)
  options_string += ":tripod={}".format(args.virtualtripod)
  options_string += ":debug={},".format(args.debug)
  options_string += "unsharp="
  options_string += "lx={}".format(args.lx)
  options_string += ":ly={}".format(args.ly)
  options_string += ":la={}".format(args.la)
  options_string += ":cx={}".format(args.cx)
  options_string += ":cy={}".format(args.cy)
  options_string += ":ca={}".format(args.ca)

  cmd = build_ff_cmd(args.ffloglevel, args.verbose, options_string, None if args.play else "stab")
  if args.writejpgs:
    template = "output_%0{}d.jpg".format(len(str(len(group["files"]))))
    cmd += ["-qscale:v", "2", "{}".format(os.path.join(outpath, "stable", template))]
  return cmd
