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

# tests/label_processor_test.py

import io
import logging
import os
import pytest
import re
import sys
import tempfile

try:
  import prelapse
except ModuleNotFoundError:
  PARENT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir))
  if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

  import prelapse


def _raise(msg):
    raise AssertionError(msg)

default_asserts = [
  lambda out, err, logs, ff, *a:
    (None if "Dry Run" in out else _raise("Missing 'Dry Run'")),
  lambda out, err, logs, ff, *a:
    (None if "ffconcat version 1.0" in out else _raise("Missing ffconcat version")),
  lambda out, err, logs, ff, *a:
    (None if re.search(r"0.0+?\tgroup", out) else _raise(r"Pattern not found: 0.0...\tgroup")),
  lambda out, err, logs, ff, *a:
    (None if re.search(r"[0-9]+\.[0-9]+\tgroup.(\|boom)?", out) else _raise(r"Pattern not found: time\tgroup..")),
  lambda out, err, logs, ff, *a:
    (None if re.search(r"file 'file:/tmp/[A-Z0-9]+\.(jpg|png)'", out) else _raise("File path not found")),
  lambda out, err, logs, ff, *a:
    (None if "movie='{}'".format(prelapse.common.shell_safe_path(ff)) in out else _raise("Missing movie line")),
]


test_cases = [
  # A tuple for (config_content, labels_content, (optionally custom_case_asserts []))
  (
    # config file contents
    "# groupA\n- /tmp/\n  - 1.jpg\n  - 2.jpg\n  - 3.jpg\n",
    # labels file contents
    "0.0\tgroupA|boom\n1.0\thold\n1.5\tmark\n2.0\tend\n"
  ),
  (
    "# groupA\n- /tmp/\n  - 1.png\n  - 2.png\n  - 3.png\n",
    "0.0\t0.0\tgroupA|boom\n1.0\t1.0\thold\n1.5\t1.5\tmark\n2.0\t2.0\tend\n"
  ),
  (
    "# groupA\n- /tmp/\n  - 1.jpg\n  - 2.jpg\n",
    """0.000000	groupA|tempo1|boom
0.790000	hold|tempo2
1.340000	mark
1.590000	hold
1.640000	mark
1.790000	mark
2.290000	groupA[-1:] # can we do comments #inline?
2.520000	end
"""
  ),
  (
    "# groupA\n- /tmp/\n" + "\n".join(["  - {:03d}.jpg".format(x+1) for x in range(29)]),
    "0.0\tgroupA|boom\n1.0\thold|tempo2\n1.5\tmark\n2.0\tend\n"
  ),
  (
    "# groupA\n- /tmp/\n" + "\n".join(["  - {:03d}.jpg".format(x+1) for x in range(30)]),
    "0.0\tgroupA|boom\n1.0\thold|tempo2\n1.5\tmark\n2.0\tend\n"
  ),
  (
    "# groupA\n- /tmp/\n" + "\n".join(["  - A{:03d}.jpg".format(x+1) for x in range(29)]) +
    "\n# groupB\n- /tmp/\n" + "\n".join(["  - B{:03d}.jpg".format(x+1) for x in range(30)]),
    "0.0\tgroupA|boom\n1.0\thold|tempo2\n1.9\tmark\n2.0\tgroupB\n3.0\tend\n"
  ),
  (
    "# groupA\n- /tmp/\n" + "\n".join(["  - {:03d}.jpg".format(x+1) for x in range(30)]),
    "0.0\tgroupA|boom\n0.9\thold\n1.0\thold|tempo2\n1.9\tmark\n2.0\tend\n"
  ),
  (
    "# groupA\n- /tmp/\n" + "\n".join(["  - {:03d}.jpg".format(x+1) for x in range(2)]),
    "0.0\tgroupA|boom\n0.9\thold\n1.0\thold|tempo2\n1.9\tmark\n2.0\tend\n"
  ),
  (
    "# groupA\n- /tmp/\n" + "\n".join(["  - {:03d}.jpg".format(x+1) for x in range(2)]),
    "0.0\tgroupA\n0.9\thold\n1.0\thold|tempo2\n1.9\tmark\n2.0\tend\n"
  ),
  (
    "# groupA\n- /tmp/\n" + "\n".join(["  - {:03d}.jpg".format(x+1) for x in range(2)]),
    "0.0\tgroupA\n0.9\thold\n1.0\thold|tempo2\n1.8\thold\n2.0\tend\n"
  ),
  (
    "# groupA\n- /tmp/\n" + "\n".join(["  - {:03d}.jpg".format(x+1) for x in range(2)]),
    "0.0\tgroupA\n0.9\thold\n1.0\thold|tempo2\n1.9\thold\n2.0\tend\n"
  ),
  (
    "# groupA\n- /tmp/\n" + "\n".join(["  - {:03d}.jpg".format(x+1) for x in range(2)]),
    "0.0\tgroupA\n0.9\thold\n1.0\ttempo2\n1.95\thold\n2.0\tend\n"
  ),
  (
    "# groupA\n- /tmp/\n" + "\n".join(["  - {:03d}.jpg".format(x+1) for x in range(4)]),
    "0.0\tgroupA|boom\n0.9\thold\n1.0\thold|tempo2\n1.9\tmark\n2.0\tend\n"
  ),
  (
    "# groupA\n- /tmp/\n" + "\n".join(["  - {:03d}.jpg".format(x+1) for x in range(29)]),
    "0.0\tgroupA|boom\n1.0\thold|tempo2\n1.9\tmark\n2.0\tend\n",
    [
      lambda out, err, logs, ff, *a:
        (None if "is more than the number of frames available" in logs else _raise("No dropped frames warning")),
      lambda out, err, logs, ff, *a:
        (None if "Reducing number of files to fit into frames:" in logs else _raise("No dropped frames warning")),
    ]
  )
]


def create_tmp_test_files(config_content, labels_content):
  # Setup: Create temporary files
  temp_files = []

  # Config file
  config_file_fd, config_file = tempfile.mkstemp(suffix=".md")
  temp_files.append(config_file)
  with os.fdopen(config_file_fd, "wb") as f:
    f.write(config_content.encode("utf-8"))

  # Labels file
  labels_file_fd, labels_file = tempfile.mkstemp(suffix=".txt")
  temp_files.append(labels_file)
  with os.fdopen(labels_file_fd, "wb") as f:
    f.write(labels_content.encode("utf-8"))

  # Output ffconcat file
  ffconcat_file_fd, ffconcat_file = tempfile.mkstemp(suffix=".ffconcat")
  temp_files += [ffconcat_file_fd, ffconcat_file]

  return temp_files  # Provide the file paths to the test


def close_temp_files(temp_files):
  # Teardown: Ensure all temporary files are removed
  for file_ref in temp_files:
    # Since file descriptors are ints, we check type and close if needed.
    if isinstance(file_ref, int):
      os.close(file_ref)
    elif os.path.exists(file_ref):
      os.remove(file_ref)


@pytest.fixture(params=test_cases)
def temp_files_fixture(request):
  num_params = len(request.param)
  assert 2 <= num_params <= 3
  config_content, labels_content = request.param[:2]
  asserts = request.param[2] if num_params == 3 else []
  temp_files = []
  try:
    temp_files = create_tmp_test_files(config_content, labels_content)
    yield (*temp_files, asserts)  # Provide the file paths and custom asserts to the test
  finally:
    close_temp_files(temp_files)


def unit_under_test(config_file, labels_file, ffconcat_file_fd, ffconcat_file):
  test_args = "play --hide_banner --ignore-files-dont-exist --dry-run -f {} -fd {} -c {} -l {} -v" \
    .format(ffconcat_file, str(ffconcat_file_fd), config_file, labels_file)
  prelapse.prelapse_main(test_args.split())


def run_asserts(assert_list, out, err, ffconcat_file, *other_files):
  for idx, a in enumerate(assert_list):
    try:
      a(out, err, ffconcat_file, *other_files)
    except AssertionError as e:
      # re-raise with index to help debugging
      raise AssertionError("Assertion #{} failed: {}".format(idx, e)) from None


def test_process_valid_labels(caplog, capsys, temp_files_fixture): #pylint: disable=redefined-outer-name
  config_file, labels_file, ffconcat_file_fd, ffconcat_file, case_asserts = temp_files_fixture
  caplog.set_level(logging.INFO)
  unit_under_test(config_file, labels_file, ffconcat_file_fd, ffconcat_file)
  out, err = capsys.readouterr()
  logs = "\n".join([r.getMessage() for r in caplog.records])

  # Debug print captured output if needed.
  print("Captured stdout:\n", out)
  print("Captured stderr:\n", err)
  print("Captured logs:\n", logs)

  # Assertions to verify output.
  run_asserts(default_asserts + case_asserts, out, err, logs, ffconcat_file, config_file, labels_file)


if __name__ == "__main__":
  for test_case in test_cases:
    num_params = len(test_case)
    assert 2 <= num_params <= 3
    config_content, labels_content = test_case[:2]
    temp_files = []
    try:
      temp_files = create_tmp_test_files(config_content, labels_content)
      config_file, labels_file, ffconcat_file_fd, ffconcat_file = temp_files
      unit_under_test(config_file, labels_file, ffconcat_file_fd, ffconcat_file)
    finally:
      close_temp_files(temp_files)
