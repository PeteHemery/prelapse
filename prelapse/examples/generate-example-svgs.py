#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# examples/generate-example-svgs.py

import argparse
import os
import prelapse
import sys

# FYI this example makes use of PIL to estimate text bounding box size.
# If you get an error make sure you run "pip install pillow"
from PIL import ImageFont

sys.dont_write_bytecode = True


def measure_text(text, font_size, font_name):
  """
  Measure the rendered text size using Pillow.
  If font_name is provided, that TrueType font is used;
  otherwise, Pillow's default font is used.
  Returns a tuple (width, height).
  """
  # print(font_name)
  font = ImageFont.truetype(font_name.replace(' ', '_'), font_size)
  bbox = font.getbbox(text)
  text_width = bbox[2] - bbox[0]
  text_height = bbox[3] - bbox[1]
  return text_width, text_height


def generate_svg(frame_index, total_frames, width, height, text, padding_x, padding_y, font_size,
                 font_name, font_type, font_color):
  text_width, text_height = measure_text(text, font_size, font_name)

  safe_width = (width - padding_x - int(text_width * 5 / 6)) - padding_x
  safe_height = (height - padding_y - int(text_height * 4 / 3)) - padding_y

  # When there's only one frame, simply position the text at the starting position.
  if total_frames > 1:
    x_increment = safe_width / (total_frames - 1)
    y_increment = safe_height / (total_frames - 1)
  else:
    x_increment = 0
    y_increment = 0

  pos_x = int(padding_x + frame_index * x_increment)
  pos_y = int(text_height + padding_y + frame_index * y_increment)
  # print(f"x_increment {x_increment} y_increment {y_increment}")
  # print(f"pos_x {pos_x} pos_y {pos_y}")

  # SVG content with the text element.
  svg_content = f'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg width="{width}" height="{height}" version="1.1" xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="black" />
  <text x="{pos_x}" y="{pos_y}"
        font-family="{font_name}, {font_type}"
        font-size="{font_size}"
        font-style="italic"
        fill="{font_color}"
        dominant-baseline="hanging"
        {'text-decoration="underline"' if frame_index % 2 else 'font-weight="bold"'}
  >
    {text}
  </text>
</svg>
'''
  return svg_content


def remove_example_relics(examples_directory):
  for filename in sorted(os.listdir(examples_directory)):
    if filename.endswith(".svg") or filename.startswith("prelapse_config.md") or filename in ["labels.txt", "prelapse.ffconcat"]:
      file_path = os.path.join(examples_directory, filename)
      os.remove(file_path)
      print(f"Deleted file: {filename}")


def example_main():
  parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
    description="Generate a sequence of SVG images with progressively offset text.")
  parser.add_argument("-f", "--frames", type=int, default=10,
    help="Number of frames to generate.\n Default: %(default)s")
  parser.add_argument("-W", "--width", type=int, default=800,
    help="Width of each SVG image in pixels.\n Default: %(default)s")
  parser.add_argument("-H", "--height", type=int, default=600,
    help="Height of each SVG image in pixels.\n Default: %(default)s")
  parser.add_argument("-t", "--text", type=str, default="Prelapse Test Frame {i}",
    help="Base text to display with frame number. where {i} is the frame number starting from 1.\n Default: '%(default)s'")
  parser.add_argument("-x", type=float, default=15,
    help="X padding in pixels.\n Default: %(default)s")
  parser.add_argument("-y", type=float, default=15,
    help="Y padding in pixels.\n Default: %(default)s")
  parser.add_argument("-s", "--font-size", type=int, default=48,
    help="Font size for the text.\n Default: %(default)s")
  parser.add_argument("-n", "--font-name", type=str,  default="Courier New Bold",
    help="Name of the primary font to use (e.g. 'Arial', 'Times New Roman', 'Courier New Bold').\n Default: '%(default)s'")
  parser.add_argument("-T", "--font-type", type=str, choices=["serif", "sans-serif"], default="serif",
    help="Type of font to use. 'serif' fonts have small decorative strokes (e.g. Times New Roman), "
         "while 'sans-serif' fonts do not (e.g. Arial).\n Default: %(default)s")
  parser.add_argument("-c", "--font-color", type=str, default="teal",
    help="Font color for the text.\n Default: %(default)s")
  parser.add_argument("-d", "--duration", type=float, default=2.0,
    help="Number of seconds to display frames in play example.\n Default: %(default)s")
  prelapse.set_prelapse_epilog(parser)

  args = parser.parse_args()

  examples_directory = os.path.realpath(os.path.dirname(__file__))
  remove_example_relics(examples_directory)
  for i in range(1, args.frames + 1):
    svg_data = generate_svg(
      frame_index=i-1,
      total_frames=args.frames,
      width=args.width,
      height=args.height,
      text=args.text.format(i=i),
      padding_x=args.x,
      padding_y=args.y,
      font_size=args.font_size,
      font_name=args.font_name,
      font_type=args.font_type,
      font_color=args.font_color
    )
    filename = os.path.realpath(os.path.join(examples_directory, f"frame_{i:03d}.svg"))
    with open(filename, "w", encoding="utf-8") as f:
      f.write(svg_data)
    print(f"Generated {filename}")

  config_file = os.path.realpath(os.path.join(examples_directory, "prelapse_config.md"))
  labels_file = os.path.realpath(os.path.join(examples_directory, "labels.txt"))
  concat_file = os.path.realpath(os.path.join(examples_directory, "prelapse.ffconcat"))

  prelapse.prelapse_main(f"gen -i {examples_directory} -l {labels_file} -lt {args.frames/args.duration}".split())
  prelapse.prelapse_main(f"play -c {config_file} -l {labels_file} -f {concat_file}".split())

  remove_example_relics(examples_directory)

if __name__ == "__main__":
  example_main()
