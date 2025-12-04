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

# runner/label_processor.py

from ..common import format_float, print_function_entrance, round_up
from .timing_builder import build_timings, insert_items_into_timings


def parse_index(index, first_label):
  try:
    idx = int(index)
  except ValueError as e:
    raise ValueError(
      "Cannot parse invalid index label:\n'{}[{}]'\n{}"
      .format(first_label, index, e)) from e
  return idx


def parse_slice(sliced, first_label):
  parsed = {"start": None, "end": None}
  for i, key in enumerate(parsed.keys()):
    try:
      parsed[key] = int(sliced[i]) if sliced[i] else None
    except ValueError as e:
      raise ValueError(
        "Cannot parse invalid slice label, must have valid {} value:\n'{}[{}:{}]'\n{}"
        .format(key, first_label, *sliced, e)) from e
  return parsed.values()


def parse_index_and_slice(label, first_label):
  if first_label[-1] != "]":
    raise RuntimeError(
      "Missing closing square bracket for index/slice. Invalid label:\n{}"
      .format(label["raw_line"]))
  indexed = first_label[:-1].split("[") # Remove the ']' char from the second string
  if len(indexed) != 2:
    raise RuntimeError(
      "Cannot parse invalid index/slice label:\n{}"
      .format(label["raw_line"]))
  first_label, index = indexed
  sliced = index.split(":")  # Search for the slice char
  num_slices = len(sliced)
  if num_slices > 2:
    raise RuntimeError(
      "Only one ':' allowed when defining group slice. Invalid label:\n{}"
      .format(label["raw_line"]))
  if num_slices == 1:   # We have an index
    label["index"] = parse_index(index, first_label)
  elif num_slices == 2: # We have a slice
    label["slice"] = parse_slice(sliced, first_label)
  else:
    raise RuntimeError("Impossible slice count: {}".format(num_slices))
  return first_label


def parse_rep(label, ins):
  if not ins[3:]:
    # Default to repeating once
    return 2
  try:
    rep = int(ins[3:])
    if rep <= 1:
      raise RuntimeError(
        "Invalid repeat request with number less than 2: {}".format(rep))
  except ValueError as e:
    raise ValueError("{}\n{}\n{}".format(e, ins, label)) from e
  return rep


def parse_tempo(label, ins):
  try:
    tempo = float(ins[5:])
  except ValueError as e:
    raise ValueError("{}\n{}\n{}".format(e, ins, label)) from e
  return tempo


def populate_group_files_from_instructions(label, group_config):
  lookup_table = {
    "rev": lambda files, _: files[::-1],
    "rep": lambda files, val: files + (val - 1) * files[int(files[0] == files[-1]):],
    "boom": lambda files, _: files + files[-2::-1],
    "tempo": lambda files, _: files,
    "hold": lambda files, _: files,
  }
  if "index" in label:
    files = [group_config.items[label["index"]]]
  elif "slice" in label:
    slice_from, slice_to = label["slice"]
    files = group_config.items[slice_from:slice_to]
  else:
    files = group_config.items[:]
  if 0 == len(files):
    raise RuntimeError("Number of files in group name {} is 0.\n".format(group_config))

  # Store lambdas for replay
  replay_stack = []
  for ins in label["group_instructions"]:
    key, value = next(iter(ins.items()))
    handler = lookup_table.get(key, lambda val, files, current_ins=ins: (_ for _ in ()).throw(
      RuntimeError("Invalid instruction: '{}'\n{}".format(current_ins, label["raw_line"]))))
    if "tempo" != key:
      replay_stack.append({
        "handler": handler,
        "instruction": key,
        "num_files_from": len(files),
        **({"value": value} if key in ["rep",] else {}),
      })
    files = handler(files, value)
    if key in ["rep", "boom"]:
      replay_stack[-1]["num_files_to"] = len(files)

  if any(key in ins["instruction"] for key in ["boom", "rep",] for ins in replay_stack):
    label["replay_stack"] = replay_stack
  return files


def add_first_label_to_marks(label):
  instructions = label["group_instructions"]
  hold_present = any(True for i in instructions if "hold" in i)
  tempo = next(i["tempo"] for i in instructions if "tempo" in i)
  return build_mark_entry(label, hold_present, tempo)


def build_group_entry(label, group_config):
  files = populate_group_files_from_instructions(label, group_config)
  group = {
    "label": label,
    "files": files,
    "num_files": len(files),
    "group_config": group_config,
    "marks": [add_first_label_to_marks(label)],
    "timestamp_start": label["timestamp"],
    "holds": len([i for i in label["group_instructions"] if "hold" in i]),
  }
  if "replay_stack" in label:
    group["replay_stack"] = label["replay_stack"]
    del label["replay_stack"]
  return group


def build_mark_entry(label, hold_present, tempo=None):
  mark = {
    "timestamp": label["timestamp"],
    "raw_timestamp": label["raw_timestamp"],
    "hold": hold_present,
    "raw_line": label["raw_line"],
  }
  if tempo:
    mark.update({"tempo": tempo})
  return mark


def decode_mark_instruction(label, instructions):
  label["mark"] = True
  valid_instructions = ["tempo", "hold", "mark"]

  for ins in instructions:
    ins = ins.lower()
    if not any(ins.startswith(i) for i in valid_instructions):
      raise RuntimeError("Unable to handle invalid instruction '{}'\n{}".format(ins, label))
    if ins.startswith("tempo"):
      label["tempo"] = parse_tempo(label, ins)
    else:
      label[ins] = True
  return build_mark_entry(label, label.get("hold", False), label.get("tempo", None))


def decode_group_instruction(label, instructions):
  group_instructions = []
  lookup_table = {
    "hold":  lambda ins: {"hold":  None},
    "rev":   lambda ins: {"rev":   None},
    "boom":  lambda ins: {"boom":  None},
    "rep":   lambda ins: {"rep":   parse_rep(label, ins)},
    "tempo": lambda ins: {"tempo": parse_tempo(label, ins)},
  }
  def get_instruction_handler(ins):
    for key, value in lookup_table.items():
      if ins.startswith(key):
        return value
    raise RuntimeError(
      "Invalid group instruction: '{}'\n{}"
      .format(ins, label["raw_line"]))

  for ins in instructions[1:]:
    ins = ins.lower()
    handler = get_instruction_handler(ins)
    group_instructions.append(handler(ins))

  if not any("tempo" in i.keys() for i in group_instructions):
    group_instructions.append({"tempo": 1.0})

  # Parse "group_name[index/slice]"
  first_label = instructions[0]
  if "[" in first_label:
    first_label = parse_index_and_slice(label, first_label)
  label.update({"group_instructions": group_instructions})
  return first_label


def parse_label_line(line):
  entry = line.split("\t")
  if not any(len(entry) == n for n in [2, 3]):
    raise RuntimeError(
      "Invalid entry encountered: {}\n"
      "Must have 2 or 3 tab delimited fields. (timestamp(s)\tlabel)"
      .format(line))
  timestamp = float(entry[0])
  if len(entry) == 3 and timestamp != float(entry[1]):
    raise RuntimeError(
      "Timestamps for beginning and end do not match: {}\n"
      "Consider using 'prelapse mod labels --shorten' to make "
      "timestamps into points rather than ranges.\n".format(line))
  return timestamp, entry[-1].strip()


def update_prev_mark_duration(mark, timestamp, raw_timestamp, framerate):
  duration = round(timestamp - mark["timestamp"], 6)
  raw_duration = round(raw_timestamp - mark["raw_timestamp"], 6)
  num_frames = round_up(duration * framerate)
  mark.update({
    "duration": duration,
    "raw_duration": raw_duration,
    "num_frames": num_frames,
    "num_files": 0, # To be decided later
  })


def update_group_mark_info(group, mark, framerate):
  last_mark = group["marks"][-1]
  if "tempo" not in mark:
    mark["tempo"] = last_mark["tempo"]
  update_prev_mark_duration(last_mark, mark["timestamp"], mark["raw_timestamp"], framerate)
  if mark["hold"]:
    group["holds"] += 1
  group["marks"].append(mark)


def decode_groups_and_marks(groups, args):
  label = args["label"]
  delimiter = args["delimiter"]
  config = args["config"]
  framerate = args["framerate"]

  instructions = [item.strip() for item in label["label"].split(delimiter)]
  first_label = instructions[0]
  if any(first_label.lower().startswith(l) for l in ["tempo", "hold", "mark"]):
    if not groups:
      raise RuntimeError(
        "Invalid. Mark instruction before Group instruction.\n{}"
        .format(label["raw_line"]))
    mark = decode_mark_instruction(label, instructions)
    update_group_mark_info(groups[-1], mark, framerate)
    return None

  first_label = decode_group_instruction(label, instructions)
  if first_label not in config:
    raise RuntimeError(
      "Label must start with a group name, 'tempo', 'hold', 'mark' or 'end'.\n"
      "Invalid label: '{}'".format(label["raw_line"]))
  group = build_group_entry(label, config[config.index(first_label)])
  group["group_idx"] = len(groups)
  return group


def timestamp_checks(timestamp, last_timestamp, framerate, label_info, logger):
  if timestamp == last_timestamp:
    logger.warning(
      "Difference of 0 calculated for timestamp {} at {:.03f} fps ({:.03f}s).\n"
      "Duplicated mark for same timestamp due to framerate calculation? \n{}"
      .format(timestamp, framerate, round(1 / framerate, 6), label_info))
  if timestamp < last_timestamp:
    raise RuntimeError(
      "Negative timestamp calculated. Are timestamps out of order?\n{}"
      .format(label_info))


def group_timing_error_checks(group, logger):
  print_function_entrance(logger, "7;38;5;184")
  num_files = group["num_files"]
  num_holds = group["holds"]
  num_marks = len(group["marks"])

  if num_marks == num_holds:
    logger.debug("Group with all holds '{}'".format(group["group_config"]))
    if num_holds > num_files:
      logger.warning(
        "More holds than files in group:\n{}Num holds: {}\tNum files: {}"
        .format(group["marks"][0]["raw_line"], num_holds, num_files))
  elif (num_files - num_holds) / (num_marks - num_holds) < 1 or num_files / num_marks < 1:
    logger.warning(
      "Number of files ({}) is less than the number of marks ({}) in group:\n{}" \
      .format(num_files, num_marks, group["marks"][0]["raw_line"]))

  total_num_frames = sum(1 if mark["hold"] and mark["num_frames"] else mark["num_frames"] for mark in group["marks"])
  if num_files > total_num_frames:
    holds = " (including {} hold{})".format(num_holds, "s" if num_holds > 1 else "") if num_holds else ""
    logger.warning(
      "Number of files ({}) is more than the number of frames available ({}){}."
      " Reducing number of files to fit into frames:\n{}"
      .format(num_files, total_num_frames, holds, group["marks"][0]["raw_line"]))


def finalize_group(group, args, logger):
  print_function_entrance(logger, "7;38;5;22", group["label"]["label"])
  timestamp = args["label"]["timestamp"]
  raw_timestamp = args["label"]["raw_timestamp"]
  framerate = args["framerate"]
  duration = round(timestamp - group["timestamp_start"], 6)
  update_prev_mark_duration(group["marks"][-1], timestamp, raw_timestamp, framerate)
  group.update({
    "timestamp_end": timestamp,
    "raw_timestamp_end": raw_timestamp,
    "duration": duration,
    "num_frames": round_up(duration * framerate),
  })
  group_timing_error_checks(group, logger)
  build_timings(group, framerate, logger)
  return group["timings"]


def get_last_non_comment_label(labels):
  idx = len(labels) - 1
  while idx >= 0 and "comment_only" in labels[idx]:
    idx -= 1
  if idx == -1:
    return None, None
  return idx, labels[idx]


def handle_comment(label, label_text):
  comment_split = label_text.split("#")
  if comment_split[0] == "":
    label.update({"comment_only": True})
  else:
    label.update({"comment": "#".join(comment_split[1:]).lstrip(), "label": comment_split[0].rstrip()})


def handle_group_label(timings, groups, args, logger):
  group = decode_groups_and_marks(groups, args)
  if group:
    if groups: # Now all marks are in place, calculate the timestamps.
      timings = insert_items_into_timings(timings, finalize_group(groups[-1], args, logger), logger)
    groups.append(group)
  return timings, groups


def handle_jump_timing(timings, jump, framerate):
  max_timestamp = round(round_up(timings[-1]["raw_timestamp"] * framerate) / framerate, 6)
  if not 0.0 < jump < max_timestamp:
    raise RuntimeError("{} jump point is invalid. Must be between 0.0 and {}".format(jump, max_timestamp))

  last_valid_idx = len(timings) - 1
  for rev_idx, entry in enumerate(reversed(timings)):
    idx = last_valid_idx - rev_idx
    if "outpoint" not in entry:
      continue
    for x in ["timestamp", "outpoint"]:
      entry[x] = round(round_up((entry[x] - jump) * framerate) / framerate, 6)
    if entry["timestamp"] <= 0:
      entry["timestamp"] = 0
      entry["duration"] = entry["outpoint"]
      return timings[idx:]

  raise RuntimeError("handle_jump_timing never returned")


def process_labels(args, logger):
  args = {
    "content": args[0],
    "framerate": args[1],
    "config": args[2],
    "delimiter": args[3],
    "jump": args[4],
  }
  labels = []
  groups = []
  timings = []
  last_timestamp = -1
  for i, line in enumerate(args["content"]):
    if line.strip() == "" or line.strip().startswith("#"): # Ignore commented and blank lines
      continue
    raw_timestamp, label_text = parse_label_line(line)
    # Align the timestamp with the framerate, always before the mark
    timestamp = round(int(raw_timestamp * args["framerate"]) / args["framerate"], 6)
    label = {
      "label": label_text,
      "timestamp": timestamp,
      "raw_timestamp": round(raw_timestamp, 6),
      "raw_line": line.rstrip(),
    }
    args.update({"label": label})
    # Ignore comment at the start of the label, but save comments within valid labels
    if "#" in label_text:
      handle_comment(label, label_text)
    lncl_idx, last_non_comment_label = get_last_non_comment_label(labels)
    if last_non_comment_label and "comment_only" not in label:
      label_info = "Line number: 'label'\n{}: '{}'\n{}: '{}'".format(
        lncl_idx + 1, last_non_comment_label["raw_line"], i + 1, label["raw_line"])
      timestamp_checks(timestamp, last_timestamp, args["framerate"], label_info, logger)
      if timestamp > 0:
        last_non_comment_label["duration"] = round(timestamp - last_timestamp, 6)
    if "comment_only" not in label:
      # Don't add comments to the running timestamp calculations
      last_timestamp = timestamp
    if "end" == label_text:
      label["end"] = True
      timings = insert_items_into_timings(timings, finalize_group(groups[-1], args, logger), logger)
      timings.append({"label": label["raw_line"], "timestamp": timestamp, "raw_timestamp": raw_timestamp})
    elif "comment_only" in label:
      timings = insert_items_into_timings(timings, [{"label": label["raw_line"], "timestamp": timestamp,
                                                     "raw_timestamp": raw_timestamp}], logger)
    else:
      timings, groups = handle_group_label(timings, groups, args, logger)

    labels.append(label)
  _, last_non_comment_label = get_last_non_comment_label(labels)
  if "end" not in last_non_comment_label:
    raise RuntimeError("The last label must be 'end'\n{}".format(last_non_comment_label["raw_line"]))

  if args["jump"] > 0:
    timings = handle_jump_timing(timings, args["jump"], args["framerate"])

  return ([["# {}".format(t["label"]) if "label" in t else t["file"],
           "{}".format(format_float(t.get("duration", 0)))] for t in timings],
          last_non_comment_label["timestamp"])
