# prelapse - Pete's Reasonably Educational Lapse Animation Python Script Experiment

## Text File Based Image Sequence Music Video Generator
🖳 🎶 ⏆ 🏷️ 🖹 🤳 🏞️ 🌇 🌃 🖹 ⏩ ⏳ 🎞 📽️ 🤓

-----

Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved

This file is part of prelapse which is released under the AGPL-3.0 License.
See the LICENSE file for full license details.

-----

### What is it?
<details>
<summary>What is it?</summary>

`prelapse` is a text based Python toolbox to help with the creation of image sequence based music videos, such as stop-motion animation, claymation, CG renders, time-lapses, hyper-lapses, slide-shows...

It is essentially a wrapper that formats groups of images into `ffconcat` file format to be used with `ffmpeg`/`ffplay` to quickly define the desired duration between images. It builds the command pipeline for the user and runs it, allowing near instant video creation/preview.

Groups of images are define in a custom markdown format. Using Audacity to position specific `prelapse syntax` comments at timestamps, it's possible to define which groups start at what time, and specify different effects within the duration of a group.

Explanations/tutorials are below/to come.
</details>

### What's in a name?
<details>
<summary>What in a name?</summary>

Since its goal is to create *lapse type videos, using the script involves some preparation, usually falling into the loop of "Prepare, Run/Refine, Enjoy". The name `prelapse` seemed to scratch my itch for puns, describe the software's function to my satisfaction, and the acronym above is just a bit of fun.
</details>

### Why did I make it?
<details>
<summary>Why did I make it?</summary>

**_Think hard and build things_** over **_Move fast and break things_**

This "non-linear text based video editor" was created because of the time consuming frustration experienced when manually stitching together image sequences ***and then*** trying to sync to audio, causing dropped or duplicated frames.

I've been a user of Free and Open Source Software (FOSS) for many years, and am a great believer in its principles. I'm a professional software developer, with a passion project, and have had the privilege of some time to put into making this software, and would feel satisfaction if others get to use it to fuel their creativity and passions.
</details>

### Who's it for?
<details>
<summary>Who's it for?</summary>

Anyone who enjoys animation, has a computer and a bit of creative vision.

Learning how to make things, for the joy of learning, and seeing the result of what you've made as a tangible thing is quite special. I hope this software will act as inspiration for others to engage in learning for the sake of growing, putting aside, at least for a while, the seductive greed for money. Can highly recommend listening to some Ren for that (#RenMakesMusic).
</details>

### Why's it different?
<details>
<summary>Why's it different?</summary>

The key insight, which I have not seen elsewhere, is to flip the order of things, so instead of squeezing/stretching video frames, write labels at timestamps in the audio to define when a group of images should begin and end, with optional effects, and let the script work out the timing for each image.

It uses:
- a config file in markdown format to specify multiple groups of files under names.
- a labels file in `Audacity` label format for marking specific moments in the audio track.

The labels can specify groups or sub-components of a group, along with instructions for that group (repeat, reverse, boomerang) which can be chained together to produce different effects using the pipe `|` symbol.

The labels can also specify marks within a group, with instructions such as tempo changes, hold/pause on a given frame, release the hold, or just alignment for the timing of the images within the groups.

Parsing these instruction labels together with the markdown config and then constructing a `ffconcat` file used to generate the final video output with `ffmpeg` or `ffplay`.

The project contains several modules that interact to process image groups, modify them based on commands, which makes use of `mogrify` from `ImageMagick`.
</details>

-----

## Installation
<details open>
<summary>Installation</summary>

You can install the latest release of this library from pypi using pip by running:

```bash
pip install prelapse
```

-----

</details>

<details>
<summary>Make changes with your own copy of the code (YAY Open Source)</summary>

To download your own version locally and run changes:

```bash
git clone https://www.github.com/PeteHemery/prelapse
cd prelapse
python -m prelapse -h
```

To install a custom version using `pip`, I've been using this **on Linux**, changing the `0.0.0` version number as needed to be higher than the current release:

```bash
export SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0
python -m build --no-isolation --verbose
pip install dist/prelapse-0.0.0-py3-none-any.whl --force-reinstall
```

</details>

### Prerequisites

This package is 100% python, with no dependencies on other libraries. Only calling external programs, e.g. `ffmpeg`.

Follow the installation instructions for your operating system from the official FFmpeg website.
`prelapse` expects to be able to find them from the `PATH` environment variable.

**_NOTE:_** The example in the source code does require `ImageMagick` to be installed, and makes use of the `pillow` python library.

<details>
<summary>Prerequisites</summary>

1. Python 2.7+ or Python 3+
2. `ffmpeg` and `ffplay` for video encoding and playback
3. (Recommended) `Audacity` for editing audio and making timestamp labels.
4. (Optional) `ImageMagick` for bulk image manipulation (resize, rotate, etc).
</details>

## Features
<details>
<summary>prelapse features</summary>

- **Audio-Visual Sync**: Sync image sequences to an audio track using `Audacity` to generate labels.
- **CLI Interface**: A command-line interface (CLI) to control the flow of operations, from generating image descriptions for processing, to previewing and encoding video output.
- **Bash Completion**: Using bash, tab completion is implemented.
- **Video Output**: Create video outputs (e.g. MP4 encoded with H264 or H265 encoding, smaller files suitable for sharing over social media or HD quality larger files), optionally with audio, and preview them instantly with `ffplay`.
- **Image Group Handling**: Import, organise, and modify image groups based on directories and metadata in easy to read/write markdown format.
- **Flexible Modifications**: Supports a variety of image modifications (using ImageMagick's `mogrify` tool), including resize, scale, rotate, crop, colour adjustment, and using `ffmpeg` `vidstab` filter for jerky footage stabilisation.
</details>

## Usage

<details open>
<summary>Overview of using prelapse</summary>

`prelapse` operates via the command line and provides several sub-commands for different tasks.
Each sub-command has its own help section, so feel free to use `-h` whenever you need help about options currently available.

### Command Syntax

```bash
prelapse [subcommand] [options]
```

To get started, it's recommended to explore the `-h/--help` options.

### Sub-commands
<details>
<summary>More info on prelapse sub-commands</summary>

#### `gen` - Generate Configuration
<details>
<summary>Generate markdown format config file to describe file locations of groups of images</summary>

Generates a markdown (.md) configuration file by scanning a directory, (the `-i`/`--inpath` which is the current directory by default) and sub-directories, for images.

Each directory containing images will be added as a group within the config file, with the relative path of the directory as a group name.

If there are pictures in multiple depths of sub-directories (i.e. folders in folders) then you can adjust the depth of the search using the `-d`/`--depth` parameter.

A value of `--depth 1` will exclude the sub-directories, and only pick up images in the current directory.

This example will search the current working directory, and all sub-directories below the current working directory.

```bash
prelapse gen --depth 2
```

To sort the images by time order instead of alphabetical order, use the `-t`/`--time` parameter.
The final product is a file called `prelapse_config.md` by default (modifiable with `-o`/`--outpath`) in the `inpath` directory.

It's possible to add a dummy labels file when generating the config using `-l`/`--labels` and optionally specifying a name. You can set the Frames-Per-Second (FPS) value using `-lt`/`--labels-time`to have control over the rate of displaying images. All images will receive this FPS. So 1 will show a single picture per seconds, and the default 5 will show each image for 0.2, or 1/5, seconds.

So a quick way to review holiday snaps with half a second for each image might be:

```bash
prelapse gen -t -l -lt 2
prelapse play
```

You can use this as a starting point for importing labels in `Audacity` and then moving or adding `prelapse` specific comments at desired timestamps to synchronise groups to audio. Then export the label for use by `prelapse`. `labels.txt` is the default.

</details>

#### `info` - Show Information

Display metadata about the image groups, such as the number of files and their offsets.

```bash
prelapse info --allgroups --details
```

#### `mod` - Modify Images or Groups

Modify image properties such as resize, crop, rotate, etc.

```bash
prelapse mod image resize --group groupA --max 800 --inplace
```
  - **_NOTE:_** There are mutually exclusive options for `--inplace` or `--outmod` to determine if the existing files are overwritten or a new directory is created for the modified files.

#### `play` - Preview Output

**_See more info on how to use the runner below._**

Preview the generated image sequence with `ffplay`.

```bash
prelapse play --audio audio.m4a
```

#### `enc` - Encode Output to Video

**_See more info on how to use the runner below._**

Create a high quality x264 MP4 video from the image sequence using ffmpeg.

```bash
prelapse enc -a audio.m4a --outpath output.mp4
```

Create a smaller, lower quality video with portrait aspect ratio, suitable for quickly sharing over social media.
Setting the width in pixels, the aspect ratio, the codec parameters.

- **_NOTE:_** Width `-w` and Aspect Ratio `-x` are the only controls exposed for scaling.

```bash
prelapse enc -a audio.m4a -w 720 -x 9/16 -C social -o social_output.mp4
```

</details>

### Runner Cheat-Sheet
<details>
<summary>prelapse Runner aka play/enc cheat-sheet</summary>

There are some useful features that `prelapse` allows when trying to work with specific sections of a project.

Since `ffplay` doesn't allow movement in the timeline as it render the video, it's possible to jump to a specific second by using `-j`/`--jump`. This allows "skipping ahead" to a section you're working on if you need to tweak specifics and just want to inspect that bit.

Since some of us have low attention spans, you can adjust the tempo to be faster or slower by using `-t`/`--tempo`, where a value of 2 is double speed.

To get a deep look at what `prelapse` is doing under the hood with calculating timestamps and parsing files, the `-v`/`-verbose` flag will probably givve you too much info.

If you want more info from the underlying `ffmpeg` process, you can adjust its loglevel settings with `-V`/`--ffloglevel`, check the `-h` for the options available.

A fun filter combo is the `-H`/`--histogram` feature, which stacks a visual representation of the audio under the current `prelapse` project.

There are some left over filter experiments in `runner/lapse_runner.py`, have a look at the `ffmpeg-filters` documentation for inspiration. You are encouraged to explore and play.

</details>

</details>

## Structure
<details>
<summary>High level structure of the library layout</summary>

The project is organised into several key modules:

-----

- **`common`**: Contains utility functions and shared components, such as logging, shell interactions and configuration handling.
- **`config`**: Handles the loading, parsing and saving of markdown files specifying groups of images.
- **`genconfig`**: Handles the generating the markdown config file.
- **`info`**: Displays information about the groups and their contents.
- **`modifier`**: Contains logic for modifying image groups (resize, crop, rotate, etc.) using `mogrify`, groups themselves (new, delete, rename) and the number of timestamp columns in the audio labels file (`Audacity` saves two columns, start and end times, but only one is required, and `Audacity` reads it when it's only one).
- **`runner`**: Handles parsing `Audacity` labels, group configuration markdown, and generating file timing calculations. Manages the execution of commands and interactions with `ffmpeg` and `ffplay`.

-----

- **`completions`**: Completions scripts for shells, such as `bash`.
- **`examples`**: Helper scripts that show example usage of the tools.
- **`tests`**: `pytest` suite of tests for functional integrity.

-----

</details>

## Markdown Config Syntax

<details>
<summary>Information about custom markdown syntax</summary>

- Group names begin with the `#` symbol.
- Full paths to single files within a group start with `- {full path}` on a new line. Optionally with a trailing slash to indicate it's a directory.
- Multiple files under a directory can be addressed by specifying the directory `- {directory path}` on a new line, then file names with `  - {file name}` on subsequent lines.

**_NOTE:_** Whitespace at the beginning of lines is important. Lines starting with `-` should be a directory or absolute file path. Lines starting with `  -`, with whitespace before the `-`, are treated as relative file paths to the directory specified above it.

Here is an example that demonstrates the various ways to format paths to images within `prelapse` markdown config groups.

### Examples

<details>
<summary>Linux/MacOS example</summary>

```markdown
<!-- comment -->
# Vacation Photos
- /images/vacation/day1/
  - beach.jpg
  - sunset.jpg
- /images/vacation/other/cityscape.jpg
- /images/vacation/day2
  - hiking.jpg
  - campfire.jpg
- /images/vacation/other/wildlife.jpg

# Group Name 1
- /absolute/path/to/images/
  - image1.jpg
  - image2.jpg

# Group Name 2
- /absolute/path/to/one/image3.jpg
- /absolute/path/to/two/image4.jpg
```

</details>

<details>
<summary>Windows example</summary>

```markdown
<!-- comment -->
# Vacation Photos
- C:\images\vacation\day1\
  - beach.jpg
  - sunset.jpg
- C:\images\vacation\other\cityscape.jpg
- C:\images\vacation\day2
  - hiking.jpg
  - campfire.jpg
- C:\images\vacation\other\wildlife.jpg

# Group Name 1
- C:\absolute\path\to\images\
  - image1.jpg
  - image2.jpg

# Group Name 2
- C:\absolute\path\to\one\image3.jpg
- C:\absolute\path\to\two\image4.jpg
```

</details>

</details>

## Audacity Label Syntax
<details>
<summary>Information about writing labels</summary>

Labels in the `Audacity` format are tab `\t` separated.
The first column as a timestamp in labels, with 6 decimal points of precision. Usually there is a second column too, to indicate a start and end time for a timestamp segment.
We are using timestamps as points, so both columns should be the same number, or one column can be removed (see `prelapse mod labels -h).
The last column will contain the labels that instruct `prelapse` what to do.

The `prelapse` labels have a particular order during processing. They are split into:
- Group Instructions
- Mark Instructions
- Comments

Comments begin with the `#` symbol.
Instructions can be chained together by the `|` symbol to create different effects.

Here is the table of available Group and Mark instructions:

| Group Instructions | Explanation                                                                            |
| ------------------ | -------------------------------------------------------------------------------------- |
| *Group Name*       | One of the names of the groups in the markdown config file                             |
| tempo (*n*)        | Set the initial tempo for the group, with expectation that a mark will change it later |
| hold               | Start with the first image in the group being paused until released by a mark          |
| rep (*n*)          | Repeat all previous instructions ** *n* ** number of times                             |
| rev                | Reverse the order of the files in the group                                            |
| boom               | Instruct the group to play forwards then backwards                                     |
| end                | The required final label to indicate where audio stops                                 |

| Mark Instructions | Explanation                                                                         |
| ----------------- | ----------------------------------------------------------------------------------- |
| tempo (*n*)       | Set the tempo from this mark onwards                                                |
| hold              | Pause on the current image within the group until released by another mark label    |
| mark              | Release a previous hold, or set for aligning group images to certain points in time |

NOTE: `tempo` is a multiplier of 1. So for half speed, set `tempo 0.5` and for double speed to `tempo 2`.

### Examples
<details>
<summary>prelapse Label Examples</summary>

Here's the labels file that gets produced when running `examples/generate-example-images-and-play.py`

**_NOTE:_** The example does rely on an external tool `convert` from `ImageMagick` and the `pillow` python library to calculate the size of the bounding box for the text, so be sure to run `pip install pillow` and install `ImageMagick` if the example fails.

When you have run the example you can see and modify the `labels.txt` file.

```text
0.000000	examples
2.000000	end
```

This will display all the items in the `examples` group over the course of 2 seconds.
You can chain some of the instructions above and experiment with the resulting output. This example first reverses the items in the group, then boomerangs them, and finally repeats the whole sequence twice.

```text
0.000000	examples|rev|boom|rep 2
2.000000	end
```

In this example, the first second will play files from the group at half speed relative to the files in the second half.

```text
0.000000	examples|tempo 0.5
1.000000	tempo 1
2.000000	end
```

Here's another way of achieving the same thing:

```text
0.000000	examples
1.000000	tempo 2
2.000000	end
```

Sub-sections of groups can be specified using the python index or slice syntax. Here we take the first 5 images for the first second, then the rest of the images, from 5 to the end of the group, for the next second, and apply some effects to it

```text
0.000000	examples[:5]
1.000000	examples[5:]|boom|rep3
2.000000	end
```
</details>

</details>

## Contributing
<details>
<summary>Ways to contribute</summary>

Contributions to improve prelapse are welcomed. The spirit of this project is to encourage learning, so feel free to dig into the code yourself and see what you can figure out if you have a problem, or would like to add a feature.

**_NOTE:_** I hear that Open Source authors can burn out and become disillusioned when confronted with entitled users who demand fixes and features. HAVE A GO YOURSELF FIRST!

Here's how you can contribute:

- Fork the repository.
- Clone your fork to your local machine.
- Create a new branch (`git checkout -b feature/your-feature-name`).
- Push your changes to your fork (`git push origin feature/your-feature-name`).
- Create a pull request.

Maybe you can get start by helping to write a test?

**_NOTE:_** AI generated/spammy posts and pull requests will be deleted. Please help me know that a human is learning from this when offering to contribute.

-----

</details>

<details>
<summary>Coding Style Guide</summary>

Please ensure that your code follows the style guide indicated in the `pylintrc` file. Run `pylint .` in the `prelapse` directory to make sure your code smells clean before issuing a pull request.

- 120 characters per line max.
- Two space indentation.
- The Art of Writing Readable Code: functions and variable names should be long enough to be self descriptive, and not too long to bloat.
- Class names should be in `CamelCase`.
- Function, variable and file names should be in `snake_case`.
- Try to fit as much on a single line as possible.
- When splitting lines try to minimize preceeding whitespace on the following line, or align it to where it makes sense for readability.
- Strings use double quotes for preference. Single characters should be surrounded by single quotes.
- Strings with variables use the form `"Variable value: {}".format(the_variable)`. This maintains older python version compatibility.
- When splitting a string containing variables to be multi-line, try to fit the variable string on one line and start the new line with `.format(`, where possible.
- Functions should have two new lines between them at the top level file scope, and one new line within class scope.
- Functions in public interface files that aren't intended to be exposed should be prefixed with underscore, e.g. `def _print_choices(choices):`.
- When passing more than 5 args to a function, wrap them in brackets as a tuple, pass as `args` variable, and unpack them inside the receiving function.
- Giving thoughtful names as you build them, so that others (and later versions of yourself) can see what you're doing, that is the best form of documentation.
- Keep pointless comments to a minimum, only used when necessary.

-----

</details>

<details open>
<summary>Hat on the ground</summary>

### How you can give support

Support can be given by:
1. Engaging me for creative projects, custom development or support contracts.
2. Showcasing credited content created with this library.
3. Contributing back to the project with bug fixes or new features.
4. Financial contributions (see GitHub Sponsors page).

Your support helps ensure the long-term sustainability and improvement of this
project.

For more information on how you can donate please visit: https://github.com/sponsors/PeteHemery or if that still isn't working https://github.com/sponsors/MemoryLapse404

Thanks for using `prelapse`! Go and be creative! Share what you learn!

-----

### Additional Note for Commercial Users:

While this software is released under an Open Source License and is free to use for
any purpose, including commercial applications, a kind reminder that
the copyright holder, license and a copy of the source code MUST be included
when using or distributing this software. A kind request that
businesses or individuals generating significant revenue through the use of
this library, or find enough value in it to be worthy of donating a nice coffee or beer,
consider supporting its continued development and maintenance.

-----

</details>
