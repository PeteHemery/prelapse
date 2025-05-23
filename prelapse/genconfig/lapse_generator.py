# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# genconfig/lapse_generator.py

"""
Generate Markdown config file for use with Audacity to ffmpeg converter script.

Select path to directory containing image files.
Resulting config file will consist of image files grouped by directory.
"""

from __future__ import print_function, division

import mimetypes
import os

from .argument_parser import _add_parser_args, _parse_args
from ..configs import save_config, ImageGroup


class LapseGenerator(): # pylint: disable=no-member
  """ Group config generator class """

  add_parser_args = staticmethod(_add_parser_args)
  parse_args = classmethod(_parse_args)

  def populate_files(self, path, current_depth=0):
    """
    Populate a list with recursive search for image files from the root down to a maximum depth.
    """
    thisdir = os.path.relpath(path, start=self.root)
    if thisdir == ".":
      thisdir = path
    index = next((i for i, p in enumerate(self.files) if p == thisdir), None)
    if os.path.realpath(thisdir) == os.path.realpath(self.root):
      thisdir = os.path.basename(self.root) # Use the basename of the root dir, instead of '.'
      if thisdir in self.files:# and self.files[thisdir]["path"] == self.root:
        # Already processed root directory
        return
    else:
      if thisdir in self.files:
        if index is not None:
          if self.files[index] == path:
            # Already processed this directory
            return
          raise RuntimeError("Cannot distinguish labels from directories with the same name:\n"
            "  {}\n  {}\n".format(self.files[index], path))
    dirlist = sorted(os.listdir(path), key=lambda name:
                      os.path.getmtime(os.path.join(path, name))
                      ) if self.bytime else sorted(os.listdir(path))

    self._recursive_populate(thisdir, dirlist, path, current_depth)

  def _recursive_populate(self, thisdir, dirlist, path, current_depth):
    for item in dirlist:
      item_path = os.path.join(path, item)
      index = next((i for i, p in enumerate(self.files) if p == thisdir), None)
      if os.path.isdir(item_path):
        if current_depth < self.depth:
          self.populate_files(item_path, current_depth + 1)
      if not os.path.isfile(item_path):
        continue
      type_guess = mimetypes.guess_type(item)
      if not (type_guess[0] and type_guess[0].startswith("image")):
        continue

      # Skip excluded strings
      if self.exclude is not None:
        if None in self.exclude:
          raise RuntimeError("Must have value for excluded string")
        excluded_strings = [x for x in self.exclude if x in item_path]
        if any(excluded_strings):
          if self.verbose:
            print("excluded strings {} in item '{}'".format(excluded_strings, item_path))
          continue
      # Found an image file, if it's the first discovery of files in this
      # directory then create a new dict entry, else just append to it
      if thisdir not in self.files:
        new_group = ImageGroup(thisdir)
        new_group.items.append(item_path)
        self.files.append(new_group)
      else:
        self.files[index].items.append(item_path)

  def run_generator(self, args):
    """
    Populate the files dict with group info
    """
    self.parse_args(args)
    self.populate_files(self.inpath)

    if self.files:
      file_extension = self.outpath.split(".")[-1].lower()
      if file_extension != "md":
        raise RuntimeError("Invalid file extension for outpath. Must end with .md")
      if self.labels is not None:
        time_cnt = 0
        labels_output = ""
        for group in self.files:
          group_data = group.items
          ttime = len(group_data) * (1/self.labels_time)
          self.logger.debug("Group '{}' with {} images, {:.6f} sec at {} fps"
                            .format(group.group, len(group_data), ttime, self.labels_time))
          labels_output += "{:.6f}\t{}\n".format(time_cnt, group.group)
          time_cnt += ttime
        labels_output += "{:.6f}\tend\n".format(time_cnt)
        if self.dry_run:
          print("{}\nDry run {}".format(labels_output, self.labels_outpath))
        else:
          with open(self.labels_outpath, "wb") as f:
            f.write(labels_output.encode("utf-8"))
          print("Written {}".format(self.labels_outpath))
      save_config(self.outpath, self.files, self.overwrite, self.dry_run)
    else:
      print("No image files found in depth of {}. No file written".format(self.depth))
