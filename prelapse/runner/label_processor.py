# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# runner/label_processor.py

from ..common import format_float
from .parser_utils import print_function_entrance
from .timing_builder import build_timings, build_mark_segments


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
  # We have an index or a slice
  first_label, index = indexed
  sliced = index.split(":")  # Search for the slice char
  if len(sliced) > 2:
    raise RuntimeError(
      "Only one ':' allowed when defining group slice. Invalid label:\n{}"
      .format(label["raw_line"]))
  if len(sliced) == 1:   # We have an index
    index = parse_index(index, first_label)
    start_idx, end_idx = index, index+1 if index > 0 else None
    label["index"] = index
  elif len(sliced) == 2: # We have a slice
    slice_values = parse_slice(sliced, first_label)
    label["slice"] = slice_values
    start_idx, end_idx = slice_values
  else:
    raise RuntimeError("Impossible slice count")
  return first_label, start_idx, end_idx


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
    "rev": lambda files, val: files[::-1],
    "rep": lambda files, val: files + (val - 1) * files[int(files[0] == files[-1]):],
    "boom": lambda files, val: files + files[-2::-1],
    "tempo": lambda files, val: files,
    "hold": lambda files, val: files,
  }
  files = group_config.items[label["files_start_idx"] : label["files_end_idx"]]
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
  group = {
    "label": label,
    "files": populate_group_files_from_instructions(label, group_config),
    "group_config": group_config,
    "marks": [add_first_label_to_marks(label)],
    "timestamp_start": float(label["timestamp"]),
    "holds": len([i for i in label["group_instructions"] if "hold" in i]),
  }
  if "replay_stack" in label:
    group["replay_stack"] = label["replay_stack"]
    del label["replay_stack"]
  return group


def build_mark_entry(label, hold_present, tempo=None):
  mark = {
    "timestamp": float(label["timestamp"]),
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
    first_label, start_idx, end_idx = parse_index_and_slice(label, first_label)
  else:
    start_idx, end_idx = None, None
  label.update({
    "group_instructions": group_instructions,
    "files_start_idx": start_idx,
    "files_end_idx": end_idx,
  })
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


def update_prev_mark_duration(mark, timestamp, framerate):
  duration = round(timestamp - mark["timestamp"], 6)
  num_frames = round(duration * framerate)
  mark.update({
    "duration": duration,
    "num_frames": num_frames,
    "num_files": 1 if mark["hold"] else 0, # To be decided later
    "play_num_frames": 1 if mark["hold"] else num_frames,
  })


def update_group_mark_info(group, mark, framerate):
  last_mark = group["marks"][-1]
  if "tempo" not in mark:
    mark["tempo"] = last_mark["tempo"]
  update_prev_mark_duration(last_mark, mark["timestamp"], framerate)
  if mark["hold"]:
    group["holds"] += 1
  group["marks"].append(mark)


def decode_groups_and_marks(label, delimiter, groups, config, framerate):
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
      "Invalid label: '{}'"
      .format(label["raw_line"]))
  group = build_group_entry(label, config[config.index(first_label)])
  group["group_idx"] = len(groups)
  return group


def timestamp_checks(timestamp, last_timestamp, label, prev_label):
  if timestamp > 0.0 and timestamp == last_timestamp:
    raise RuntimeError(
      "Difference of 0 calculated. Duplicated mark for same timestamp?\n{}\n{}"
      .format(label, prev_label))
  if timestamp < last_timestamp:
    raise RuntimeError(
      "Negative timestamp calculated. Are timestamps out of order?\n{}\n{}"
      .format(prev_label, label))


def group_timing_error_checks(group, logger):
  print_function_entrance(logger, "7;38;5;184")
  num_files = len(group["files"])
  num_holds = group["holds"]
  num_marks = len(group["marks"])

  if num_marks == num_holds:
    # raise RuntimeError(
    logger.warning(
      "Group with all holds? OK.. {}"
      .format(group["group_config"]))
    if num_holds > num_files:
      raise RuntimeError(
        "More holds than files in group:\n{}\nNum holds: {}\tNum files: {}"
        .format(group["marks"][0]["raw_line"], num_holds, num_files))
  elif (num_files - num_holds) / (num_marks - num_holds) < 1 or num_files / num_marks < 1:
    logger.warning(
      "Number of files ({}) is less than the number of marks ({}) in group:\n{}\n" \
      .format(num_files, num_marks, group["marks"][0]["raw_line"]))

  total_num_frames = sum(mark["play_num_frames"] for mark in group["marks"])
  if num_files > total_num_frames:
    logger.warning(
      "Number of files ({}) is more than the number of frames available ({}){}."
      " Reducing number of files to fit into frames:\n{}\n"
      .format(
        num_files, total_num_frames,
        " (including {} holds)".format(group["holds"]) if group["holds"] else "",
        group["marks"][0]["raw_line"]))


def finalize_group(group, timestamp, framerate, logger):
  print_function_entrance(logger, "7;38;5;22", group["label"]["label"])
  duration = timestamp - float(group["timestamp_start"])
  update_prev_mark_duration(group["marks"][-1], timestamp, framerate)
  group.update({
    "timestamp_end": timestamp,
    "duration": duration,
    "num_frames": round(duration * framerate),
  })
  group_timing_error_checks(group, logger)
  total_diffs = build_mark_segments(group, logger)
  num_files = len(group["files"])
  if total_diffs != num_files:
    raise RuntimeError("total_diffs {} != num_files {}".format(total_diffs, num_files))

  build_timings(group, framerate, logger)

  return group["timings"]


def handle_jump_timing(timings, jump):
  max_timestamp = float([t for t in timings[::-1] if "outpoint" in t][0]["outpoint"])
  if jump < 0.0 or jump >= max_timestamp:
    raise RuntimeError(
      "{} jump point is invalid. Must be between 0.0 and {}"
      .format(jump, max_timestamp))

  # Keep track of the last/next valid index while going backwards through timings
  idx = 0
  for i, entry in enumerate(timings[::-1]):
    if "inpoint" in entry:
      for x in ["inpoint", "outpoint"]:
        entry[x] = "{:.6f}".format(float(entry[x]) - jump)
      if float(entry["inpoint"]) < 0:
        if float(entry["outpoint"]) > 0:
          idx = len(timings) - 1 - i
        first_entry = timings[idx]
        if float(first_entry["inpoint"]) != 0:
          first_entry["duration"] = float(first_entry["outpoint"])
          first_entry["inpoint"] = "{:.6f}".format(0)
        return timings[idx:]
      idx = len(timings) - 1 - i
  return None


def insert_items_into_timings(timings, items):
  # Sort both lists first by timestamp.
  timings_sorted = sorted(timings, key=lambda x: x["timestamp"])
  items_sorted = sorted(items, key=lambda x: x["timestamp"])

  merged = []
  i, j = 0, 0
  while i < len(timings_sorted) and j < len(items_sorted):
    if timings_sorted[i]["timestamp"] <= items_sorted[j]["timestamp"]:
      merged.append(timings_sorted[i])
      i += 1
    else:
      merged.append(items_sorted[j])
      j += 1

  if i < len(timings_sorted):
    merged.extend(timings_sorted[i:])
  if j < len(items_sorted):
    merged.extend(items_sorted[j:])

  return merged


def get_last_non_comment_label(labels):
  return next((l for l in labels[::-1] if "comment_only" not in l), None)


def handle_comment(label, label_text):
  comment_split = label_text.split("#")
  label.update(
    {"comment_only": True} if comment_split[0] == "" else
    {"comment": "#".join(comment_split[1:]).lstrip(),
      "label": comment_split[0].rstrip()}
  )


def process_labels(args, logger): # pylint: disable=too-many-locals
  content, framerate, config, delimiter, jump = args
  labels = []
  groups = []
  timings = []
  last_timestamp = 0.0
  for line in content:
    line = line.rstrip()
    if line == "" or line.startswith("#"): # Ignore commented and blank lines
      continue
    timestamp, label_text = parse_label_line(line)
    # Align the timestamp with the framerate by rounding up
    timestamp = int((timestamp * framerate) + 0.5) / framerate
    label = {
      "label": label_text,
      "timestamp": "{}".format(format_float(timestamp)),
      "raw_line": line,
    }
    # Ignore comment at the start of the label, but save comments within valid labels
    if "#" in label_text:
      handle_comment(label, label_text)
    last_non_comment_label = get_last_non_comment_label(labels)
    if last_non_comment_label:
      timestamp_checks(timestamp, last_timestamp, label["raw_line"],
                       last_non_comment_label["raw_line"])
    # Don't add comments to the running timestamp calculations
    if timestamp > 0.0:
      last_non_comment_label["duration"] = round(timestamp - last_timestamp, 6)
      last_timestamp = timestamp
    if "end" == label_text:
      label["end"] = True
      timings = insert_items_into_timings(timings,
                                          finalize_group(groups[-1], timestamp, framerate, logger))
      timings.append({"label": label["raw_line"], "timestamp": timestamp})
    elif "comment_only" in label:
      timings = insert_items_into_timings(timings,
                                          [{"label": label["raw_line"], "timestamp": timestamp}])
    else:
      group = decode_groups_and_marks(label, delimiter, groups, config, framerate)
      if group:
        if groups: # Now all marks are in place, calculate the timestamps.
          timings = insert_items_into_timings(timings,
                                              finalize_group(groups[-1], timestamp, framerate, logger))
        groups.append(group)

    labels.append(label)
  last_non_comment_label = get_last_non_comment_label(labels)
  if "end" not in last_non_comment_label:
    raise RuntimeError(
      "The last label must be 'end'\n{}".format(last_non_comment_label["raw_line"]))

  if jump != 0.0:
    timings = handle_jump_timing(timings, jump)
    assert timings

  return [["# {}".format(t["label"]) if "label" in t else t["file"],
           "{}".format(format_float(t.get("duration", 0)))] for t in timings]
