# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# configs/configs.py

from __future__ import print_function, division

import datetime
import os
import re

from locale import getpreferredencoding

RELATIVE_LINE_PATTERN = re.compile(r"^(\s+-\s*)(.*)$")

# Define a class to represent the image groups
class ImageGroup:
  def __init__(self, group):
    self.group = group
    self.items = []  # list to hold paths and files in order

  def __repr__(self):
    # return "ImageGroup(group='{}', items={})".format(self.group, pformat(self.items))
    return "'{}'".format(self.group)

  def __eq__(self, other):
    if isinstance(other, str):
      return self.group == other
    return False

  def __hash__(self):
    return hash(self.group)


def process_group_header(line, current_group, groups):
  """Process a group header line. Append the previous group to the groups list."""
  if current_group:
    groups.append(current_group)
  # Assume the title follows '# ' (skip the first two characters)
  return ImageGroup(line[2:])


def process_absolute_line(line, i, enforce_files_exist):
  """
  Process a line starting with '- ' which must be an absolute path or a directory.
  Returns a tuple (path, is_directory) where if is_directory True, then a path
  separator may be appended.
  """
  abs_path = line[2:]
  if enforce_files_exist and not os.path.exists(abs_path):
    raise RuntimeError("'{}' on line {} does not exist.".format(abs_path, i+1))

  if os.path.isdir(abs_path):
    # Ensure directory has a trailing separator
    if not abs_path.endswith(os.sep):
      abs_path += os.sep
    return abs_path, True
  if not os.path.isabs(abs_path):
    raise RuntimeError("Lines starting with '- ' must be an absolute file or directory path.\n{}:{}".format(i+1, line))
  return abs_path, False


def process_relative_line(line, filename, i, current_path, enforce_files_exist):
  """
  Process a line starting with '  - ' which specifies a relative filename.
  Returns the complete path.
  """
  if current_path is None:
    raise RuntimeError("Relative path file without current path for group on line {}.".format(i+1))

  if os.path.isabs(filename):
    raise RuntimeError("Lines starting with '  - ' must be relative file path.\n{}:{}".format(i+1, line))

  rel_path = os.path.join(current_path, filename)
  if enforce_files_exist and not os.path.exists(rel_path):
    print("File '{}' on line {} cannot be found. Skipping.".format(rel_path, i+1))
    return None
  return rel_path

# Function to parse Markdown format
def parse_markdown(markdown_data, enforce_files_exist=True):
  groups = []
  lines = markdown_data.splitlines()
  current_group = None
  current_path = None

  for i, line in enumerate(lines):
    line = line.rstrip()
    if not line or line[0] == "<":
      continue # skip blank and comment lines
    if line.startswith("# "):
      # Start a new group: push the existing group and create a new one.
      current_group = process_group_header(line, current_group, groups)
      current_path = None
    elif line.startswith("- "):
      abs_path, is_dir = process_absolute_line(line, i, enforce_files_exist)
      if is_dir:
        # This indicates that following relative lines belong to this directory.
        current_path = abs_path
      else:
        # Add the file directly to the current group
        if current_group is None:
          raise RuntimeError("File found outside of a group on line {}.".format(i+1))
        current_group.items.append(abs_path)
    else:
      match = re.match(RELATIVE_LINE_PATTERN, line)
      if match:
        rel_path = process_relative_line(line, match[2], i, current_path, enforce_files_exist)
        if rel_path and current_group:
          current_group.items.append(rel_path)
      else:
        # Optionally handle unexpected line formats here.
        print("Warning: Unrecognized line format at line {}: {}".format(i+1, line))

  # Make sure to add the last group if it exists.
  if current_group:
    groups.append(current_group)

  return groups


def print_relative_path_files(relative_path_files, current_path):
  lines = ""
  num_path_files = len(relative_path_files)
  if not current_path.endswith(os.sep):
    current_path += os.sep

  if num_path_files > 1:
    lines += "- {}\n".format(current_path)
    for filename in relative_path_files:
      lines += "  - {}\n".format(filename)

  elif num_path_files == 1:
    lines += "- {}\n".format(os.path.join(current_path, relative_path_files[0]))
  # print("num_path_files {}, relative_path_files {}, current_path {}".format(
  #   num_path_files, relative_path_files, current_path))
  # print(lines)
  return lines


# Function to encode list of ImageGroup objects to Markdown format
def encode_to_markdown(groups):
  lines = []
  for i, group in enumerate(groups):
    if i > 0:
      lines.append("\n")
    lines.append("# {}\n".format(group.group))
    current_path = None
    paths = []
    relative_path_files = []

    for item in group.items:
      path, filename = os.path.split(item)
      paths.append((path, filename))
    for i, path in enumerate(paths):
      if current_path is None:
        current_path = path[0]
      if path[0] == current_path:
        relative_path_files.append(path[1])
      else:
        lines.append(print_relative_path_files(relative_path_files, current_path))
        relative_path_files = []
        relative_path_files.append(path[1])
        current_path = path[0]
    lines.append(print_relative_path_files(relative_path_files, current_path))

  return "".join(lines)


# Example usage
EXAMPLE_MARKDOWN_DATA = '''
<!-- comment -->
# Vacation Photos
- /images/vacation/day1/
  - beach.jpg
  - sunset.jpg
- /images/vacation/other/cityscape.jpg
- /images/vacation/day2
  - hiking.jpg
  - campfire.jpg
- /images/vacation/other/wildlife.jpg

# Group Name 1
- /absolute/path/to/images/
  - image1.jpg
  - image2.jpg

# Group Name 2
- /absolute/path/to/one/image3.jpg
- /absolute/path/to/two/image4.jpg
'''


# Load Markdown config file.
def load_config(config_path, enforce_files_exist=True):
  if not os.path.exists(config_path):
    raise RuntimeError("Could not find config file '{}'".format(config_path))
  # Allow reading from subshell file redirection for the config.
  if os.path.isfile(config_path) and not config_path.endswith(".md"):
    raise RuntimeError("Config file '{}' must have .md extension".format(config_path))
  with open(config_path, "r", encoding=getpreferredencoding(False)) as f:
    md_text = f.read()

  markdown_groups = parse_markdown(md_text, enforce_files_exist) # Parse Markdown
  return markdown_groups, config_path


def backup_config(config_path):
  # Create a timestamp string in local time, e.g. "2024-10-31_23-59-59_BST"
  timestamp = datetime.datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S_%Z")
  backup_path = "{}.{}.bak".format(config_path, timestamp)
  if os.path.exists(backup_path):
    raise RuntimeError("Backup file '{}' already exists.".format(backup_path))
  try:
    os.rename(config_path, backup_path)
    print("Backup created at '{}'".format(backup_path))
  except OSError as e:
    raise OSError("Failed to create backup") from e


def save_config(config_path, config, overwrite=False, dryrun=False):
  if os.path.exists(config_path) and not dryrun and not overwrite:
    print("WARNING: Config file already exists:\n'{}'".format(config_path))
    print("Use '-y' to overwrite without being prompted to backup.")
    response = input("Would you like to back it up before over writing? (y/n): ").strip().lower()
    if response and response[0] in ['Y', 'y']:
      backup_config(config_path)
    else:
      print("No backup will be made. Overwriting the config file.")

  if not config_path.endswith(".md"):
    raise RuntimeError("Config file '{}' must have .md extension".format(config_path))
  # Encode to Markdown and write to file
  markdown_data = "<!-- prelapse config generated: {} -->\n".format(
    datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"))
  markdown_data += encode_to_markdown(config)
  if dryrun:
    print("{}\nDry run".format(markdown_data))
  else:
    with open(config_path, "w", encoding=getpreferredencoding(False)) as file:
      file.write(markdown_data)
    print("Markdown written to {}".format(config_path))
