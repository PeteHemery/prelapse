# -*- coding: utf-8 -*-

# Copyright (c) 2020-2025 Pete Hemery - Hembedded Software Ltd. All Rights Reserved
# This file is part of prelapse which is released under the AGPL-3.0 License.
# See the LICENSE file for full license details.

# tests/label_processor_test.py

import io
import os
import pytest
import re
import sys
import tempfile

import prelapse
from prelapse.common import shell_safe_path


test_cases_1 = [
  # A tuple for (config_content, labels_content)
  (
    # config file contents
    "# groupA\n- /tmp/\n  - 1.jpg\n  - 2.jpg\n  - 3.jpg\n",
    # labels file contents
    "0.0\tgroupA|boom\n1.0\thold\n1.5\tmark\n2.0\tend\n"
  ),
  (
    "# groupB\n- /tmp/\n  - 1.png\n  - 2.png\n  - 3.png\n",
    "0.0\t0.0\tgroupB|boom\n1.0\t1.0\thold\n1.5\t1.5\tmark\n2.0\t2.0\tend\n"
  ),
]

@pytest.fixture(params=test_cases_1)
def temp_files_fixture(request):
  config_content, labels_content = request.param

  # Setup: Create temporary files
  temp_files = []
  try:
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

    yield temp_files  # Provide the file paths to the test
  finally:
    # Teardown: Ensure all temporary files are removed
    for file_ref in temp_files:
      # Since file descriptors are ints, we check type and close if needed.
      if isinstance(file_ref, int):
        os.close(file_ref)
      elif os.path.exists(file_ref):
        os.remove(file_ref)


def test_process_valid_labels(capsys, temp_files_fixture): #pylint: disable=redefined-outer-name
  # Unpack temp file paths
  config_file, labels_file, ffconcat_file_fd, ffconcat_file = temp_files_fixture

  test_args = "play --ignore-files-dont-exist --dry-run -f {} -fd {} -c {} -l {} -v" \
    .format(ffconcat_file, str(ffconcat_file_fd), config_file, labels_file)
  prelapse.prelapse_main(test_args.split())
  captured = capsys.readouterr()

  # Debug print captured output if needed.
  print("Captured stdout:", captured.out)
  print("Captured stderr:", captured.err)

  # Assertions to verify output.
  assert "Dry Run" in captured.out
  assert "ffconcat version 1.0" in captured.out
  assert "0.0\tgroup" in captured.out
  assert re.search(r"[0-9]+\.[05]\tgroup.|boom", captured.out), "Pattern not found in output"
  assert re.search(r"file 'file:/tmp/[0-9]+\.(jpg|png)'", captured.out), "Pattern not found in output"
  assert "movie={}".format(shell_safe_path(ffconcat_file)) in captured.out
