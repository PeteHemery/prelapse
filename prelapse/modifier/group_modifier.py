# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# modifier/group_modifier.py

from __future__ import print_function, division

import glob
import mimetypes
import os

from pprint import pformat

from ..common import parse_group_args
from ..configs import save_config, ImageGroup


def rename_group(self, args):
  from_group = args.fromgroup
  to_group = args.togroup

  if from_group not in self.config:
    raise RuntimeError("'From' group name not in config: '{}'\nExisting groups: {}"
                        .format(from_group, pformat([x.group for x in self.config])))
  if to_group in self.config:
    raise RuntimeError("'To' group name already in config: '{}'\nExisting groups: {}"
                        .format(to_group, pformat([x.group for x in self.config])))
  for i, group in enumerate(self.config):
    if group == from_group:
      self.config[i].group = to_group
      break
  if self.dry_run:
    self.logger.warning("Dry run: Not renaming groups in config.\n"
      "Use -v to see updated config")
    self.logger.info(pformat(self.config, compact=True, sort_dicts=False))
  else:
    save_config(self.configfile, self.config, self.overwrite)
  self.logger.info("Renamed '{}' to '{}'".format(from_group, to_group))


def delete_group(self, args):
  if args.groups is None:
    raise RuntimeError("Must specify at least one group")
  self.logger.debug(args.groups)
  for group in args.groups:
    if group not in self.config:
      raise RuntimeError("Group name not in config: '{}'".format(group))
    del self.config[self.config.index(group)]
  if self.dry_run:
    self.logger.warning("Dry run: Not deleting groups from config.\n"
      "Use -v to see updated config")
    self.logger.info(pformat(self.config, compact=True, sort_dicts=False))
  else:
    save_config(self.configfile, self.config, self.overwrite)
  self.logger.info("parsed del")


def check_for_image_files(self, files):
  items = []
  for file_path in files:
    if not os.path.exists(file_path):
      self.logger.warning("Specified file does not exist: {}".format(file_path))
      continue
    type_guess = mimetypes.guess_type(file_path)
    if not (type_guess[0] and type_guess[0].startswith("image")):
      continue
    items.append(os.path.realpath(file_path))
  return items


def populate_group_items(self, args):
  items = []

  if args.groups is not None:
    parse_group_args(self, args)
    for group in self.groups:
      items += [f[1] for f in group["files"]]

  if args.search_path is not None:
    search_pattern = os.path.join(args.search_path, "*")
    found_files = check_for_image_files(self, glob.glob(search_pattern))
    if not found_files:
      self.logger.warning("No files found in search path: {}".format(args.search_path))
    else:
      items += found_files

  # If specific files are provided, add them.
  if args.files is not None:
    found_files = check_for_image_files(self, args.files)
    if not found_files:
      self.logger.warning("No files found in list provided: {}".format(args.files))
    else:
      items += found_files

  # Remove duplicates while preserving order.
  seen = set()
  unique_items = []
  for item in items:
    if item not in seen:
      seen.add(item)
      unique_items.append(item)
  return unique_items


def new_group(self, args):
  if args.groupname in self.config:
    raise RuntimeError("New group name already in config: '{}'".format(args.groupname))
  # Require at least one method to supply items: groups to copy, search path, or files.
  if args.groups is None and args.search_path is None and args.files is None:
    raise RuntimeError("Must specify at least one of --group, --path, or --files to build new group")

  fresh_group = ImageGroup(args.groupname)
  fresh_group.items = populate_group_items(self, args)
  self.config.append(fresh_group)
  self.logger.debug("'{}':\n {}".format(self.config[-1].group, fresh_group.items))
  if not fresh_group.items:
    raise RuntimeError("No accessible files provided for new group: '{}'".format(args.groupname))

  save_config(self.configfile, self.config, self.overwrite, self.dry_run)

  if self.dry_run:
    self.logger.warning("Dry run: Not writing new group to config.\n"
      "Use -v to see updated config")
    self.logger.info(pformat(self.config, compact=True, sort_dicts=False))
  else:
    print("Written {}".format(self.configfile))
  self.logger.info("parsed new")


def run_group(self, args):
  self.parse_args(args, "Group Modifier")
  if args.modgrp is None:
    raise RuntimeError("Must select a sub-command. See usage with -h")

  if args.modgrp == "rename":
    rename_group(self, args)
  elif args.modgrp == "del":
    delete_group(self, args)
  elif args.modgrp == "new":
    new_group(self, args)
