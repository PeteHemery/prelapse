# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# runner/parser_utils.py

import os
import sys
import ctypes


def supports_ansi(stream=sys.stdout):
  # 1) Must be a real terminal
  if not hasattr(stream, "isatty") or not stream.isatty():
    return False

  # 2) On POSIX, a non-“dumb” TERM usually means ANSI is OK
  if os.name == "posix":
    term = os.environ.get("TERM", "")
    return bool(term and term != "dumb")

  # 3) On Windows, we check the console mode for the ENABLE_VIRTUAL_TERMINAL_PROCESSING bit
  if os.name == "nt":
    # STD_OUTPUT_HANDLE = -11
    kernel32 = ctypes.windll.kernel32
    h = kernel32.GetStdHandle(-11)
    mode = ctypes.c_uint()
    if not kernel32.GetConsoleMode(h, ctypes.byref(mode)):
      return False
    # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    return (mode.value & 0x0004) != 0

  # 4) Fallback: give up
  return False


def print_function_entrance(logger, ansi, text="", prefix="    "):
  caller = sys._getframe(1).f_code.co_name # pylint: disable=protected-access
  to_print = "IN {}({})".format(caller, text)
  logger.debug(prefix + "\x1b[{}m{}\x1b[0m".format(ansi, to_print) if supports_ansi() else to_print)


def correct_rounding_errors(goal, logger, lst, key_files=None):
  print_function_entrance(logger, "7;38;5;189")
  if not lst:
    raise RuntimeError("No lst for correction")
  floored_lst = [int(item) for item in lst]
  if key_files:
    sum_diffs = [floored_lst[i+1] - floored_lst[i] for i in range(len(floored_lst) - 1)]
    current_sum = sum(sum_diffs)
    logger.debug("DIFFS {}".format(sum_diffs))
  else:
    current_sum = sum(floored_lst)
  error = goal - current_sum
  logger.debug("error {}, goal {}, current_sum {}".format(error, goal, current_sum))

  if error == 0:
    logger.debug("No rounding correction needed.")
    return [1 if l <= 1 and lst[i] != 0 else l for i, l in enumerate(floored_lst)]
  if error < 0:
    raise RuntimeError("Error is negative. {}".format(error))

  fractional_parts = sorted(
    [(i, offset - floored_lst[i], offset)
     for i, offset in enumerate(lst)],
    key=lambda x: -x[1] if floored_lst[x[0]] == 0 else 0)

  if key_files:
    logger.error("{}, {}, {}".format(error, goal, current_sum))
    logger.error(key_files)
    raise RuntimeError("Still have key_files when there should be none.")

  while error > 0:
    for idx, _, _ in fractional_parts:
      # Ensure we still have error to distribute.
      if error <= 0:
        break
      floored_lst[idx] += 1
      error -= 1

  if 0 in floored_lst and 0 not in lst:
    logger.error("Inconsistent state: floored_lst has a 0 when original lst did not.")
    logger.error("{}, {}, {}".format(goal, error, floored_lst))
    logger.error("WTF!")
    raise ValueError("Rounding correction error.")

  return [1 if l == -1 else l for l in floored_lst] # Add back the holds
