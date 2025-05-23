# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# modifier/argument_parser.py

import argparse
import copy
import os

from ..common import setup_logger
from ..configs import load_config, DEFAULT_CONFIG_FILE_NAME


_gravity = ["None", "Center", "East", "Forget",
           "NorthEast", "North", "NorthWest",
           "SouthEast", "South", "SouthWest", "West"]


def _add_geometry_argument(parser, required=False):
  parser.add_argument("-G", "--geometry", type=str, required=required,
    help="image geometry specifying width and height and other quantities\n"
    "e.g. 800x600\n"
    "see full instructions:\n"
    "  https://imagemagick.org/script/command-line-processing.php#geometry")


def _get_common_image_gen_args(completion):

  common_image_args = argparse.ArgumentParser(
    formatter_class=argparse.RawTextHelpFormatter,
    add_help=False)
  mutexgroup = common_image_args.add_mutually_exclusive_group(required=not completion)
  mutexgroup.add_argument(
    "-a", "--allgroups", action="store_true",
    help="access all groups\n(default: %(default)s)")
  mutexgroup.add_argument(
    "-g", "--group", dest="groups", nargs="?", action="append",
    help="group names within config\n"
    "(NOTE: Can use index or slice, e.g. -g groupA[10] or -g groupB[55:100])")
  common_image_args.set_defaults(allgroups=False)

  common_image_gen_args = argparse.ArgumentParser(
    formatter_class=argparse.RawTextHelpFormatter,
    add_help=False)
  imagegenmutexgroup = common_image_gen_args.add_mutually_exclusive_group(required=not completion)
  imagegenmutexgroup.add_argument(
    "-o", "--outmod", action="store_true",
    help="flag to save modified files to separate directory within group path.\n"
    "Specifying a group, modified images will be saved in a subdirectory structure\n"
    " that represents the parameters passed with the sub-command.\n"
    "Inside the group directory, a new subdirectory will be created\n"
    " prefixed with 'mod-' and suffixed with the command and parameters used.\n"
    "e.g. running:\n"
    "  prelapse mod image resize -g _GROUP-NAME_ -p 25 -o\n"
    "would result in image files being stored in:\n"
    "  _GROUP-PATH_{0}mod-resize-p25{0}_RESIZED-FILES_.jpg\n"
    "The new files will be appended and written to the group"
    " config file".format(os.sep))
  imagegenmutexgroup.add_argument(
    "-i", "--inplace", action="store_true",
    help="modify and overwrite files in place\n"
    "(default: %(default)s)")
  common_image_gen_args.add_argument(
    "--gravity", type=str, default="Center",
    help="horizontal and vertical text placement.\n"
    "run 'mogrify -list gravity' to see the following options:\n{}\n"
    "(default: %(default)s)".format(_gravity))
  common_image_gen_args.set_defaults(inplace=False, outmod=False)
  return [common_image_args, common_image_gen_args]


def _add_image_modifier(modsubparser, parents, completion):
  # Image modifier
  modimgparser = modsubparser.add_parser(
    "image", help="modify image options",
    formatter_class=argparse.RawTextHelpFormatter)
  modimgsubparser = modimgparser.add_subparsers(
    dest="modimg", help="modify image sub-commands help", required=True)

  image_gen_parents = parents + _get_common_image_gen_args(completion)
  for subcmd in [_add_image_resize, _add_image_scale, _add_image_crop, _add_image_color, _add_image_rotate]:
    modimgsubparser = subcmd(modimgsubparser, image_gen_parents, completion)

  return modimgsubparser, _add_image_stab(modimgsubparser, parents, completion)


def _add_image_resize(modimgsubparser, parents, completion):
  modimgresize = modimgsubparser.add_parser(
    "resize", help="resize image options",
    formatter_class=argparse.RawTextHelpFormatter,
    parents=parents)
  resizemutexgroup = modimgresize.add_mutually_exclusive_group(required=not completion)
  resizemutexgroup.add_argument(
    "-m", "--max", type=int,
    help="maximum dimensions (height or width) in pixels\n"
    "(default: %(default)s)")
  resizemutexgroup.add_argument(
    "-p", "--percent", type=int,
    help="scale height and width by specified percentage\n"
    "(default: %(default)s)")
  _add_geometry_argument(resizemutexgroup)
  return modimgsubparser


def _add_image_scale(modimgsubparser, parents, completion):
  modimgscale = modimgsubparser.add_parser(
    "scale", help="scale image options",
    formatter_class=argparse.RawTextHelpFormatter,
    parents=parents)
  scalemutexgroup = modimgscale.add_mutually_exclusive_group(required=not completion)
  scalemutexgroup.add_argument(
    "-m", "--max", type=int,
    help="maximum dimensions (height or width) in pixels for resized image")
  scalemutexgroup.add_argument(
    "-p", "--percent", type=int,
    help="scale height and width by specified percentage")
  _add_geometry_argument(scalemutexgroup)
  return modimgsubparser


def _add_image_crop(modimgsubparser, parents, completion):
  modimgcrop = modimgsubparser.add_parser(
    "crop", help="crop image options",
    formatter_class=argparse.RawTextHelpFormatter,
    parents=parents)
  _add_geometry_argument(modimgcrop, required=not completion)
  return modimgsubparser


def _add_image_color(modimgsubparser, parents, completion): # pylint: disable=unused-argument
  modimgcolor = modimgsubparser.add_parser(
    "color", help="color image options",
    formatter_class=argparse.RawTextHelpFormatter,
    parents=parents)
  modimgcolor.add_argument(
    "--normalize", action="store_true",
    help="increase the contrast in an image by stretching the range of intensity values\n"
    "(default: %(default)s)")
  modimgcolor.add_argument(
    "--autolevel", action="store_true",
    help="automagically adjust color levels of image\n"
    "(default: %(default)s)")
  modimgcolor.add_argument(
    "--autogamma", action="store_true",
    help="automagically adjust gamma level of image\n"
    "(default: %(default)s)")
  modimgcolor.set_defaults(normalize=False, autolevel=False, autogamma=False)
  return modimgsubparser


def _add_image_rotate(modimgsubparser, parents, completion):
  modimgrotate = modimgsubparser.add_parser(
    "rotate", help="rotate image options",
    formatter_class=argparse.RawTextHelpFormatter,
    parents=parents)
  rotatemutexgroup = modimgrotate.add_mutually_exclusive_group(required=not completion)
  rotatemutexgroup.add_argument(
    "-R", "--autoorient", action="store_true",
    help="auto rotate image using exif metadata suitable for viewing\n"
    "(default: %(default)s)")
  rotatemutexgroup.add_argument(
    "-C", "--clockwise", action="store_true",
    help="rotate image 90 degrees clockwise\n"
    "(default: %(default)s)")
  rotatemutexgroup.add_argument(
    "-A", "--anticlockwise", action="store_true",
    help="rotate image 90 degrees anticlockwise\n"
    "(default: %(default)s)")
  rotatemutexgroup.add_argument(
    "-D", "--degrees", type=str,
    help="rotate image arbitrary number of degrees\n"
    "Use > to rotate the image only if its width exceeds the height.\n"
    "< rotates the image only if its width is less than the height.\n"
    "For example, if you specify -rotate '-90>' and the image size is 480x640,\n"
    " the image is not rotated. However, if the image is 640x480,"
    " it is rotated by -90 degrees.\n"
    "If you use > or <, enclose it in quotation marks to prevent it from"
    " being misinterpreted as a file redirection.\n"
    "\nEmpty triangles in the corners, left over from rotating the image,"
    " are filled with the background color.")
  modimgrotate.set_defaults(autoorient=False, clockwise=False, anticlockwise=False)
  return modimgsubparser


def _add_common_img_stab_args():
  common_img_stab_args = argparse.ArgumentParser(
    formatter_class=argparse.RawTextHelpFormatter,
    add_help=False)
  common_img_stab_args.add_argument(
    "-r", "--fps", "--framerate", dest="fps", type=float, default=25,
    help="preview and output video frame rate per second\n"
    "(default: %(default)s)")
  common_img_stab_args.add_argument(
    "--ffloglevel", type=str, default="info",
    choices=["quiet", "panic", "fatal", "error", "warning",
            "info", "verbose", "debug", "trace"],
    help="log level for ffplay/ffmpeg\n"
    "(default: %(default)s)")
  return common_img_stab_args


def _add_image_stab(modimgsubparser, parents, completion):
  modimgstab = modimgsubparser.add_parser(
    "stab", help="stabilize image options",
    formatter_class=argparse.RawTextHelpFormatter)

  modstabphase1 = _add_stab_phase1()
  modstabphase2 = _add_stab_phase2(completion)

  common_img_stab_args = _add_common_img_stab_args()

  modstabsubparser = modimgstab.add_subparsers(
    dest="modstabphase", help="mod stab sub-commands help", required=True)
  _ = modstabsubparser.add_parser(
    "1", help="perform first phase of stabilization (vidstabdetect)",
    parents=parents + [common_img_stab_args, modstabphase1],
    formatter_class=argparse.RawTextHelpFormatter)
  _ = modstabsubparser.add_parser(
    "2", help="perform second phase of stabilization (vidstabtransform)",
    parents=parents + [common_img_stab_args, modstabphase2],
    formatter_class=argparse.RawTextHelpFormatter)
  _ = modstabsubparser.add_parser(
    "12", help="perform both phases of stabilization (vidstabdetect then vidstabtransform)",
    parents=parents + [common_img_stab_args,
                       copy.deepcopy(modstabphase1), # Avoid mangling "--play" help for the original parser
                       modstabphase2],
    formatter_class=argparse.RawTextHelpFormatter,
    conflict_handler="resolve")

  return modstabsubparser


def _add_stab_phase1():
  modstabphase1 = argparse.ArgumentParser(
    formatter_class=argparse.RawTextHelpFormatter,
    add_help=False)
  modstabphase1.add_argument(
    "--result", type=str,
    help="Set the path to the file used to write the transforms information.\n"
    "Default value is stable/transforms.trf")
  modstabphase1.add_argument(
    "--shakiness", default=5, type=int,
    help="Set how shaky the video is and how quick the camera is.\n"
    "It accepts an integer in the range 1-10, a value of 1 means little shakiness,\n"
    "a value of 10 means strong shakiness.\n"
    "(default: %(default)s)")
  modstabphase1.add_argument(
    "--accuracy", default=15, type=int,
    help="Set the accuracy of the detection process.\n"
    "It must be a value in the range 1-15. A value of 1 means low accuracy,\n"
    "a value of 15 means high accuracy. Default value is 15.\n"
    "(default: %(default)s)")
  modstabphase1.add_argument(
    "--stepsize", default=6, type=int,
    help="Set stepsize of the search process.\n"
    "The region around minimum is scanned with 1 pixel resolution.\n"
    "(default: %(default)s)")
  modstabphase1.add_argument(
    "--mincontrast", default=0.3, type=float,
    help="Set minimum contrast. Below this value a local measurement field is discarded.\n"
    "Must be a floating point value in the range 0-1.\n"
    "(default: %(default)s)")
  modstabphase1.add_argument(
    "--tripod", default=0, type=int,
    help="Set reference frame number for tripod mode.\n"
    "If enabled, the motion of the frames is compared to a reference frame in\n"
    "the filtered stream, identified by the specified number.\n"
    "The idea is to compensate all movements in a more-or-less static scene\n"
    "and keep the camera view absolutely still.\n"
    "If set to 0, it is disabled. The frames are counted starting from 1.\n"
    "(default: %(default)s)")
  modstabphase1.add_argument(
    "--show", default=2, type=int,
    help="Show fields and transforms in the resulting frames.\n"
    "It accepts an integer in the range 0-2.\n"
    "Value 0 disables any visualization.\n(default: %(default)s)")
  modstabphase1.add_argument(
    "-p", "--play", action="store_true", help="preview stabilization detection\n"
    "(default: %(default)s)")
  modstabphase1.set_defaults(play=False)
  return modstabphase1


def _add_stab_phase2(completion):
  modstabphase2 = argparse.ArgumentParser(
    formatter_class=argparse.RawTextHelpFormatter,
    add_help=False)
  modstabphase2.add_argument(
    "--input", type=str,
    help="Set path to the file used to read the transforms.\n"
    "Default value is stable/transforms.trf")
  modstabphase2.add_argument(
    "--smoothing", default=10, type=int,
    help="Set the number of frames (value*2 + 1) "
    "used for lowpass filtering the camera movements.\n"
    "Default value is 10.\n"
    "For example a number of 10 means that 21 frames are used "
    "(10 in the past and 10 in the future) to\n"
    "smoothen the motion in the video. A larger value leads to a smoother video,\n"
    "but limits the acceleration of the camera (pan/tilt movements).\n"
    "0 is a special case where a static camera is simulated.\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--optalgo", default="gauss", type=str,
    help="Set the camera path optimization algorithm.\n"
    "Accepted values are:\n"
    "'gauss' gaussian kernel low-pass filter on camera motion (default)\n"
    "'avg'   averaging on transformations\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--maxshift", default=1, type=int,
    help="Set maximal number of pixels to translate frames.\n"
    "Default value is -1, meaning no limit.\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--maxangle", default=-1, type=float,
    help="Set maximal angle in radians (degree*PI/180) to rotate frames.\n"
    "Default value is -1, meaning no limit.\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--crop", default="black", type=str,
    help="Specify how to deal with borders that may be visible due to movement "
    "compensation.\nAvailable values are:\n"
    "'keep'  keep image information from previous frame (default)\n"
    "'black' fill the border black\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--invert", default=0, type=int,
    help="Invert transforms if set to 1. Default value is 0.\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--relative", default=0, type=int,
    help="Consider transforms as relative to previous frame if set to 1,\n"
    "absolute if set to 0. Default value is 0.\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--zoom", default=0.0, type=float,
    help="Set percentage to zoom. A positive value will result in a zoom-in effect,\n"
    "a negative value in a zoom-out effect.\n"
    "Default value is 0 (no zoom).\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--optzoom", default=1, type=int,
    help="Set optimal zooming to avoid borders.\n"
    "Accepted values are:\n"
    "'0' disabled\n"
    "'1' optimal static zoom value is determined"
    " (only very strong movements will lead to visible borders) (default)\n"
    "'2' optimal adaptive zoom value is determined"
    " (no borders will be visible), see zoomspeed\n"
    "Note that the value given at zoom is added to the one calculated here.\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--zoomspeed", default=0.1, type=float,
    help="Set percent to zoom maximally each frame"
    " (enabled when optzoom is set to 2).\n"
    "Range is from 0 to 5, default value is 0.25.\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--interpol", default="bilinear", type=str,
    help="Specify type of interpolation.\n"
    "Available values are:\n"
    "'no'       no interpolation\n"
    "'linear'   linear only horizontal\n"
    "'bilinear' linear in both directions (default)\n"
    "'bicubic'  cubic in both directions (slow)\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--virtualtripod", default=0, type=int,
    help="Enable virtual tripod mode if set to 1, which is equivalent to "
    "relative=0:smoothing=0.\nDefault value is 0.\n"
    "Use also tripod option of vidstabdetect.\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--debug", default=0, type=int,
    help="Increase log verbosity if set to 1.\n"
    "Also the detected global motions are written to the"
    " temporary file global_motions.trf.\n"
    "Default value is 0.\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--unsharp", action="store_true",
    help="Sharpen or blur the input video.\n"
    "All parameters are optional and default to the "
    "equivalent of the string '5:5:0.0:5:5:0.0'\n"
    "(NOTE: This option does nothing and is just for diplaying this information)")
  modstabphase2.add_argument(
    "--lx", default=5, type=int,
    help="Set the luma matrix horizontal size.\n"
    "It must be an odd integer between 3 and 23. The default value is 5.\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--ly", default=5, type=int,
    help="Set the luma matrix vertical size.\n"
    "It must be an odd integer between 3 and 23. The default value is 5.\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--la", default=0.0, type=float,
    help="Set the luma effect strength.\n"
    "It must be a floating point number, reasonable values lay between "
    "-1.5 and 1.5.\n"
    "Negative values will blur the input video, "
    "while positive values will sharpen it,\n"
    "a value of zero will disable the effect. Default value is 1.0.\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--cx", default=5, type=int,
    help="Set the chroma matrix horizontal size.\n"
    "It must be an odd integer between 3 and 23. The default value is 5.\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--cy", default=5, type=int,
    help="Set the chroma matrix vertical size.\n"
    "It must be an odd integer between 3 and 23. The default value is 5.\n"
    "(default: %(default)s)")
  modstabphase2.add_argument(
    "--ca", default=0.0, type=float,
    help="Set the chroma effect strength.\n"
    "It must be a floating point number, reasonable values lay between "
    "-1.5 and 1.5.\n"
    "Negative values will blur the input video, "
    "while positive values will sharpen it,\n"
    "a value of zero will disable the effect. Default value is 1.0.\n"
    "(default: %(default)s)")

  stabmutexgroup = modstabphase2.add_mutually_exclusive_group(required=not completion)
  stabmutexgroup.add_argument(
    "-p", "--play", action="store_true",
    help="ffplay stabilized images")
  stabmutexgroup.add_argument(
    "-w", "--writejpgs", action="store_true",
    help="output stabilized images")
  modstabphase2.set_defaults(unsharp=True, play=False, writejpgs=False)

  return modstabphase2


def _add_group_modifier(modsubparser, parents, completion):
  # Group modifier
  modgrpparser = modsubparser.add_parser(
    "group", help="modify group option", formatter_class=argparse.RawTextHelpFormatter)
  modgrpsubparser = modgrpparser.add_subparsers(
    dest="modgrp", help="modify group sub-commands help", required=True)

  modgrprename = modgrpsubparser.add_parser(
    "rename", help="rename group", formatter_class=argparse.RawTextHelpFormatter,
    parents=parents)
  if completion:
    modgrprename.add_argument("fromgroup", nargs="*", help="old group name")
    modgrprename.add_argument("togroup", nargs="*", help="new group name")
  else:
    modgrprename.add_argument("fromgroup", help="old group name")
    modgrprename.add_argument("togroup", help="new group name")

  modgrpdel = modgrpsubparser.add_parser(
    "del", help="delete group",
    formatter_class=argparse.RawTextHelpFormatter,
    parents=parents)
  modgrpdel.add_argument(
    "groups", nargs="?" if completion else "+",
    help="groups names within config to delete.\n"
    "(NOTE: Can NOT use index or slice, e.g. groupA groupB)")

  modgrpnew = modgrpsubparser.add_parser(
    "new", help="new group",
    formatter_class=argparse.RawTextHelpFormatter,
    parents=parents)
  modgrpnew.add_argument("groupname", help="new group name")
  modgrpnew.add_argument(
    "-g", "--group", dest="groups", nargs="?", action="append",
    help="groups names within config from which to build new group.\n"
    "(NOTE: Can use index or slice, e.g. -g groupA[10] -g groupB[55:100])")
  modgrpnew.add_argument(
    "-p", "--path", dest="search_path", nargs="?",
    help="Directory path to search for files to include in the new group")
  modgrpnew.add_argument(
    "-f", "--files", dest="files", nargs="+",
    help="List of specific file paths to add to the new group")
  return modgrpsubparser


def _add_label_modifier(modsubparser, parents, completion):
  # Labels modifier
  modlblparser = modsubparser.add_parser("labels",
    help="modify audacity labels",
    formatter_class=argparse.RawTextHelpFormatter,
    parents=parents)
  modlblparser.add_argument("-l", "--labels", default="labels.txt",
    help="path to input Audacity labels file\n(default: %(default)s)")

  lblmutexgroup = modlblparser.add_mutually_exclusive_group(required=not completion)
  lblmutexgroup.add_argument("--shorten", action="store_true", help="remove the first column in labels file")
  lblmutexgroup.add_argument("--lengthen", action="store_true", help="duplicate the first column in labels file")

  modlblparser.set_defaults(shorten=False, lengthen=False)


def _add_parser_args(parser, common_args=None, completion=False): # pylint: disable=too-many-locals,too-many-statements,unused-argument
  common_mod_args = argparse.ArgumentParser(
    formatter_class=argparse.RawTextHelpFormatter,
    add_help=False,
    parents=[common_args])
  common_mod_args.add_argument(
    "-c", "--config", default=DEFAULT_CONFIG_FILE_NAME,
    help="Required Markdown config file describing the picture groups\n"
    "(default: %(default)s)")
  parents=[common_mod_args]

  modsubparser = parser.add_subparsers(dest="modcmd", help="mod sub-commands help", required=True)

  # Images
  modimgsubparser, modstabsubparser = _add_image_modifier(modsubparser, parents, completion)

  # Groups
  modgrpsubparser = _add_group_modifier(modsubparser, parents, completion)

  # Labels
  _add_label_modifier(modsubparser, parents, completion)

  return parser, [modsubparser, modgrpsubparser, modimgsubparser, modstabsubparser] if completion else None


def _parse_args(self, args, logger_name):
  self.verbose = args.verbose
  self.dry_run = args.dry_run
  self.overwrite = args.overwrite
  self.logger = setup_logger(logger_name, self.verbose)
  if hasattr(args, "config"):
    self.config, self.configfile = load_config(args.config)
