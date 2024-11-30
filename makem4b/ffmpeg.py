from __future__ import annotations

import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger

from makem4b import constants
from makem4b.emoji import Emoji
from makem4b.utils import TaskProgress, pinfo

if TYPE_CHECKING:
    from collections.abc import Generator

    from makem4b.types import CodecParams


FFMPEG_CMD_BIN = "ffmpeg"

FFPROBE_CMD = [
    "ffprobe",
    "-hide_banner",
    "-v",
    "16",
]
FFMPEG_CMD = [
    FFMPEG_CMD_BIN,
    "-hide_banner",
    "-v",
    "16",
    "-y",
]

TRANSCODE_CMD_ARGS_FDK = [
    "-c:a",
    "libfdk_aac",
]
TRANSCODE_CMD_ARGS_FREE = [
    "-c:a",
    "aac",
]
TRANSCODE_MAX_BITRATE = 192000

COPY_CMD_ARGS = [
    "-c:a",
    "copy",
    "-map",
    "0:a",
    "-muxpreload",
    "0",
    "-muxdelay",
    "0",
    "-vn",
]
CONCAT_CMD_ARGS = [
    "-c:a",
    "copy",
    "-map_metadata",
    "1",
    "-map_chapters",
    "1",
]
CONCAT_AAC_ADDED_ARGS = [
    "-movflags",
    "faststart",
    "-f",
    "mp4",
]

CONCAT_APPEND_COVER_ADDED_ARGS = [
    "-c:v",
    "mjpeg",
    "-map",
    "0:a",
    "-map",
    "2:v",
    "-disposition:1",
    "attached_pic",
    "-metadata:s:v",
    'title="Album cover"',
    "-metadata:s:v",
    'comment="Cover (front)"',
]

re_progress = re.compile(r"^total_size=(\d+)")


def _make_input_args(inputs: list[Path | str] | Path | str) -> list[str]:
    if not isinstance(inputs, list):
        inputs = [inputs]
    args = []
    for file in inputs:
        if isinstance(file, Path) and not file.is_file():
            msg = f"File '{file}' not found"
            raise ValueError(msg)
        args += ["-i", str(file)]
    return args


def make_transcoding_args(codec: CodecParams) -> list[str]:
    codec_args = [
        "-ar",
        str(codec.sample_rate),
        "-b:a",
        str(min(codec.bit_rate, TRANSCODE_MAX_BITRATE)),
        "-vn",
    ]

    version_output = subprocess.check_output(  # noqa: S603
        [FFMPEG_CMD_BIN, "-version"],
        stderr=subprocess.PIPE,
    ).decode()

    if "enable-libfdk-aac" in version_output:
        pinfo(Emoji.FDKAAC, "Using libfdk-aac encoder")
        return TRANSCODE_CMD_ARGS_FDK + codec_args
    return TRANSCODE_CMD_ARGS_FREE + codec_args


def _poll_for_progress(process: subprocess.Popen[bytes]) -> Generator[int, None, None]:
    while True:
        if process.stdout is None:
            continue

        stdout_line = process.stdout.readline().decode("utf-8", errors="replace").strip()
        if stdout_line == "" and process.poll() is not None:
            break

        if match := re_progress.search(stdout_line):
            yield round(int(match.group(1)))


def _check_result(process: subprocess.Popen[bytes] | subprocess.CompletedProcess[bytes], *, args: list[str]) -> None:
    if process.returncode != 0:
        msg = f"Error running command {shlex.join(['ffmpeg']+args)}"
        raise RuntimeError(msg)


def wrapped_ffmpeg(args: list[str]) -> Generator[int, None, None]:
    progress_args = ["-progress", "-", "-nostats"]
    process = subprocess.Popen(  # noqa: S603
        FFMPEG_CMD + progress_args + args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=False,
    )
    yield from _poll_for_progress(process)
    _check_result(process, args=args)


def wrapped_ffmpeg_no_progress(args: list[str]) -> None:
    list(wrapped_ffmpeg(args))


def extract_cover_img(file: Path, *, output: Path) -> None:
    wrapped_ffmpeg_no_progress(
        [
            *_make_input_args(file),
            "-map_metadata",
            "-1",
            "-map",
            "0:v",
            "-map",
            "-0:V",
            "-c",
            "copy",
            str(output),
        ],
    )


def probe(file: Path) -> dict[str, Any]:
    try:
        probe_res = subprocess.check_output(  # noqa: S603
            [
                *FFPROBE_CMD,
                *_make_input_args(file),
                "-output_format",
                "json",
                "-show_streams",
                "-show_entries",
                "format_tags",
            ],
            stderr=subprocess.PIPE,
        )
        return json.loads(probe_res)
    except json.JSONDecodeError as exc:
        msg = f"File {file} could not be probed: {exc}"
        raise RuntimeError(msg) from exc
    except subprocess.CalledProcessError as exc:
        msg = f"File {file} could not be parsed: {exc.stderr.decode()}"
        raise RuntimeError(msg) from exc


def probe_duration(file: Path) -> int:
    probe_res = subprocess.check_output(  # noqa: S603
        [
            *FFPROBE_CMD,
            *_make_input_args(file),
            "-output_format",
            "csv=p=0",
            "-show_entries",
            "format=duration",
        ],
        text=True,
    )
    return round(float(probe_res) * constants.TIMEBASE)


def convert(inputs: list[Path | str], args: list[str], *, output: Path, progress: TaskProgress) -> None:
    try:
        all_args = [
            *_make_input_args(inputs),
            *args,
            str(output),
        ]
        logger.debug("Running command: {}", shlex.join(all_args))
        for completed in wrapped_ffmpeg(all_args):
            progress.update(completed=completed)
        progress.close()
    except subprocess.CalledProcessError as exc:
        msg = f"Conversion failed: {exc.stderr.decode()}"
        raise RuntimeError(msg) from exc


def concat(inputs: list[Path | str], args: list[str], *, output: Path, progress: TaskProgress) -> None:
    if output.suffix in (".m4a", ".m4b"):
        args = args + CONCAT_AAC_ADDED_ARGS
    try:
        all_args = [
            "-f",
            "concat",
            "-safe",
            "0",
            *_make_input_args(inputs),
            *args,
            str(output),
        ]
        logger.debug("Running command: {}", shlex.join(all_args))
        for completed in wrapped_ffmpeg(all_args):
            progress.update(completed=completed)
        progress.close()
    except subprocess.CalledProcessError as exc:
        msg = f"Conversion failed: {exc.stderr.decode()}"
        raise RuntimeError(msg) from exc
