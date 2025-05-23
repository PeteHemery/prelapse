# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# modifier/label_modifier.py

from __future__ import print_function, division

import os


def modify_lines(self, args, lines):
  modified_lines = []
  for i, line in enumerate(lines):
    # Split the line into columns
    columns = line.strip().split("\t")

    if args.shorten:
      if len(columns) < 3:
        raise RuntimeError("Labels file '{}' doesn't have 3 columns\n{}".format(args.labels, line.strip()))
      if columns[0] != columns[1]:
        self.logger.warning("Timestamps for label on line {} do not match!\n{}".format(i, lines[i].strip()))
      # Remove the first column and join the remaining columns
      modified_line = "\t".join(columns[1:])

    elif args.lengthen:
      if len(columns) != 2:
        raise RuntimeError("Labels file '{}' doesn't have 2 columns\n{}".format(args.labels, line.strip()))

      # Duplicate the first column and join the remaining columns
      modified_line = "\t".join([columns[0],] + columns)
    else:
      raise RuntimeError("See usage with -h")

    if args.dry_run:
      print(modified_line)
    else:
      self.logger.debug(modified_line)
    modified_lines.append(modified_line + "\n")
  return modified_lines


def run_labels(self, args):
  self.parse_args(args, "Label Modifier")
  if not os.path.exists(args.labels):
    raise RuntimeError("Labels file '{}' does not exist".format(args.labels))
  with open(args.labels, "rb") as input_file:
    # Read the contents of the file
    lines = input_file.readlines()
  if args.dry_run:
    self.logger.info("Only dry run")
  self.logger.debug(lines)
  modified_lines = modify_lines(self, args, lines)
  self.logger.debug(modified_lines)
  if not args.dry_run:
    with open(args.labels, "wb") as output_file:
      # Iterate through each line
      for line in modified_lines:
        # Write the modified line to the output file
        output_file.write(line.encode("utf-8"))
