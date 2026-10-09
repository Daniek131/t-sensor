import shutil
import subprocess
from pathlib import Path

import pytest


def test_cpp_protocol_on_host_compiler(tmp_path):
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("g++ is required to exercise the C++ protocol library")
    root = Path(__file__).resolve().parents[1]
    binary = tmp_path / "protocol-test"
    subprocess.run(
        [
            compiler,
            "-std=c++11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(root / "firmware/include"),
            str(root / "tests/cpp/test_protocol.cpp"),
            "-o",
            str(binary),
        ],
        check=True,
    )
    subprocess.run([str(binary)], check=True)
