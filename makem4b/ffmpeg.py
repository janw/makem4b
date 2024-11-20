import json
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

from makem4b.models import ProbedFile

FFMPEG_CMD_BIN = "ffmpeg"

FFPROBE_CMD = ["ffprobe", "-hide_banner", "-v", "16"]
FFMPEG_CMD = [FFMPEG_CMD_BIN, "-hide_banner", "-v", "16", "-y"]

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
]
CONCAT_CMD_ARGS = [
    "-c:a",
    "copy",
    "-bsf:a",
    "aac_adtstoasc",
    "-movflags",
    "+faststart",
    "-map_metadata",
    "0",
]


def _make_input_args(inputs: list[Path | str] | Path | str) -> list[str]:
    if not isinstance(inputs, list):
        inputs = [inputs]
    args = []
    for file in inputs:
        if isinstance(file, Path) and not file.is_file():
            raise ValueError(f"File '{file}' not found")
        args += ["-i", str(file)]
    return args


def make_transcoding_args(file: ProbedFile) -> list[str]:
    codec_args = [
        "-b:a",
        str(min(file.codec.bit_rate, TRANSCODE_MAX_BITRATE)),
        "-ar",
        str(file.codec.sample_rate),
    ]

    version_output = subprocess.check_output(
        [FFMPEG_CMD_BIN, "-version"],
        stderr=subprocess.PIPE,
    ).decode()

    if "enable-libfdk-aac" in version_output:
        print(" -> (Using libfdk-aac encoder)")
        return TRANSCODE_CMD_ARGS_FDK + codec_args
    print(" -> (Using native FFmpeg encoder)")
    return TRANSCODE_CMD_ARGS_FREE + codec_args


def get_metadata(file: Path) -> str:
    with NamedTemporaryFile("r", prefix="makem4b_metadata_in_") as tempfile:
        subprocess.check_call(
            [
                *FFMPEG_CMD,
                *_make_input_args(file),
                "-f",
                "ffmetadata",
                str(tempfile.name),
            ]
        )
        return tempfile.read()


def probe(file: Path) -> dict:
    try:
        probe_res = subprocess.check_output(
            [
                *FFPROBE_CMD,
                *_make_input_args(file),
                "-output_format",
                "json",
                "-show_streams",
            ],
            stderr=subprocess.PIPE,
        )
        return json.loads(probe_res)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"File {file} could not be probed: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"File {file} could not be parsed: {exc.stderr.decode()}") from exc


def convert(inputs: list[Path | str], args: list[str], *, output: Path) -> None:
    try:
        subprocess.check_output(
            [
                *FFMPEG_CMD,
                *_make_input_args(inputs),
                *args,
                str(output),
            ],
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Conversion failed: {exc.stderr.decode()}") from exc
