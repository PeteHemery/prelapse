# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# runner/lapse_runner.py

from __future__ import print_function, division

import os

from .argument_parser import _add_parser_args, _parse_args
from .label_processor import process_labels
from ..common import build_ff_cmd, call_shell_command, format_float, gen_list_file, write_list_file, \
  shell_safe_path


class LapseRunner: # pylint: disable=no-member
  """ Main parser class """

  add_parser_args = staticmethod(_add_parser_args)
  parse_args = classmethod(_parse_args)

  def parse_labels_and_config(self):
    """
    Convert Audacity labels file to ffmpeg ffconcat image sequence using info from Markdown config file.
    """
    with open(self.labels, "r", encoding="utf-8") as f:
      content = f.readlines()

    # Sanity checks
    if len(content) < 2:
      raise RuntimeError("Must have 2 or more labels present in file, marking start and end")
    if float(content[0].split("\t")[0]) != 0.0:
      raise RuntimeError("First label must start at 0.0")
    if content[-1].split("\t")[-1].strip() != "end":
      raise RuntimeError("Last label must be 'end'")
    files = process_labels((content, self.fps, self.config, self.delimiter, self.jump), self.logger)

    return gen_list_file(files, self.fps, self.jump)

  def run_parser(self, args, run=False, out=False):
    self.parse_args(args, run=run, out=out)

    output = self.parse_labels_and_config()
    write_list_file(self.ffconcatfile, output, self.dry_run, fd=self.ffconcatfile_fd)
    self.logger.info(self.ffconcatfile)
    if not (run or out):
      self.logger.warning("Parsed only")
      return []

    filter_complex = self.build_filter_complex()

    out_args = (self.overwrite, self.fps, self.codec, self.crf, self.audiofile, self.outpath) if out else None
    runcmd = build_ff_cmd(self.ffloglevel, self.verbose, filter_complex, out_args)
    if out:
      runcmd.append(self.outpath)
    return runcmd

  def run_prelapse(self, args, run=False, out=False):
    runcmd = self.run_parser(args, run=run, out=out)
    try:
      shell_ret = call_shell_command(runcmd, dry_run=args.dry_run)
      if shell_ret:
        print("Shell command failed with return code: {}".format(shell_ret))
        return
    finally:
      # Tidy up tempfile, if used
      if hasattr(self, "ffconcatfile_fd"):
        if self.ffconcatfile_fd is not None:
          os.remove(self.ffconcatfile)
    if out:
      print("Written '{}'".format(self.outpath)) # pylint: disable=no-member

  def build_filter_complex(self):
    # Build various parts of the filter_complex command,
    # then combine them in order

    # Build the setpts string, using a format placeholder for parameters.
    setpts = "setpts={{}}PTS-STARTPTS{}".format(
      "+({}/TB)".format(format_float(self.jump / self.tempo)) if self.jump else "")
    filter_complex = self.build_video_filter(setpts)
    if self.audiofile is not None:
      filter_complex += self.build_audio_filter(setpts)

    return filter_complex

  def build_video_filter(self, setpts):
    # Construct the movie input part with filter string.
    cmd = "movie={}:f=ffconcat:si=0:format_opts='".format(shell_safe_path(self.ffconcatfile))
    cmd += "safe=0\\:auto_convert=0"
    if self.metadata_string:
      cmd += "\\:segment_time_metadata=1"
    cmd += "',settb=1/{}".format(format_float(self.fps, 3))
    cmd += ",fps={}".format(format_float(self.fps, 3))
    # Previously experimented options:
    # cmd += ":start_time={:0.3f}".format(self.jump)
    cmd += ":round=inf"
    cmd += ":eof_action=pass"
    # cmd += ":start_time={:0.3f}".format(self.jump)
    # cmd += ",setpts=N/FR/TB"
    # cmd += ",setpts={}-STARTPTS".format("{:0.3f}*PTS".format(1.0 / self.tempo) if self.tempo != 1 else "PTS")
    # Set the PTS filter with possible tempo adjustment.
    cmd += ",{}".format(setpts.format(
      "{}*".format(format_float(1.0 / self.tempo)) if self.tempo != 1.0 else ""))
    # Build scaling and padding based on whether histogram and audiofile are set
    if self.histogram and self.audiofile:
      new_height = int(self.height * 2 / 3) + int(self.height * 2 / 3) % 2
      cmd += ",scale={}:{}:flags=lanczos:force_original_aspect_ratio=decrease:eval=frame".format(
        self.width, new_height)
      cmd += ",pad=w={}:h={}:x=-1:y=-1:color=black:eval=frame".format(
        self.width, new_height)
      cmd += ",setdar={}/{}".format(self.width, new_height)
    else:
      cmd += ",scale={}:{}:flags=lanczos:force_original_aspect_ratio=decrease:eval=frame".format(
        self.width, self.height)
      cmd += ",pad=w={}:h={}:x=-1:y=-1:color=black:eval=frame".format(
        self.width, self.height)
      cmd += ",setdar={}/{}".format(self.width, self.height)

    # Add metadata overlay if available
    if self.metadata_string:  # and False:
      cmd += ",select=concatdec_select,metadata=delete:UserComment"
      cmd += ",drawtext=fontsize=16:fontcolor=white:fontfile=FreeSans.ttf:text='"
      for l in ["pts", "steps", "seed", "guidance", "timestamp", "which"]:
        cmd += "{0}\\: %{{metadata\\:{0}}}\n".format(l)
      for l in ["filename", "prompt", "neg_prompt", "prompt2", "neg_prompt2"]:
        cmd += "\n"
        for i in range(6):
          cmd += "{0}_{1}\\: %{{metadata\\:{0}_{1}}}\n".format(l, i)
      cmd += "':x=10:y=10"

    cmd += ",format=yuv420p"
    # Previous filter experiments:
    # cmd += ",format=rgb24"
    # cmd += ",vectorscope"
    # cmd += ",zmq"
    # cmd += ",edgedetect=mode=colormix"
    # cmd += ",fade=in:0:100"

    # Choose output label based on whether histogram and audio file exist.
    if self.histogram and self.audiofile:
      cmd += "[vid]"
    else:
      cmd += "[out0]"

    return cmd

  def build_audio_filter(self, setpts):
    # Build audio filter chain based on parameters such as jump, tempo, etc.
    cmd = ";amovie={}".format(shell_safe_path(self.audiofile))
    # Uncomment one of the following if needed for experimenting with the audio start time
    # cmd += ",aselect=gt(t\,{})".format(self.jump)
    if self.jump > 0:
      cmd += ",atrim=start={}".format(format_float(self.jump, 3))
    if self.tempo != 1:
      if self.tempo > 2:
        cmd += ",atempo=sqrt({0}),atempo=sqrt({0})".format(self.tempo)
      else:
        cmd += ",atempo={}".format(self.tempo)
    # Previous experiment: adjust audio pts with asetpts
    # cmd += ",asetpts=PTS-STARTPTS{}".format("+({:0.3f}/TB)".format(self.jump / self.tempo) if self.jump else "")
    cmd += ",a{}".format(setpts.format(""))
    # More commented experiments for audio:
    # cmd += ",asetpts=({}PTS{})-STARTPTS".format(
    #   "{:0.4f}*".format(self.tempo) if self.tempo != 1 else "",
    #   "+({:0.3f}/TB)".format(self.jump / self.tempo) if self.jump else "")
    # cmd += ",asetpts=PTS-STARTPTS+{}/TB".format(self.jump / self.tempo)
    # cmd += ",asetpts={}*PTS-STARTPTS+{}/TB".format(self.tempo, self.jump / self.tempo)

    # If histogram is enabled, split the audio for a spectrum/CQT overlay example.
    if self.histogram:
      cmd += ",asplit=2[out1][b];"
      # Previous experiment:
      # cmd += ",asplit=3[out1][a][b];"
      # cmd += "[a]showspectrum=s={}x{}:".format(200, self.height)
      # cmd += "orientation=horizontal:color=fire:scale=log:overlap=1[spectrum];"
      cmd += "[b]showcqt=s={}x{}:fps={}[cqt];".format(
        round(self.width), int(self.height / 3), format_float(self.fps, 3))
      cmd += "[vid][cqt]"
      cmd += "vstack"
      cmd += ",setdar={}/{}".format(self.width, self.height)
      # Previous experiment:
      # cmd += "[vid0];[vid0]"
      cmd += "[out0]"
      # More experiments:
      # cmd += "[spectrum][vid]hstack[vidtop];"
      # cmd += "[vidtop][cqt]vstack[out0]"
    else:
      cmd += "[out1]"

    return cmd
