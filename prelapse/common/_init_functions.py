# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# common/_init_functions.py

import argparse
import os
import sys

from ..modifier.argument_parser import _gravity
from ..genconfig import LapseGenerator
from ..modifier import LapseModifier
from ..runner import LapseRunner
from ..info import LapseInfo
from ..configs import load_config
from .._version import __version__


__prelapse_banner__ = " " * 19 + """.
 .=,   ,-_  .:.   ;`  .-,   .:.   _.  .:.
 p  : .r   .;_;  :`    _;  ;  :  = ` .;_;
 :  ; :'   :e`   =   ;` ;  ;  ;  `=, :=`
`:<+` ;     '=+` l_, `-a.  :p+` ,s=`  'e+`
 =                         =
'`    by Pete Hemery      '`{:>12}""".format(__version__)

__all__ = ["prelapse_main", "set_prelapse_epilog", "__version__"]


def set_prelapse_epilog(parser):
  parser.epilog = __prelapse_banner__
  for subparser in [
    subparser
    for action in parser._actions if isinstance(action, argparse._SubParsersAction) # pylint: disable=protected-access
    for subparser in action.choices.values()]:
    set_prelapse_epilog(subparser)


def _handle_parsed_args(parser, args):
  cmd = args.cmd
  if cmd == "gen":
    LapseGenerator().run_generator(args)
  elif cmd == "mod":
    LapseModifier().run_modifier(args)
  elif cmd == "play":
    LapseRunner().run_prelapse(args, run=True)
  elif cmd == "enc":
    LapseRunner().run_prelapse(args, out=True)
  elif cmd == "info":
    output = LapseInfo().show_info(args)
    if output != "":
      print(output)
  else:
    print(parser.format_help())


def _setup_arg_parsing(completion=False):
  common_args = argparse.ArgumentParser(
    formatter_class=argparse.RawTextHelpFormatter,
    add_help=False)
  common_args.add_argument(
    "--hide_banner", dest="hide_banner", action="store_true",
    help="disable printing prelapse banner\n(default: %(default)s)")
  common_args.add_argument(
    "-n", "--dry-run", dest="dry_run", action="store_true",
    help="disable writing output, only print\n(default: %(default)s)")
  common_args.add_argument(
    "-y", "--overwrite", dest="overwrite", action="store_true",
    help="over write output file if it already exists\n(default: %(default)s)")
  common_args.add_argument(
    "-v", "--verbose", dest="verbose", action="store_true",
    help="enable verbose prints\n(default: %(default)s)")
  common_args.set_defaults(hide_banner=False, dry_run=False, overwrite=False, verbose=False)

  parser = argparse.ArgumentParser(
    description="Script for creating image sequence based music videos.\n"
    "Explore the sub commands with -h for more details on options available.",
    formatter_class=argparse.RawTextHelpFormatter)
  subparsers = parser.add_subparsers(dest="cmd", help="sub-commands help", required=True)

  spgen = subparsers.add_parser(
    "gen", help="generate config command",
    description="Markdown group config generator.\n"
    "Run this command to search a directory tree downwards for images.\n"
    "By default the depth of directory search is 1, meaning pictures in\n"
    "subdirectories further down than 1 layer from the INPATH won't be\n"
    "included in the search.\n"
    "The output will be a Markdown file with the images grouped together by\n"
    "directory name. These groups can then be used in an Audacity format\n"
    "labels file to indicate the timestamp that a group should start.\n"
    "Explore the sub commands with -h for more details on options available.",
    formatter_class=argparse.RawTextHelpFormatter, parents=[common_args])
  spgen.set_defaults(cmd = "gen")
  spgen = LapseGenerator.add_parser_args(spgen)

  spmod = subparsers.add_parser(
    "mod", help="modify images or groups or labels",
    description="Modify images or groups or labels.\n"
    "Assorted commands associated with modifying images:\n"
    " resize, scale, crop, color, rotate, stabilize\n"
    "or groups:\n"
    " rename, delete, new\n"
    "or labels:\n"
    " --shorten to change timestamp columns from 2 to 1\n"
    " --lengthen to change timestamp columns from 1 to 2\n"
    "Explore the sub commands with -h for more details on options available.",
    formatter_class=argparse.RawTextHelpFormatter, parents=[common_args])
  spmod.set_defaults(cmd = "mod")
  spmod, spmod_subparsers = LapseModifier.add_parser_args(spmod, common_args, completion)

  sprun = subparsers.add_parser(
    "play", help="preview output with ffplay command",
    description="Preview output with ffplay command.\n"
    "Explore the sub commands with -h for more details on options available.",
    formatter_class=argparse.RawTextHelpFormatter, parents=[common_args])
  sprun.set_defaults(cmd = "play")
  sprun = LapseRunner.add_parser_args(sprun, run=True)

  spout = subparsers.add_parser(
    "enc", help="create encoded mp4 output with ffmpeg command",
    description="Create encoded mp4 output with ffmpeg command.\n"
    "Explore the sub commands with -h for more details on options available.",
    formatter_class=argparse.RawTextHelpFormatter, parents=[common_args])
  spout.set_defaults(cmd = "enc")
  spout = LapseRunner.add_parser_args(spout, out=True)

  spinfo = subparsers.add_parser(
    "info", help="show info about groups and files",
    description="Show info about groups and files.\n"
    "Extract information about the groups and files within them\n"
    "(e.g. number of files and file offsets into group).\n"
    "Or show the details for a particular image file name.\n"
    "Explore the sub commands with -h for more details on options available.",
    formatter_class=argparse.RawTextHelpFormatter, parents=[common_args])
  spinfo.set_defaults(cmd = "info")
  spinfo = LapseInfo.add_parser_args(spinfo)

  parser.set_defaults(verbose=False)

  set_prelapse_epilog(parser)
  return [subparsers,] + spmod_subparsers if completion else parser


def _print_choices(choices):
  print(" ".join(choices))


def _flatten_choices(subparser, subcommand):
  return [item for sublist in [
    action.option_strings
    for choice in subparser.choices if choice.startswith(subcommand)
    for action in subparser.choices[choice]._actions] for item in sublist] # pylint: disable=protected-access


def _parse_group_names(subparser, comp_line, comp_words, cmd_index):
  cmd = comp_words[cmd_index]
  # Turn off any positional args requirement parsing errors
  for i, x in enumerate(subparser.choices[cmd]._actions): # pylint: disable=protected-access
    if x.required:
      subparser.choices[cmd]._actions[i].required = False # pylint: disable=protected-access


  # Get the config contents
  args = subparser.choices[cmd].parse_args()
  config, _ = load_config(args.config)
  current_word = comp_words[-1]
  if comp_line[-1] == " ":
    output = (_flatten_choices(subparser, cmd)
              if any(x == comp_words[-2] for x in ["-g", "--group"])
              else [g.group for g in config])
  else:
    output = [choice for choice in _flatten_choices(subparser, cmd) if choice.startswith(current_word)] if \
      any(x == current_word for x in ["-g", "--group"]) else \
        [g.group for g in config if g.group.startswith(current_word)]
  return " ".join(output)


def _handle_generic_completion(subparser, cmd, comp_words, comp_line, args_with_params):
  current_word = comp_words[-1]
  if comp_line[-1] == " ":
    if any(x == comp_words[-1] for x in args_with_params):
      print("\nExpecting input\n{}".format(comp_line), file=sys.stderr, end="")
    else:
      _print_choices(_flatten_choices(subparser, cmd))
  else:
    if any(x == comp_words[-2] for x in args_with_params):
      _print_choices(_flatten_choices(subparser, current_word))
    else:
      _print_choices(choice for choice in _flatten_choices(subparser, cmd) if choice.startswith(current_word))


def _handle_group(args):
  spmodgroup, comp_words, comp_line, num_words, current_word, last_char_is_a_space = args
  if num_words in (3, 4) and not last_char_is_a_space:
    _print_choices([choice for choice in spmodgroup.choices if choice.startswith(current_word)])
  elif num_words == 3:
    _print_choices(spmodgroup.choices)
  elif num_words >= 4 and any(x in comp_words[3] for x in ["del", "rename"]):
    if any(x == comp_words[i] for i in [-1, -2] for x in ["-g", "--group"]) or comp_words[3] == "del":
      output = _parse_group_names(spmodgroup, comp_line, comp_words, 3)
      if output and output != comp_words[-1]:
        print(output)
        return
    if current_word.startswith("-"):
      _print_choices(_flatten_choices(spmodgroup, comp_words[3]))
      return
    args = spmodgroup.choices[comp_words[3]].parse_args()
    if comp_words[3] == "rename" and num_words >= 6:
      _print_choices(_flatten_choices(spmodgroup, comp_words[3]) if last_char_is_a_space else
                    [choice for choice in _flatten_choices(spmodgroup, comp_words[3])
                      if choice.startswith(current_word)])
      return
    config, _ = load_config(args.config)
    output = [g.group for g in config if g.group.startswith(current_word)] if not last_char_is_a_space \
        else [g.group for g in config] + _flatten_choices(spmodgroup, comp_words[3])
    if comp_words[3] == "del":
      output = [x for x in output if all(x != o for o in comp_words[4:])]
    _print_choices(output)
  elif num_words >= 4 and any(x == comp_words[i] for i in [-1, -2] for x in ["-g", "--group"]):
    print(_parse_group_names(spmodgroup, comp_line, comp_words, 3))
  else:
    _print_choices(_flatten_choices(spmodgroup, comp_words[3]))


def _handle_image(args):
  spmodimage, spmodimagestab, comp_words, comp_line, num_words, current_word, last_char_is_a_space = args
  # print("\ncomp_words {}\n#comp_words {}\ncurrent_word {}\ncomp_line {}\n"
  #       .format(comp_words, num_words, current_word, comp_line), file=sys.stderr)
  if num_words == 3:
    _print_choices(spmodimage.choices)
  elif num_words in (3, 4) and not last_char_is_a_space:
    _print_choices([choice for choice in spmodimage.choices if choice.startswith(current_word)])
  elif (num_words == 4 or (num_words == 5 and not last_char_is_a_space)) and comp_words[3] == "stab":
    _print_choices(spmodimagestab.choices)
  elif num_words == 4:
    _print_choices(_flatten_choices(spmodimage, comp_words[3]))
  elif comp_words[3] == "stab":
    _print_choices(_flatten_choices(spmodimagestab, comp_words[4]))
  elif num_words >= 5 and any(x == comp_words[i] for i in [-1, -2] for x in ["-g", "--group"]):
    print(_parse_group_names(spmodimage, comp_line, comp_words, 3))
  elif num_words >= 5 and any("--gravity" == comp_words[i] for i in [-1, -2]):
    if last_char_is_a_space:
      _print_choices(_flatten_choices(spmodimage, comp_words[3]) if comp_words[-2] == "--gravity"
                     else list(_gravity))
    else:
      _print_choices(_flatten_choices(spmodimage, comp_words[3]) if current_word == "--gravity"
                     else [choice for choice in _gravity if choice.startswith(current_word)])
  else:
    args_with_params = ["-m", "--max", "-p", "--percent", "-G", "--geometry"]
    _handle_generic_completion(spmodimage, comp_words[3], comp_words, comp_line, args_with_params)


def _handle_labels(args):
  spmod, comp_words, num_words, current_word, last_char_is_a_space = args
  if num_words >= 3 and not last_char_is_a_space:
    _print_choices([choice for choice in _flatten_choices(spmod, comp_words[2]) if choice.startswith(current_word)])
  else:
    _print_choices(_flatten_choices(spmod, comp_words[2]))


def _handle_mod_completion(subparsers, comp_words, comp_line):
  spmod, spmodgroup, spmodimage, spmodimagestab = subparsers[1:]
  num_words = len(comp_words)
  current_word = comp_words[-1]
  last_char_is_a_space = comp_line[-1] == " "

  if num_words == 3 and not last_char_is_a_space:
    _print_choices([choice for choice in spmod.choices if choice.startswith(current_word)])
  elif comp_words[2] == "group":
    _handle_group((spmodgroup, comp_words, comp_line, num_words, current_word, last_char_is_a_space))
  elif comp_words[2] =="image":
    _handle_image((spmodimage, spmodimagestab, comp_words, comp_line, num_words, current_word, last_char_is_a_space))
  elif comp_words[2] == "labels":
    _handle_labels((spmod, comp_words, num_words, current_word, last_char_is_a_space))
  else:
    print("\nInvalid command! '{}' How did you get here??\n{}"
          .format(" ".join(comp_words), comp_line), file=sys.stderr, end="")


def _handle_gen(subparsers, comp_words, comp_line):
  args_with_params = ["-i", "--inpath", "-d", "--depth", "-x", "--exclude", "-lt", "--labels-time"]
  _handle_generic_completion(subparsers[0], comp_words[1], comp_words, comp_line, args_with_params)


def _handle_info(subparsers, comp_words, comp_line):
  top_subparser = subparsers[0]
  if any(x == comp_words[i] for i in [-1, -2] for x in ["-g", "--group"]):
    print(_parse_group_names(top_subparser, comp_line, comp_words, 1))
  else:
    args_with_params = ["-i", "--filename", "-d", "--depth", "-x", "--exclude", "-lt", "--labels-time"]
    _handle_generic_completion(top_subparser, comp_words[1], comp_words, comp_line, args_with_params)


def _handle_play_enc(subparsers, comp_words, comp_line):
  args_with_params = ["-d", "--delimiter", "-r", "--fps", "--framerate", "-w", "--width",
                      "-x", "--aspectratio", "-t", "--tempo", "-j", "--jump"]
  if comp_words[1] == "enc":
    args_with_params += ["-C", "--codec", "-Q", "--crf", "-o", "--outpath"]
  _handle_generic_completion(subparsers[0], comp_words[1], comp_words, comp_line, args_with_params)


def _handle_command(subparsers, comp_words, comp_line):
  command_map = {
    "gen": _handle_gen,
    "info": _handle_info,
    "mod": _handle_mod_completion,
    "play": _handle_play_enc,
    "enc": _handle_play_enc,
  }
  action = command_map.get(comp_words[1])
  if action:
    action(subparsers, comp_words, comp_line)
    return True
  print("Invalid command")
  return False


def _prelapse_bash_completion(subparsers):
  # print("subparsers {}".format(subparsers), file=sys.stderr)
  comp_line = os.environ["COMP_LINE"]
  comp_point = int(os.environ["COMP_POINT"])
  if len(comp_line) != comp_point:
    # print("Adjusting the comp_line to reflect shorter comp_point", file=sys.stderr)
    comp_line = comp_line[:comp_point]
  comp_words = comp_line.split()
  num_words = len(comp_words)
  current_word = comp_words[-1]
  top_subparser, spmod = subparsers[:2]

  if num_words == 1:
    _print_choices(top_subparser.choices)
  elif num_words == 2:
    if comp_line[-1] != " ":
      _print_choices([choice for choice in top_subparser.choices if choice.startswith(current_word)])
    else:
      _print_choices(spmod.choices if comp_words[1] == "mod" else _flatten_choices(top_subparser, comp_words[1]))
  elif num_words > 2 and not comp_words[1] in top_subparser.choices:
    print("\nInvalid command! '{}' How did you get here??\n{}"
          .format(" ".join(comp_words), comp_line), file=sys.stderr, end="")
  elif not _handle_command(subparsers, comp_words, comp_line):
    print("\nUnhandled command", file=sys.stderr, end="")
    _print_choices(_flatten_choices(top_subparser, comp_words[1]))


def prelapse_main(args=None):
  sys.dont_write_bytecode = True
  if "COMP_LINE" in os.environ:
    subparsers = _setup_arg_parsing(completion=True)
    try:
      _prelapse_bash_completion(subparsers)
    except Exception: # pylint: disable=broad-exception-caught
      pass
    return
  exit_code = 0
  parser = _setup_arg_parsing()
  args = parser.parse_args(args)
  try:
    _handle_parsed_args(parser, args)
  except Exception as e: # pylint: disable=broad-exception-caught
    if args.verbose:
      print(__prelapse_banner__)
      raise
    exit_code = 1
    print("Run with '-v' to see back trace.\n{}: {}".format(type(e).__name__, e))
  if not args.hide_banner:
    print(__prelapse_banner__)
  if exit_code:
    sys.exit(exit_code)
