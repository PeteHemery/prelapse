# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# info/info.py

import os

from .argument_parser import _add_parser_args, _parse_args

class LapseInfo(): # pylint: disable=no-member,too-few-public-methods
  """ Group and image information class """

  add_parser_args = staticmethod(_add_parser_args)
  parse_args = classmethod(_parse_args)

  def _print_group(self):
    output = ""
    if not self.details and not self.filepaths_only:
      for g in self.groups:
        del g["files"]
    groupoffsetwidth = len(str(len(self.groups)))

    for group in self.groups:
      if group["numfiles"] == 0:
        continue
      if output != "":
        output += "\n\n"
      if self.filepaths_only:
        for _, filepath in group["files"]:
          output += "{}\n".format(filepath)
        output = output.rstrip()
        continue

      output += "group index: {:0{}}\tgroup type: {}\tnumber of files: {}\tname: '{}'\n".format(
        group["groupindex"], groupoffsetwidth, group["grouptype"], group["numfiles"], group["name"])
      if "path" in group:
        output += "path: '{}'".format(group["path"])
      if not self.details:
        continue
      if not self.filepaths_only:
        output += "\noffset:\tfilename:\n"
      width = len(str(len(group["files"])))
      for offset, filepath in group["files"]:
        output += "{}\n".format(filepath) if self.filepaths_only \
              else "  {:0{}}\t{}\n".format(offset, width, filepath)
      output = output.rstrip()
    output = output.rstrip()

    return output

  def _print_image_info(self):
    output = ""
    if self.details:
      self.logger.warning("Ignoring request for details when searching for image info")
    notfoundimages = self.imagefiles
    for group in self.groups:
      if group["numfiles"] == 0:
        continue
      width = len(str(len(group["files"])))
      for f in group["files"]:
        basename = os.path.basename(f[1])
        if basename in self.imagefiles:
          if output != "":
            output += "\n"
          output += "offset {:0{}} for image\n  '{}'\n  in group index: {} name:\n    '{}'".format(
            f[0], width, f[1], group["groupindex"], group["name"])
          if basename in notfoundimages:
            notfoundimages.remove(basename)
    if notfoundimages:
      self.logger.warning("images {} could not be found in request groups:\n{}\n"
                          .format(notfoundimages, [x.get("name") for x in self.groups]))
    return output

  def show_info(self, args):
    self.parse_args(args)
    if args.filename is True:
      args.hide_banner = True
    return self._print_group() if self.printgroup else self._print_image_info()
