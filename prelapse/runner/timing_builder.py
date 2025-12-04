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

# runner/timing_builder.py

import bisect

from ..common import print_function_entrance, round_up


def handle_zeroes(lst, goal, logger):
  print_function_entrance(logger, "7;38;5;187")
  list_length = len(lst)
  if goal <= list_length:
    alloc = [1] * goal + [0] * (list_length - goal)
    logger.debug("goal = {}, list length = {}. Returning: {}".format(goal, list_length, alloc))
    return alloc

  alloc = [1] * list_length
  remaining_goal = goal - list_length
  logger.debug("Input list: {}".format(lst))
  while remaining_goal:
    reduced_lst = [(i, round(x, 6)) for i, x in [(i, l - alloc[i] + 0.5) for i, l in enumerate(lst)] if x > 1]
    # logger.debug("Remaining goal: {}, Reduced list: {}, allocated: {}".format(remaining_goal, reduced_lst, alloc))
    if not reduced_lst:
      logger.debug("Breaking out of doomed loop with nothing in the reduced list")
      for i in range(remaining_goal):
        alloc[i % list_length] += 1
      break
    for i, _ in reduced_lst:
      if remaining_goal == 0:
        break
      alloc[i] += 1
      remaining_goal -= 1

  if sum(alloc) == goal and 0 not in alloc:
    logger.debug("Reached goal: {}".format(goal))
  else:
    raise RuntimeError("Unable to handle zeroes in correction. goal: {} allocated: {} {}"
                       .format(goal, sum(alloc), alloc))

  logger.debug("updated list: {}".format(alloc))
  return alloc


def handle_over_under_rounding(alloc, lst, goal, logger, catch_zeroes=None):
  print_function_entrance(logger, "7;38;5;188")
  sum_lst = sum(alloc)
  diff = goal - sum_lst
  logger.debug("error {}, goal {}, current_sum {}".format(diff, goal, sum_lst))
  logger.debug("current list: {}".format(alloc))
  step = 1 if diff > 0 else -1
  while diff != 0:
    candidates = sorted(((i, l, round(l - lst[i], 3)) for i, l in enumerate(alloc)),
                        key=lambda x: (x[2], x[0]), reverse=step < 0)
    logger.debug("candidates: {}".format(candidates))
    if step < 0:
      candidates = [(i, l, r) for i, l, r in candidates if l > 1]
      if catch_zeroes is not None and catch_zeroes != []:
        excluded_candidates = [i for i, x in enumerate(alloc) if i in catch_zeroes and x > 0]
        logger.debug("excluded_candidates: {}".format(excluded_candidates))
        for i in reversed(excluded_candidates):
          if alloc[i] <= 0:
            continue
          alloc[i] += step
          diff -= step
          logger.debug("Setting idx {} to {}. Diff now {}".format(i, alloc[i], diff))
          if diff == 0:
            break
        if diff == 0:
          break
      if candidates == []:
        logger.debug("Manually reducing alloc by {}".format(diff))
        i = len(alloc) - 1
        while diff:
          if alloc[i] <= 0:
            i -= 1
            continue
          alloc[i] += step
          diff -= step
          i -= 1
        if i < 0:
          raise RuntimeError("Finished reassigning all alloc to 0: {}".format(alloc))
        break
      # logger.debug("updated candidates above 1: {}".format(candidates))
    target = candidates[0][0]
    logger.debug("target: [{}] = {} -> {}".format(target, alloc[target], alloc[target] + step))
    alloc[target] += step
    diff -= step
  if diff != 0:
    raise RuntimeError("Badly miscalculated diff: {}.".format(diff))
  logger.debug("updated list: {}".format(alloc))
  return alloc


def correct_rounding_errors(logger, goal, lst, catch_zeroes=None):
  alloc = [round_up(i) for i in lst]

  # Guard against allocating zero for a segment
  if 0 in alloc and not catch_zeroes:
    print_function_entrance(logger, "7;38;5;189")
    logger.debug("detected zeros in list: {}".format(alloc))
    alloc = handle_zeroes(lst, goal, logger)
  # Guard against over/under allocating after rounding
  sum_lst = sum(alloc)
  if goal != sum_lst:
    print_function_entrance(logger, "7;38;5;189")
    alloc = handle_over_under_rounding(alloc, lst, goal, logger, catch_zeroes)
    sum_lst = sum(alloc)

  if 0 in alloc:
    logger.debug("Zeroes still present - goal: {}, {}".format(goal, alloc))
  if goal != sum_lst:
    raise RuntimeError("Still off by {}".format(goal - sum_lst))
  return alloc


def process_repeat(ins, init_offset, key_file_offsets, logger):
  repeat_count = ins["value"]
  if repeat_count <= 1:
    raise ValueError("Invalid repeat count value: {}".format(repeat_count))
  num_files_to_repeat = round_up((ins["num_files_to"] - init_offset) / (repeat_count - 1))
  logger.debug("repeat_count: {}, num files to repeat: {}".format(repeat_count, num_files_to_repeat))
  running_total = init_offset
  if init_offset == key_file_offsets[-1] and len(key_file_offsets) > 2:
    offsets_snapshot = key_file_offsets[1:-1]
  else:
    offsets_snapshot = key_file_offsets[1:]
  for _ in range(repeat_count - 1):
    for offset in offsets_snapshot:
      candidate = running_total + offset
      if candidate not in key_file_offsets:
        key_file_offsets.append(candidate)
    running_total += num_files_to_repeat
    if running_total not in key_file_offsets:
      key_file_offsets.append(running_total)
  if running_total != ins["num_files_to"]:
    raise RuntimeError("Miscalculated repeating running_total: {}. Should be {}"
                       .format(running_total, ins["num_files_to"]))
  return key_file_offsets


def process_boomerang(ins, init_offset, key_file_offsets, logger):
  running_total = init_offset - 1
  offsets_snapshot = key_file_offsets[:]
  logger.debug("boom diff: {}".format(ins["num_files_to"] - init_offset))
  for i in range(len(offsets_snapshot) - 1):
    this_offset = offsets_snapshot[i+1] - offsets_snapshot[i]
    candidate = running_total + this_offset
    if candidate not in key_file_offsets:
      key_file_offsets.append(candidate)
    running_total += this_offset
  return key_file_offsets


def get_key_file_offsets_from_replay_stack(group, logger):
  print_function_entrance(logger, "7;38;5;164")
  last_file_idx = group["num_files"]
  if "replay_stack" not in group:
    return [0, last_file_idx]
  key_file_offsets = [0]
  for ins in group["replay_stack"]:
    init_offset = ins["num_files_from"]
    if init_offset not in key_file_offsets:
      key_file_offsets.append(init_offset)
    if ins["instruction"] == "rep":
      key_file_offsets = process_repeat(ins, init_offset, key_file_offsets, logger)
    elif ins["instruction"] == "boom":
      key_file_offsets = process_boomerang(ins, init_offset, key_file_offsets, logger)
    if "num_files_to" in ins and ins["num_files_to"] not in key_file_offsets:
      raise RuntimeError("instruction num_files_to {} not in key_file_offsets: {}"
                         .format(ins["num_files_to"], key_file_offsets))

  if len(key_file_offsets) < 2:
    raise RuntimeError("not enough entries in key_file_offsets to continue: {}".format(key_file_offsets))
  if last_file_idx not in key_file_offsets:
    raise RuntimeError("last_file_idx {} not in key_file_offsets {}".format(last_file_idx, key_file_offsets))
  return key_file_offsets


def calculate_tempo_weights(non_hold_indices, logger):
  print_function_entrance(logger, "7;38;5;35")
  all_durations = []
  all_tempos = []
  tempo_scaled_durations = []
  for _, mark in non_hold_indices:
    all_durations.append(mark["raw_duration"])
    all_tempos.append(mark["tempo"])
    tempo_scaled_durations.append(mark["tempo"] * mark["raw_duration"])
  sum_tempo_scaled_durations = sum(tempo_scaled_durations)
  tempo_ratio = 1 / sum_tempo_scaled_durations
  weights = [(i, mark["raw_duration"] * mark["tempo"] * tempo_ratio) for i, mark in non_hold_indices]
  printable_weights = ["{}: {:.03f}".format(i, w) for i, w in weights]
  logger.debug("All tempos: {}, Tempo Ratio: {:.06f} Sum: {:.03f}".format(all_tempos, tempo_ratio, sum(all_tempos)))
  logger.debug("All durations: {}, Sum: {:.03f}".format(all_durations, sum(all_durations)))
  logger.debug("Tempo scaled durations: {}, Sum: {:.03f}".format(tempo_scaled_durations, sum_tempo_scaled_durations))
  logger.debug("Total weights: {}, Sum {:.03f}".format(printable_weights, sum(w for _, w in weights)))
  return weights


def distribute_non_hold_files(remaining_goal, alloc, non_hold_indices, logger):
  print_function_entrance(logger, "7;38;5;34")
  weights = calculate_tempo_weights(non_hold_indices, logger)
  no_frames = [i for i, (_, mark) in enumerate(non_hold_indices) if mark["num_frames"] == 0]
  if no_frames != []:
    logger.debug("no available frames for indices: {}".format(no_frames))
  rounded = correct_rounding_errors(logger, remaining_goal,
                                    [max(1, remaining_goal * weight) for _, weight in weights], catch_zeroes=no_frames)
  for i, (idx, _) in enumerate(weights):
    alloc[idx] = rounded[i]
  return alloc


def redistribute_frames(group, logger):
  print_function_entrance(logger, "7;38;5;36")
  marks = group["marks"]
  first_mark_idx, first_mark = 0, marks[0]
  for idx in range(1, len(marks)):
    mark = marks[idx]
    if mark["timestamp"] != first_mark["timestamp"]:
      first_mark_idx, first_mark = idx, mark
      continue
    if mark["duration"] == 0:
      continue
    old_num_frames = mark["num_frames"]
    if mark["hold"] and not first_mark["hold"] and first_mark_idx != 0:
      logger.debug("Not copying {} out of {} frames from idx {} to {} because it's a hold"
                    .format(mark["num_frames"], old_num_frames, idx, first_mark_idx))
      continue
    updated_duration = mark["duration"]
    if mark["num_frames"] > 1:
      diff = idx - first_mark_idx
      if diff > 1:
        for i in range(idx - 1, first_mark_idx - 1, -1):
          if marks[i]["hold"]:
            first_mark_idx, first_mark = i, marks[i]
      one_frame = round(mark["duration"] / mark["num_frames"], 6)
      updated_duration = first_mark["duration"] = one_frame
      first_mark["num_frames"] = 1
      mark["duration"] = round(mark["duration"] - one_frame, 6)
      mark["num_frames"] -= 1
    else:
      first_mark["duration"] = mark["duration"]
      first_mark["num_frames"] = mark["num_frames"]
      mark["duration"] = mark["num_frames"] = mark["num_files"] = 0
    logger.debug("Copying {} out of {} frames from idx {} to {}"
                  .format(first_mark["num_frames"], old_num_frames, idx, first_mark_idx))
    new_timestamp = round(first_mark["timestamp"] + updated_duration, 6)
    while idx > first_mark_idx and first_mark["timestamp"] == mark["timestamp"]:
      logger.debug("Setting new timestamp for idx {}: {:.03f}".format(idx, new_timestamp))
      mark["timestamp"] = new_timestamp
      idx -= 1
      mark = marks[idx]


def distribute_files_among_marks(group, logger):
  print_function_entrance(logger, "7;38;5;33")
  goal = group["num_files"]
  holds = group["holds"]
  if goal < 1:
    raise RuntimeError("Number of playable files in group is 0: '{}'".format(group["label"]["label"]))
  num_marks = len(group["marks"])
  alloc = [1] + [0] * (num_marks - 1)
  hold_indices, non_hold_indices = [], []
  for i, mark in sorted(enumerate(group["marks"]),
                        key=lambda x: (x[0] == 0, x[1]["duration"], x[1]["timestamp"],
                                       x[1]["timestamp"] - x[1]["raw_timestamp"], x[0]), reverse=True):
    logger.debug("{}: {}".format(i, mark))
    (hold_indices if mark["hold"] else non_hold_indices).append((i, mark))

  logger.debug("Initial goal: {}, num_marks: {}, num_holds: {}{}"
               .format(goal, num_marks, holds, ", hold_indices: {}"
                       .format([i for i, _ in hold_indices]) if holds else ""))
  for i, _ in hold_indices:
    alloc[i] = 1
    if sum(alloc) == goal:
      logger.debug("Reached allocation goal while distributing holds. Allocations: {}".format(alloc))
      return alloc

  # Discount the "for safety" first allocation if it's not a hold
  remaining_goal = goal - (sum(alloc) - int(not group["marks"][0]["hold"]))
  if remaining_goal <= 0:
    raise RuntimeError("Badly miscalculated remaining_goal: {}.\n{}".format(remaining_goal, alloc))
  alloc = distribute_non_hold_files(remaining_goal, alloc, non_hold_indices, logger)
  sum_alloc = sum(alloc)
  if sum_alloc != goal:
    raise RuntimeError("sum(alloc) {} != goal {}".format(sum_alloc, goal))
  logger.debug("Allocations: {} {}".format(alloc, sum_alloc))
  return alloc


def prepare_mark_data(group, files_offsets, logger):
  print_function_entrance(logger, "7;38;5;60")
  marks = group["marks"]
  num_frames_offsets = [mark["num_frames"] for mark in marks]
  num_frames = sum(num_frames_offsets)

  assert num_frames_offsets[0] != 0 or (num_frames_offsets[0] == 0 and num_frames == 0)
  # Reduce the duration scaled offsets by the number of frames available.
  smallest = [min(files_offsets[i], num_frames_offsets[i]) for i, _ in enumerate(marks)]
  sum_smallest = sum(smallest)

  logger.debug("{} {} num_frames".format(num_frames_offsets, num_frames))
  logger.debug("{} {} files_offsets".format(files_offsets, sum(files_offsets)))
  logger.debug("{} {} smallest (playable files or frames)".format(smallest, sum_smallest))
  if sum_smallest < num_frames and sum_smallest < sum(files_offsets):
    logger.debug("Smallest is less than both num frames and files")

  group_num_files = group["num_files"]
  if sum_smallest != group_num_files:
    dropped = group_num_files - sum_smallest
    logger.debug("Dropping {} file{}".format(dropped, "s" if dropped > 1 else ""))

  if sum_smallest > group_num_files:
    raise RuntimeError("allocated more files {} than group_num_files {}".format(sum_smallest, group_num_files))
  return smallest


def compute_segment_slices(group, files_offsets, logger):
  key_files_indices = get_key_file_offsets_from_replay_stack(group, logger)
  logger.debug("{} raw key_files_indices".format(key_files_indices))

  print_function_entrance(logger, "7;38;5;54")
  total_files = sum(files_offsets)
  logger.debug("files_offsets {}: {}".format(total_files, files_offsets))
  total_frames = [m["num_frames"] for m in group["marks"]]
  logger.debug("total_frames: {}".format(total_frames))
  group_num_files = group["num_files"]

  if total_files != group_num_files:
    logger.warning("total_files {} != group_num_files {}".format(total_files, group_num_files))
    group_num_files = total_files

  running_total = 0
  prev_key_pos = 0
  segment_slices = []

  for num_files in files_offsets:
    running_total += num_files
    if running_total not in key_files_indices: # ensure `running_total` is in the list
      bisect.insort_left(key_files_indices, running_total)
    key_pos = key_files_indices.index(running_total)
    slice_ = key_files_indices[prev_key_pos:key_pos + 1]
    if num_files == 0:
      if not slice_[-1] > 0:
        if sum(total_frames) == 0:
          logger.debug("No frames available in group, keep going")
        else:
          raise RuntimeError("Last indice of slice is not > 0: {}".format(slice_))
      else:
        slice_[-1] = running_total - 1
    if slice_ == []:
      raise RuntimeError("Expected non-empty segment slice")
    segment_slices.append(slice_)
    slice_to = key_files_indices[key_pos] - 1
    slice_from = min(slice_to, key_files_indices[prev_key_pos])
    logger.debug("slice {}: {}\tfor segment {}\tslice {}\trunning_total: {}\tnum_files: {}"
                 .format(len(segment_slices), slice_, key_pos,
                         "{} -> {}".format(slice_from, slice_to) if slice_from != slice_to else slice_from,
                         running_total, num_files))
    logger.debug("segment_slices: {}".format(segment_slices))
    prev_key_pos = key_pos
  if running_total != group_num_files:
    raise RuntimeError("running total offset miscalculation! {} != {}".format(running_total, group_num_files))

  logger.debug("{} updated key_files_indices".format(key_files_indices))
  logger.debug("{} segment_slices".format(segment_slices))
  return segment_slices


def update_marks_with_segment_data(group, segment_slices, smallest, logger):
  print_function_entrance(logger, "7;38;5;56")
  for i, mark in enumerate(group["marks"]):
    seg = segment_slices[i]
    num_files = smallest[i]
    if seg[-1] - seg[0] == 0 and seg != [0]:
      key_files_diffs = [0]
      logger.debug("Compensate: using key_files_diffs = {} for mark {}".format(key_files_diffs, i))
    else:
      key_files_diffs = [seg[idx + 1] - seg[idx] for idx in range(len(seg) - 1)]
    # Determine segment_files with rounding correction if applicable.
    if num_files <= 1 or (num_files == key_files_diffs[0] and len(key_files_diffs) == 1):
      segment_files = [num_files]
    else:
      total_diff = sum(key_files_diffs)
      if total_diff == 0:
        segment_files = [0] * len(key_files_diffs)
      else:
        # Scale each diff to contribute to num_files.
        segment_files = correct_rounding_errors(logger, num_files,
                                                [round_up(d * num_files, total_diff) for d in key_files_diffs])
    sum_segment_files = sum(segment_files)
    if sum_segment_files != num_files:
      raise RuntimeError("Rounding correction failed: sum(segment_files) {} != num_files {}"
                         .format(sum_segment_files, num_files))

    logger.debug("key_files_diffs: {} seg: {}\tsegment_files: {}, num_files {}"
                 .format(key_files_diffs, seg, segment_files, num_files))
    mark.update({
      "key_files_offsets": seg,
      "key_files_diffs": key_files_diffs,
      "num_files": num_files,
      "segment_files": segment_files,
    })

  # Final consistency check across all marks.
  group_num_files = sum(smallest)
  total_files = sum(m["num_files"] for m in group["marks"])
  if total_files != group_num_files:
    raise RuntimeError("total_files {} != group_num_files {}".format(total_files, group_num_files))
  return total_files


def append_group_timings(args, logger):
  group, file_idx, timestamp, mark, duration, num_frames= args
  print_function_entrance(logger, "7;38;5;216")
  if file_idx >= group["num_files"]:
    raise RuntimeError("file_idx {} for {} group files".format(file_idx, group["num_files"]))
  new_entry = {
    "file": group["files"][file_idx],
    "timestamp": timestamp,
    "outpoint": round(timestamp + duration, 6),
    "duration": duration,
    "num_frames": num_frames,
    "raw_timestamp": mark["raw_timestamp"],
    "hold": mark["hold"],
  }
  logger.debug(new_entry)
  return new_entry


def handle_file_timing(args, logger):
  print_function_entrance(logger, "7;38;5;79")
  mark, group, file_idx, timestamp, _ = args
  file_idx = mark["key_files_offsets"][0]
  logger.debug("hold? {} num_files {}".format(mark["hold"], mark["num_files"]))
  if file_idx >= group["num_files"]:
    raise RuntimeError("file_idx: {} is outside group num_files: {}".format(file_idx, group["num_files"]))
  duration = mark["duration"]
  group["timings"].append(append_group_timings(
    (group, file_idx, timestamp, mark, mark["duration"], mark["num_frames"]), logger))
  new_timestamp = round(timestamp + duration, 6)
  return file_idx, new_timestamp


def distribute_frames_evenly(num_files, num_frames, kf_offset_idx):
  if num_files <= num_frames:
    file_indices = [i + kf_offset_idx for i in range(num_files)]
    frames_per_file = [round_up((i + 1) * num_frames, num_files) - round_up(i * num_frames, num_files)
                       for i in range(num_files)]
  else:
    frames_per_file = [1] * num_frames
    file_indices = [kf_offset_idx]
    _ = [file_indices.append(file_indices[-1] +
                             (round_up((i + 1) * num_files, num_frames) - round_up(i * num_files, num_frames)))
         for i in range(num_frames - 1)]
  return file_indices, frames_per_file


def distribute_files_among_segments(args, logger):
  print_function_entrance(logger, "7;38;5;77")
  args = {
    "idx": args[0],
    "kf_offset_idx": args[1],
    "num_files_from": args[2],
    "num_frames_to": args[3],
    "total_num_frames": args[4],
    "timestamp": args[5],
    "framerate": args[6],
  }
  idx = args["idx"]
  kf_offset_idx = args["kf_offset_idx"]
  if args["num_frames_to"] == 0:
    logger.debug("Segment {}: By-passing segment with 0 frames_to".format(idx))
    timing_diffs = [0]
    file_indices = [kf_offset_idx]
    return timing_diffs, file_indices
  framerate = args["framerate"]
  running_total = round_up(args["timestamp"] * framerate)
  last_timestamp = args["timestamp"]
  if args["num_frames_to"] == 1:
    logger.debug("Segment {}: Manually setting single frame. kf_offset_idx: {}"
                 .format(idx, kf_offset_idx))
    file_indices = [kf_offset_idx]
    running_total += 1
    this_timestamp = round(running_total / framerate, 6)
    timing_diffs = [round(this_timestamp - last_timestamp, 6)]
    logger.debug("last_timestamp: {:.6f}\tadded frames: {}\trunning_total: {}\t"
                  "added diff:{:.6f}\tthis_timestamp: {:.6f}"
                  .format(last_timestamp, 1, running_total, timing_diffs[-1], this_timestamp))
    return timing_diffs, file_indices

  file_indices, frames_per_file = distribute_frames_evenly(args["num_files_from"], args["num_frames_to"], kf_offset_idx)
  logger.debug("Segment {}: kf_offset_idx: {}, file_indices {}: {}"
                .format(idx, kf_offset_idx, len(file_indices), file_indices))
  logger.debug("Segment {}: num_files_from {} / frames: {} / total_frames {} - frames per file {}"
               .format(idx, args["num_files_from"], args["num_frames_to"], args["total_num_frames"], frames_per_file))
  timing_diffs = []
  for i, frames in enumerate(frames_per_file):
    running_total += frames
    this_timestamp = round(running_total / framerate, 6)
    timing_diffs.append(round(this_timestamp - last_timestamp, 6))
    logger.debug("{}: last_timestamp: {:.6f}\tadded frames: {}\trunning_total: {}\t"
                  "added diff:{:.6f}\tthis_timestamp: {:.6f}"
                  .format(i, last_timestamp, frames, running_total, timing_diffs[-1], this_timestamp))
    last_timestamp = this_timestamp

  if round_up(sum(timing_diffs) * framerate) != sum(frames_per_file) or not timing_diffs:
    msg = "About to run into trouble with timestamp calculations"
    logger.warning(msg)
    raise RuntimeError(msg)
  logger.debug("Segment {}: timing_diffs: len {}, sum {:.6f}, diffs: {}"
              .format(idx, len(timing_diffs), sum(timing_diffs), timing_diffs))
  return timing_diffs, file_indices


def validate_and_update_files(args, logger):
  print_function_entrance(logger, "7;38;5;78")
  group, file_indices, mark, timing_diffs, framerate, segment_idx, timestamp = args
  group_num_files =  group["num_files"]

  expected = round(mark["timestamp"] + mark["duration"], 6)
  idx = file_indices[-1]
  for i, idx in enumerate(file_indices):
    if idx >= group_num_files:
      raise IndexError("idx {} >= group_num_files {}".format(idx, group_num_files))
    duration = timing_diffs[i]
    num_frames = round_up(duration * framerate)
    logger.debug("Segment {}: Setting idx {} with duration {}" .format(segment_idx, idx, duration))
    # logger.debug("i: {} out of {}, duration {} / {}".format(i, len(file_indices) - 1, duration, mark["duration"]))
    group["timings"].append(append_group_timings((group, idx, timestamp, mark, duration, num_frames), logger))
    timestamp = round(timestamp + duration, 6)
    logger.debug("Segment {}: Added duration {} to running_timestamp {:.3f}".format(segment_idx, duration, timestamp))
    if timestamp > expected:
      logger.debug("Segment {}: running_timestamp {} > timestamp + duration {}"
                   .format(segment_idx, timestamp, expected))
      logger.debug("{} - {}"
                   .format(sum(sum(m["segment_files"]) for m in group["marks"]), group_num_files))
      raise RuntimeError("Segment {}: Timestamp overflow - this shouldn't happen!".format(segment_idx))
  logger.debug("Segment {}: Finished validate_and_update_files()".format(segment_idx))
  return idx, timestamp


def handle_segment_distribution(args, logger):
  print_function_entrance(logger, "7;38;5;80")
  args = {
    "mark": args[0],
    "group": args[1],
    "file_idx": args[2],
    "timestamp": args[3],
    "framerate": args[4],
  }

  mark = args["mark"]
  file_idx = args["file_idx"]
  timestamp = args["timestamp"]

  total_num_frames = mark["num_frames"]
  key_files_offsets = mark["key_files_offsets"]
  if total_num_frames == 0:
    logger.warning("Cannot distribute mark with no frames")
    return file_idx, timestamp
  key_files_diffs = mark["key_files_diffs"]
  sum_key_files_diffs = sum(key_files_diffs)

  logger.debug("total num frames: {}, files distribution {}: {}"
               .format(total_num_frames, len(key_files_diffs), key_files_diffs))
  logger.debug("key files offsets: {}, diffs: {}".format(key_files_offsets, key_files_diffs))
  # Correct any under/over allocations of frames to files
  frames_slots = correct_rounding_errors(logger, total_num_frames,
                                         [total_num_frames * files / sum_key_files_diffs for files in key_files_diffs])

  for idx, kf_diff in enumerate(key_files_diffs):
    if idx == 0:
      logger.debug("Segment {}: mark details:\n{}".format(idx, mark))
    timing_diffs, file_indices = distribute_files_among_segments(
      (idx, key_files_offsets[idx], kf_diff, frames_slots[idx],
      total_num_frames, timestamp, args["framerate"]), logger)

    file_idx, timestamp = validate_and_update_files(
      (args["group"], file_indices, mark, timing_diffs, args["framerate"], idx, timestamp), logger)
    logger.debug("Segment {}: completed. Updated timestamp: {:.3f}".format(idx, timestamp))

  return file_idx, timestamp


def validate_timestamp_alignment(running, expected, logger):
  if running != expected:
    msg = "running timestamp {:.06f} != expected timestamp {:.06f}".format(running, expected)
    logger.warning(msg)
    raise RuntimeError(msg)


def build_timings(group, framerate, logger):
  print_function_entrance(logger, "7;38;5;220", group["label"]["label"])
  group["timings"] = []
  redistribute_frames(group, logger)
  files_offsets = distribute_files_among_marks(group, logger)
  smallest = prepare_mark_data(group, files_offsets, logger)
  segment_slices = compute_segment_slices(group, files_offsets, logger)
  update_marks_with_segment_data(group, segment_slices, smallest, logger)

  file_idx = 0
  running_timestamp = group["timestamp_start"]
  logger.debug("group timestamp_start {:.3f} end {:.3f}"
               .format(group["timestamp_start"], group["timestamp_end"]))

  for mark in group["marks"]:
    mark_timestamp = mark["timestamp"]
    validate_timestamp_alignment(running_timestamp, mark_timestamp, logger)
    group["timings"].append({"label": mark["raw_line"], "timestamp": mark_timestamp,
                             "raw_timestamp": mark["raw_timestamp"], "hold": mark["hold"]})
    logger.debug("\nAdded timings: \t{}\n".format(group["timings"][-1]))
    single_or_group_fn = handle_file_timing if mark["hold"] or mark["num_files"] <= 1 else handle_segment_distribution
    file_idx, running_timestamp = single_or_group_fn((mark, group, file_idx, running_timestamp, framerate), logger)

  validate_timestamp_alignment(running_timestamp, group["timestamp_end"], logger)


def handle_multiple_same_timestamps(this_timestamp_files, logger):
  print_function_entrance(logger, "7;38;5;215")
  num_files = len(this_timestamp_files)
  donor_idx, donor = this_timestamp_files[0]
  for i in range(num_files - 1, 0, -1):
    chosen_one_idx, chosen_one = this_timestamp_files[i]
    if donor["hold"] and not chosen_one["hold"]:
      logger.debug("Preventing copying allocation of duration and outpoint "
        "from label[{}] to label[{}] because it's a hold".format(donor_idx, chosen_one_idx))
      break
    if chosen_one["raw_timestamp"] < chosen_one["timestamp"] and not chosen_one["hold"]:
      logger.debug("Skipping non-hold raw_timestamp before timestamp further away than donor: {}: {}"
                    .format(chosen_one_idx, chosen_one))
      break
    logger.debug("Selected a new best match after timestamp")

    one_frame_duration = round(donor["duration"] / donor["num_frames"], 6)
    chosen_one["duration"] = one_frame_duration
    chosen_one["timestamp"] = donor["timestamp"]
    chosen_one["outpoint"] = donor["timestamp"] = round(donor["timestamp"] + one_frame_duration, 6)
    donor["duration"] = round(donor["duration"] - one_frame_duration, 6)
    chosen_one["num_frames"] = 1
    logger.debug("Updating duration and outpoint by {:.03f} from label[{}] to label[{}]:\n{}"
                 .format(one_frame_duration, donor_idx, chosen_one_idx, chosen_one))
    this_timestamp_files.remove((chosen_one_idx, chosen_one))
    donor["num_frames"] -= 1
    if donor["num_frames"] <= 1:
      break
    logger.debug("Marked chosen_idx {}, on the hunt for more".format(chosen_one_idx))
  if donor["num_frames"]:
    logger.debug("Keeping the donor: {}:\n{}".format(donor_idx, donor))
    this_timestamp_files.remove((donor_idx, donor))
  return this_timestamp_files


def correct_duplicate_mark_timestamps(timings, first_timestamp, logger):
  print_function_entrance(logger, "7;38;5;210")
  last_idx = idx = len(timings) - 1
  while idx >= 0 and timings[idx]["timestamp"] >= first_timestamp:
    idx -= 1
  idx += 1
  if idx >= last_idx:
    return timings
  output_timings = timings[:idx]
  while idx <= last_idx:
    this_timestamp = timings[idx]["timestamp"]
    # logger.debug("refreshing this_timestamp: {}".format(this_timestamp))
    this_timestamp_labels = []
    while idx <= last_idx and timings[idx]["timestamp"] <= this_timestamp:
      if this_timestamp != timings[idx]["timestamp"]:
        raise RuntimeError("timings timestamp order is corrupted")
      this_timestamp_labels.append((idx, timings[idx]))
      idx += 1
    # logger.debug("setting idx to {} with last_idx {}".format(idx, last_idx))
    this_timestamp_files = sorted(((i, t) for i, t in this_timestamp_labels if "file" in t), key=lambda x: (
      -x[1]["duration"], x[1]["hold"], x[1]["raw_timestamp"] > x[1]["timestamp"], -x[1]["raw_timestamp"],
      abs(x[1]["timestamp"] - x[1]["raw_timestamp"])))
    num_files = len(this_timestamp_files)
    if num_files:
      duration = this_timestamp_files[0][1].get("duration", 0)
      # duration = sum(t["duration"] for _, t in this_timestamp_files[0]["duration"])
      # logger.debug("this_timestamp {:.06f} has {:.06f} duration with {} files"
      #              .format(this_timestamp, duration, num_files))
      # if duration == 0:
      #   logger.debug("save for next round")
      if duration != 0 and num_files > 1:
        for i, t in sorted(handle_multiple_same_timestamps(this_timestamp_files, logger), key=lambda x: -x[0]):
          logger.debug("Removing label[{}]:\n{}".format(i, t))
          this_timestamp_labels.remove((i, t))
    output_timings.extend(t for _, t in this_timestamp_labels)
  return output_timings


def insert_items_into_timings(timings, items, logger):
  print_function_entrance(logger, "7;38;5;230")
  first_item = items[0]
  last_idx = idx = len(timings) - 1
  while idx >= 0 and timings[idx]["timestamp"] > first_item["raw_timestamp"]:
    idx -= 1
  if idx == last_idx:
    merged = timings + items
  else:
    idx += 1
    merged = timings[:idx]
    last_timing_ts = timings[idx]["timestamp"]
    for item in items:
      while idx <= last_idx and item["timestamp"] > last_timing_ts:
        merged.append(timings[idx])
        idx += 1
        if idx > last_idx:
          break
        last_timing_ts = timings[idx]["timestamp"]
      merged.append(item)
    merged.extend(timings[idx:])
  return correct_duplicate_mark_timestamps(merged, first_item["timestamp"], logger)
