# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# runner/timing_builder.py

import bisect

from pprint import pformat

from .parser_utils import correct_rounding_errors, print_function_entrance


def linear_scale_indices(args, logger, timing=False):
  # One function with two uses:
  # 1. Calculating offsets when scaling between numbers of files.
  # 2. Calculating diffs of timing intervals between num_files and num_frames.
  print_function_entrance(logger, "7;38;5;77")
  key_files_offsets, idx_from, idx_to, current, target = args
  logger.debug("current: {} target: {} timing: {}".format(current, target, timing))

  if target == 1 and not timing:
    logger.debug("indices 1: [0]")
    return [0]

  raw_scaled = [i * current / (target - (0 if timing else 1))
                for i in range(target + (1 if timing else 0))]
  key_range = (True if timing else
               key_files_offsets[key_files_offsets.index(idx_from):
                                 key_files_offsets.index(idx_to) + 1])

  indices = correct_rounding_errors(current, logger, raw_scaled, key_files=key_range)
  logger.debug("indices {}: {}".format(len(indices), indices))

  if not timing:
    missing_keys = [
      {i: x} for i, x in enumerate(key_files_offsets)
      if x - idx_from not in indices and idx_from <= x <= idx_to
    ]
    if missing_keys:
      logger.warning("missing_keys: {}".format(missing_keys))
      logger.warning("key_files_offsets: {}".format(key_files_offsets))
      logger.warning("idx_from: {} idx_to: {}".format(idx_from, idx_to))

  else:
    diffs = [indices[i+1] - indices[i] for i in range(len(indices) - 1)]
    logger.debug("{} {} {} diffs".format([0]+diffs, sum(diffs), len(diffs)))

  logger.debug("Scaled indices:\n{}".format(indices))
  return indices


def append_group_timings(args, logger):
  group, file_idx, running_timestamp, duration= args
  new_entry = {
    "file": group["files"][file_idx],
    "timestamp": round(running_timestamp, 6),
    "inpoint": round(running_timestamp, 6),
    "outpoint": round(running_timestamp + duration, 6),
    "duration": duration,
  }
  print_function_entrance(logger, "7;38;5;216")
  logger.debug(pformat(new_entry))
  return new_entry


def validate_timestamp_alignment(running, expected, logger):
  if round(running, 3) != expected:
    logger.warning(
      "running timestamp {} != timestamp {}"
      .format(round(running, 3), expected))
    raise RuntimeError(
      "running timestamp {} != timestamp {}"
      .format(round(running, 3), expected))
  return expected


def add_label_timing(group, mark, timestamp, logger):
  timing = {"label": mark["raw_line"], "timestamp": timestamp}
  group["timings"].append(timing)
  logger.debug("\nAdded timings: \t{}\n".format(timing))


def handle_hold_or_single_file(args, logger):
  group, mark, file_idx, timestamp = args
  if mark["hold"]:
    file_idx = mark["key_files_offsets"][0]
  logger.debug("hold? {} num_files {}".format(mark["hold"], mark["num_files"]))
  duration = mark["duration"]
  if file_idx >= len(group["files"]):
    file_idx -= 1
  group["timings"].append(append_group_timings((group, file_idx, timestamp, duration), logger))
  file_idx += 1
  logger.debug("incrementing file_idx {} with duration {}".format(file_idx, duration))
  return file_idx, timestamp + duration


def handle_zero_segment(args, logger):
  group, mark, timestamp = args
  logger.debug("hold? {} num_files {}".format(mark["hold"], mark["num_files"]))
  duration = mark["duration"]
  idx = mark["key_files_offsets"][0]
  group["timings"].append(append_group_timings((group, idx, timestamp, duration), logger))
  return timestamp + duration


def generate_file_indices(args, logger):
  kf_offsets, idx_from, idx_to, n_from, n_to = args
  if n_to == n_from:
    return [i + idx_from for i in range(n_to)]
  assert n_to != 0
  return [offset + idx_from for offset in linear_scale_indices((kf_offsets, idx_from, idx_to, n_from, n_to), logger)]


def get_file_indices_for_segment(args, logger):
  kf_offsets, kf_diffs, segment_idx, n_to = args
  # Retrieves the indices for the files associated with a segment.
  try:
    n_from = kf_diffs[segment_idx]
  except IndexError as e:
    raise IndexError("Index {} into key_files_diffs (length: {}) failed."
                     .format(segment_idx, len(kf_diffs))) from e

  idx_from = kf_offsets[segment_idx]
  idx_to = kf_offsets[segment_idx + 1]
  assert len(kf_offsets) > 1, "kf_offsets only has one entry"

  file_indices = generate_file_indices((kf_offsets, idx_from, idx_to, n_from, n_to), logger)
  return n_from, idx_from, idx_to, file_indices


def calculate_timing_diffs(args, logger):
  frames, n_to, framerate, kf_offsets, idx_from, idx_to = args
  if n_to == 1:
    return [round(frames / framerate, 6)]
  if frames == n_to:
    return [round(1 / framerate, 6)] * frames
  scaled = linear_scale_indices((kf_offsets, idx_from, idx_to, frames, n_to), logger, True)
  return [round((scaled[n + 1] - scaled[n]) / framerate, 6) for n in range(n_to)]


def validate_and_update_files(args, logger):
  group, file_indices, kf_diffs, mark, timing_diffs, segment_idx, timestamp, file_idx = args
  # Iterates over files for a segment and updates the group's timing.
  for i, _ in enumerate(file_indices):
    # Protect from going over the edge of the files list
    current_file_idx = min(file_indices[i], len(group["files"]) - 1)
    try:
      _ = group["files"][current_file_idx]
    except IndexError as e:
      logger.error("Invalid file_idx {} (max {})".format(current_file_idx, len(group["files"]) - 1))
      raise IndexError("file_idx {} into key_files_diffs (length: {}) caused exception."
                       .format(current_file_idx, len(kf_diffs))) from e

    duration = timing_diffs[i]
    logger.debug("Segment {}: setting file_idx {} with duration {}"
                 .format(segment_idx, current_file_idx, duration))
    group["timings"].append(append_group_timings((group, current_file_idx, timestamp, duration), logger))
    logger.debug("Segment {}: Adding duration {} to running_timestamp {:.3f}"
                 .format(segment_idx, duration, timestamp))
    timestamp += duration
    file_idx = current_file_idx

    if round(timestamp, 6) > round(mark["timestamp"] + mark["duration"], 6):
      logger.debug("Segment {}: running_timestamp {} > timestamp + duration {}"
             .format(segment_idx, round(timestamp,6), round(mark["timestamp"] + mark["duration"],6)))
      logger.debug(len(group["files"]))
      # Notice that we’re using a generator expression here.
      logger.debug(sum(sum(m['key_files_diffs']) for m in group["marks"]), max(1, len(group["files"]) - 1))
      raise RuntimeError("Segment {}: Timestamp overflow – this shouldn't happen!".format(segment_idx))
  return file_idx, timestamp


def process_segment(args, logger): # pylint: disable=too-many-locals
  segment_idx, mark, group, file_idx, timestamp, framerate = args
  # Extract frequently used mark information.
  kf_offsets = mark["key_files_offsets"]
  kf_diffs = mark["key_files_diffs"]
  total_frames = mark["play_num_frames"]
  segment_frames = mark["segment_frames"]

  # Compute maximum frames for all segments.
  segment_max_frames = correct_rounding_errors(
    total_frames, logger,
    [(seg * total_frames) / sum(segment_frames) for seg in segment_frames])

  n_to = segment_frames[segment_idx]

  logger.debug("Segment {}: num_files_to {} / num_files_from (from diff lookup) will be derived below."
               .format(segment_idx, n_to))
  logger.debug("Segment {}: Total frames: {}. Frame distribution: {}."
               .format(segment_idx, total_frames, segment_frames))

  # Obtain file indices for the segment.
  n_from, idx_from, idx_to, file_indices = get_file_indices_for_segment(
    (kf_offsets, kf_diffs, segment_idx, n_to), logger)
  logger.debug("Segment {}: idx_from: {}, idx_to: {}, n_from: {}, n_to: {}, mark num_frames: {}"
               .format(segment_idx, idx_from, idx_to, n_from, n_to, mark["num_frames"]))

  # Compute timing differences (assuming calculate_timing_diffs is defined).
  timing_diffs = calculate_timing_diffs(
    (segment_max_frames[segment_idx], n_to, framerate, kf_offsets, idx_from, idx_to), logger)
  logger.debug("Segment {}: timing_diffs: len {}, sum {:.3f}, diffs: {}"
               .format(segment_idx, len(timing_diffs), sum(timing_diffs), timing_diffs))

  # Update file list and timings inside the segment.
  file_idx, timestamp = validate_and_update_files(
    (group, file_indices, kf_diffs, mark, timing_diffs, segment_idx, timestamp, file_idx), logger)
  logger.debug("Segment {}: completed. Updated timestamp: {:.3f}.".format(segment_idx, timestamp))
  logger.debug("Segment {}: mark details:\n{}".format(segment_idx, pformat(mark)))
  return file_idx, timestamp


def handle_segment_distribution(args, logger):
  mark, group, file_idx, timestamp, framerate = args
  num_segment_frames = len(mark["segment_frames"])
  for idx in range(num_segment_frames):
    file_idx, timestamp = process_segment((idx, mark, group, file_idx, timestamp, framerate), logger)

  return file_idx, timestamp


def validate_final_timestamp(actual, expected, logger):
  if round(actual, 6) != expected:
    logger.info("{}, {}".format(round(actual, 6), expected))
    raise RuntimeError("Miscalculated timestamps. Needs manual inspection.")


def build_timings(group, framerate, logger):
  print_function_entrance(logger, "7;38;5;220", group["label"]["label"])
  file_idx = 0
  group["timings"] = []
  running_timestamp = group["timestamp_start"]
  logger.debug("group timestamp_start {:.3f} end {:.3f}"
               .format(group["timestamp_start"], group["timestamp_end"]))

  for mark in group["marks"]:
    running_timestamp = validate_timestamp_alignment(running_timestamp, mark["timestamp"], logger)
    add_label_timing(group, mark, running_timestamp, logger)

    if mark["hold"] or 1 == mark["num_files"] or 1 == len(group["files"]):
      file_idx, running_timestamp = handle_hold_or_single_file((group, mark, file_idx, running_timestamp), logger)

    elif sum(mark["segment_frames"]) == 0:
      running_timestamp = handle_zero_segment((group, mark, running_timestamp), logger)
      logger.debug("keeping file_idx to {} and setting from key_files_offsets {} with duration {}"
                   .format(file_idx, mark["key_files_offsets"][0], mark["duration"]))
    else:
      file_idx, running_timestamp = handle_segment_distribution((
        mark, group, file_idx, running_timestamp, framerate), logger)

  validate_final_timestamp(running_timestamp, group["timestamp_end"], logger)


def get_key_file_offsets_from_replay_stack(group, logger):
  print_function_entrance(logger, "7;38;5;164")
  last_file_idx = len(group["files"])
  if "replay_stack" not in group:
    return [0, last_file_idx]
  key_file_offsets = [0]
  for ins in group["replay_stack"]:
    # pprint(ins)
    init_offset = ins["num_files_from"]
    if init_offset not in key_file_offsets:
      key_file_offsets.append(init_offset)
    if ins["instruction"] == "rep":
      repeat_val = ins["value"]
      num_files_to_repeat = int((ins["num_files_to"] - init_offset) / (repeat_val - 1))
      running_total = init_offset
      offsets_snapshot = key_file_offsets[1:
        -1 if init_offset == key_file_offsets[-1] and len(key_file_offsets) > 2 else None]
      for i in range(repeat_val - 1):
        for offset in offsets_snapshot:
          if running_total + offset - 1 not in key_file_offsets:
            key_file_offsets.append(running_total + offset - 1)
        running_total += num_files_to_repeat
        if running_total not in key_file_offsets:
          key_file_offsets.append(running_total)
    elif ins["instruction"] == "boom":
      diff = int(ins["num_files_to"] - init_offset)
      logger.debug("boom diff: {}".format(diff))
      running_total = init_offset

      offsets_snapshot = key_file_offsets[:]
      for i in range(len(offsets_snapshot) - 1):
        this_offset = offsets_snapshot[i+1] - offsets_snapshot[i] - 1
        if running_total + this_offset not in key_file_offsets:
          key_file_offsets.append(running_total + this_offset)
        running_total += this_offset
    if "num_files_to" in ins and ins["num_files_to"] not in key_file_offsets:
      key_file_offsets.append(ins["num_files_to"])
  assert last_file_idx in key_file_offsets, ("last_file_idx {} not in key_file_offsets {}"
                                             .format(last_file_idx, key_file_offsets))
  return key_file_offsets


def set_remaining_goal(goal, fixed, marks, logger):
  print_function_entrance(logger, "7;38;5;93")
  allocations = [1 if i in fixed else None for i in range(len(marks))]
  remaining_goal = goal - len(fixed)

  if remaining_goal <= 1:
    if goal == 1:
      logger.debug("Hard coded 1 allocation with goal = 1")
      return [1], None, True
    for idx, allocation in enumerate(allocations):
      if allocation is None:
        if remaining_goal > 0:
          allocations[idx] = 1
          remaining_goal -= 1
        else:
          allocations[idx] = 0
    logger.debug("Hard coded allocation for only 1 file {}".format(allocations))
    return allocations, None, True
  return allocations, remaining_goal, False


def fixup_scaled_allocations(args, logger):
  goal, allocations, scaled_allocations, fixed, non_fixed, remaining_goal = args
  newly_fixed = {*sorted((k for k, v in scaled_allocations.items() if v < 1),
                          key=lambda k: scaled_allocations[k], reverse=True)}

  if newly_fixed and len(newly_fixed) <= remaining_goal:
    logger.debug("newly_fixed {}".format(newly_fixed))
    left_over_non_fixed = len(non_fixed - newly_fixed)
    current_allocations_total = sum(x for x in allocations if x)
    fixable_allocations_to_go = remaining_goal - left_over_non_fixed
    logger.debug("current_allocations_total {}, left_over_non_fixed {}, fixable_allocations_to_go {}, remaining_goal {}"
                 .format(current_allocations_total, left_over_non_fixed, fixable_allocations_to_go, remaining_goal))
    if len(newly_fixed) > fixable_allocations_to_go:
      logger.debug("More allocations than files, need to set some to 0")
      while len(newly_fixed) > fixable_allocations_to_go:
        to_pop = list(newly_fixed)[-1]
        allocations[to_pop] = 0
        newly_fixed.remove(to_pop)

    for i in newly_fixed:
      allocations_to_go = goal - len(newly_fixed) + left_over_non_fixed - current_allocations_total
      logger.debug("current_allocations_total {}, allocations_to_go {}, remaining_goal {}"
                   .format(current_allocations_total, allocations_to_go, remaining_goal))
      allocations[i] = 1
      current_allocations_total += 1
      remaining_goal -= 1
      fixed |= {i}
      non_fixed -= {i}
      if remaining_goal == 0:
        allocations = [0 if x is None else x for x in allocations]
        logger.debug("Finished forcing allocations: {}".format(allocations))
        break
      logger.debug("Forcing segment {} to {}: {}".format(i, allocations[i], allocations))


def round_all_allocations(args, logger):
  goal, allocations, scaled_allocations, fixed, non_fixed, _ = args

  if len(non_fixed) < goal:
    fixup_scaled_allocations(args, logger)
  # Round down allocations
  allocations_int = {i: int(scaled_allocations[i]) for i in non_fixed}

  # Compute remaining files after flooring
  allocated_so_far = sum(allocations_int.values()) + len(fixed)
  remaining_files = goal - allocated_so_far

  logger.debug("Allocated so far: {}, Remaining files: {}".format(allocated_so_far, remaining_files))

  if remaining_files > 0:
    # Sort non-fixed marks by largest fractional remainder
    fractional_parts = {i: scaled_allocations[i] - allocations_int[i] for i in non_fixed}
    sorted_indices = sorted(
      non_fixed,
      key=lambda i: (-scaled_allocations[i] if allocations_int[i] == 0 else 0, -fractional_parts[i]))
    logger.debug("Non-fixed indices sorted by fractional parts: {}"
                  .format([{'i': i, 'frac_parts': round(fractional_parts[i], 3)} for i in sorted_indices]))

    for i in sorted_indices[:remaining_files]:
      allocations_int[i] += 1
  else:
    logger.debug("More marks than files!")

  # Assign final allocations
  for i in non_fixed:
    allocations[i] = allocations_int[i]

  if allocations[0] == 0:
    first_non_zero_index = next((index for index, value in enumerate(allocations) if value != 0), -1)
    allocations[first_non_zero_index] -= 1
    allocations[0] += 1
  return allocations


def distribute_files_among_marks(group, logger):
  """
  Distribute group["files"] among the group's mark segments.
  Holds (where mark["hold"] is True) are fixed to 1. The remaining marks
  receive weighted allocations based on (num_frames * tempo * tempo_ratio).

  Segments with an allocation < 1 are rounded up to 1 first.
  The remaining files are distributed using rounding based on fractional parts.

  Returns a list of allocations (one per mark).
  """
  print_function_entrance(logger, "7;38;5;33")
  goal = len(group["files"])
  marks = group["marks"]

  fixed = {i for i, mark in enumerate(marks) if mark["hold"]}

  while goal - len(fixed) < 1:
    #reduce the number of files in the assigned lists to match actual number of files
    fixed = set(list(fixed)[:-1])

  allocations, remaining_goal, ret = set_remaining_goal(goal, fixed, marks, logger)
  if ret:
    return allocations

  logger.debug("Initial goal: {}, Fixed indices (holds): {}".format(goal, fixed))

  non_fixed = set(range(len(marks))) - fixed

  # Compute total weight of non-fixed marks
  all_tempos = [marks[i]["tempo"] for i in non_fixed]
  assert sum(all_tempos) != 0, "all_tempos sum is 0"
  logger.debug("len(all_tempos) {} / sum(all_tempos) {}".format(len(all_tempos), sum(all_tempos)))
  tempo_ratio = len(all_tempos) / sum(all_tempos)
  total_weight = sum(marks[i]["num_frames"] * marks[i]["tempo"] * tempo_ratio for i in non_fixed)
  logger.debug("Total weight: {}, Remaining goal: {}".format(total_weight, remaining_goal))

  if total_weight <= 0:  # Edge case: no weight left, distribute equally
    scaled_allocations = {i: round(remaining_goal / len(non_fixed), 6) for i in non_fixed}
  else:
    weight_factor = remaining_goal / total_weight
    scaled_allocations = {
      i: round(marks[i]["num_frames"] * marks[i]["tempo"] * tempo_ratio * weight_factor, 6)
      for i in non_fixed}

  sum_scaled = round(sum(scaled_allocations.values()), 3)
  logger.debug("Scaled allocations: {}".format(scaled_allocations))
  logger.debug("Sum Scaled allocations: {}".format(sum_scaled))

  allocations = round_all_allocations(
    (goal, allocations, scaled_allocations, fixed, non_fixed, remaining_goal), logger)
  logger.debug("Final distribution: {}".format(allocations))
  return allocations


def prepare_mark_data(group, files_offsets, logger):
  print_function_entrance(logger, "7;38;5;60")
  group_num_files = len(group["files"])
  num_files_offsets = len(files_offsets)
  num_marks = len(group["marks"])

  # Identify which marks are fixed (holds)
  fixed = {i for i, mark in enumerate(group["marks"])
           if mark["hold"] and files_offsets[i]}
  num_frames_offsets = [mark["num_frames"] for mark in group["marks"]]

  # Reduce the duration scaled offsets by the number of frames available.
  smallest = [
    1 if i in fixed else min(files_offsets[i], num_frames_offsets[i])
    for i in range(num_marks)]
  sum_smallest = sum(smallest)
  goal = [0 if i in fixed else n for i, n in enumerate(num_frames_offsets)]
  logger.debug("goal: {}".format(goal))

  logger.debug("{} {} num_frames".format(num_frames_offsets, sum(num_frames_offsets)))
  logger.debug("{} {} files_offsets".format(files_offsets, sum(files_offsets)))
  logger.debug("{} {} smallest".format(smallest, sum_smallest))

  if (sum_smallest >= group_num_files and len(smallest) > 1):
    logger.debug("sum smallest {} num files {}".format(sum_smallest, group_num_files))
    if sum_smallest > group_num_files:
      while sum_smallest > group_num_files:
        smallest_order = sorted((i for i, v in enumerate(goal) if v > 0 and smallest[i] > 0), key=lambda i: goal[i])
        goal[smallest_order[0]] += 1
        smallest[smallest_order[0]] -= 1
        sum_smallest = sum(smallest)
        logger.debug("adjusted indice {}".format(smallest_order[0]))
      logger.debug("sum smallest {} num files {}".format(sum_smallest, group_num_files))
  else:
    smallest_correction = correct_rounding_errors(
      sum(goal), logger,
      [0 if i in fixed else files_offsets[i] * sum(goal) / (group_num_files - group["holds"])
       for i in range(num_files_offsets)])

    logger.debug("{} {} smallest_correction"
                .format(smallest_correction, sum(smallest_correction)))
    # Now we have the final tempo scaled files distribution, allocate num_files.
    smallest = [ # Add back in the holds
      max(1, min(smallest_correction[i], num_frames_offsets[i], files_offsets[i]))
      for i in range(len(smallest))]

  logger.debug("{} {} smallest".format(smallest, sum(smallest)))
  return smallest


def compute_segment_slices(key_files_indices, files_offsets, group, logger):
  print_function_entrance(logger, "7;38;5;54")
  total_files = sum(files_offsets)
  group_num_files = len(group["files"])

  assert total_files == group_num_files, "sum(files_offsets)={} != group_num_files={}".format(
    total_files, group_num_files)

  running_total = 0
  prev_key_pos = 0
  segment_slices = []
  segment_offsets = []
  for num_files in files_offsets:
    running_total += num_files
    if running_total not in key_files_indices:
      bisect.insort_left(key_files_indices, running_total) # ensure `running_total` is in the list
    key_pos = key_files_indices.index(running_total)
    if running_total not in segment_offsets:
      segment_offsets.append(running_total)
    slice_ = key_files_indices[prev_key_pos:key_pos+1]
    assert slice_, "Expected non-empty segment slice"
    segment_slices.append(slice_)
    logger.debug("slice {}: {}\tkey_pos {} for frame/idx {}\tnum_files: {}\tsegment_offsets: {}"
                 .format(len(segment_slices), slice_, key_pos, running_total, num_files, segment_offsets))
    logger.debug("segment_slices: {}".format(segment_slices))
    prev_key_pos = key_pos
  assert running_total == group_num_files, ("running total offset miscalculation! {} != {}"
                                            .format(running_total, group_num_files))

  logger.debug("{} updated key_files_indices".format(key_files_indices))
  logger.debug("{} segment_offsets".format(segment_offsets))
  logger.debug("{} segment_slices".format(segment_slices))
  if sum(segment_offsets) == 0 and len(segment_offsets) > 1:
    segment_slices[0] = [1]
    logger.debug("manually updating {} segment_slices".format(segment_slices))
  return segment_slices


def update_marks_with_segment_data(group, segment_slices, smallest, logger):
  print_function_entrance(logger, "7;38;5;56")
  group_num_files = len(group["files"])
  num_marks = len(group["marks"])

  for i, mark in enumerate(group["marks"]):
    seg = segment_slices[i]
    num_files = smallest[i]

    # Compute key_files_diffs based on the segment slice.
    if seg[-1]-seg[0] == 0:
      assert num_marks > 1
      key_files_diffs = [0]
      logger.debug("Compensate: using key_files_diffs = {} for mark {}".format(key_files_diffs, i))
    else:
      # Compute differences between consecutive key file indices.
      key_files_diffs = [seg[idx + 1] - seg[idx] for idx in range(len(seg) - 1)]


    # Determine segment_frames with rounding correction if applicable.
    if num_files > 1:
      # Scale each diff to contribute to num_files.
      # Guard against division by zero:
      total_diff = sum(key_files_diffs)
      if total_diff == 0:
        scaled_diffs = [0 for _ in key_files_diffs]
      else:
        scaled_diffs = [d * num_files / total_diff for d in key_files_diffs]
      segment_frames = correct_rounding_errors(num_files, logger, scaled_diffs)
      assert sum(segment_frames) == num_files, "Rounding correction failed: sum(segment_frames) != num_files"
    else:
      segment_frames = [num_files]

    logger.debug("key_files_diffs: {} seg: {}\tsegment_frames: {}, num_files {}"
                 .format(key_files_diffs, seg, segment_frames, num_files))

    # Update mark with calculated data.
    mark.update({
      "key_files_diffs": key_files_diffs,
      "key_files_offsets": seg,
      "num_files": num_files,
      "segment_frames": segment_frames,
    })

  # Final consistency check across all marks.
  total_diffs = sum(sum(m["key_files_diffs"]) for m in group["marks"])
  if total_diffs != group_num_files:
    if group["marks"][0]["key_files_diffs"] == [0]:
      group["marks"][0]["key_files_diffs"] = [1]
      logger.debug("manually updating mark[0]['key_files_diffs'] from 0 to 1")
    else:
      raise RuntimeError("total_diffs {} != group_num_files {}".format(total_diffs, group_num_files))
  return total_diffs


def build_mark_segments(group, logger):
  print_function_entrance(logger, "7;38;5;64")
  # Build the list of key file offsets for the marks, coping with float rounding errors
  key_files_indices = get_key_file_offsets_from_replay_stack(group, logger)
  logger.debug("{} raw key_files_indices".format(key_files_indices))

  files_offsets = distribute_files_among_marks(group, logger)
  num_marks = len(group["marks"])
  num_files_offsets = len(files_offsets)

  if num_marks != num_files_offsets: # Pad out the files_offsets when not enough files for num_marks
    files_offsets += [0] * (num_marks - num_files_offsets)

  smallest = prepare_mark_data(group, files_offsets, logger)
  segment_slices = compute_segment_slices(key_files_indices, files_offsets, group, logger)
  return update_marks_with_segment_data(group, segment_slices, smallest, logger)
