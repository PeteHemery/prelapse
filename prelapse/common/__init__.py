# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# You may convey verbatim copies of the Program's source code as you
# receive it, in any medium, provided that you conspicuously and
# appropriately publish on each copy an appropriate copyright notice;
# keep intact all notices stating that this License and any
# non-permissive terms added in accord with section 7 apply to the code;
# keep intact all notices of the absence of any warranty; and give all
# recipients a copy of this License along with the Program.

# prelapse is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

# common/__init__.py

from .utility_functions import setup_logger, parse_group_args, parse_group_slice_index, group_append, \
  gen_list_file, write_list_file, build_ff_cmd, get_pwd, format_float, \
  shell_safe_path, backup_prelapse_file, supports_ansi, print_function_entrance, round_up
from .shell import call_shell_command

__all__ = [
  "setup_logger", "parse_group_args", "parse_group_slice_index", "group_append",
  "gen_list_file", "write_list_file", "build_ff_cmd", "get_pwd", "format_float",
  "shell_safe_path", "backup_prelapse_file", "supports_ansi", "print_function_entrance", "round_up",
  "call_shell_command"
]
