import argparse
import json
import subprocess
from dataclasses import dataclass
from operator import itemgetter
from pathlib import Path
from typing import Iterable

MIN_BITRATE = 96000


@dataclass
class ProbeResult:
    files: list[Path]
    streams: list[int]
    codecs: set[tuple[str, int, float, int]]

    @property
    def can_be_concatenated(self) -> bool:
        return len(self.codecs) == 1 and list(self.codecs)[0][0] in ("aac", "libfdk_aac")


def probe_files(files_to_probe: Iterable[Path]) -> ProbeResult:
    codecs = set()
    valid_files: list[Path] = []
    streams: list[int] = []
    for file in sorted(files_to_probe):
        if not file.is_file():
            raise ValueError(f"File {file} not found")
        try:
            probe_res = subprocess.check_output(
                [
                    "ffprobe",
                    "-v",
                    "16",
                    "-i",
                    str(file),
                    "-output_format",
                    "json",
                    "-show_streams",
                ],
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"File {file} could not be parsed: {exc.stderr.decode()}") from None

        media = json.loads(probe_res)
        for idx, stream in enumerate(media.get("streams", [])):
            if stream.get("codec_type", "") == "audio":
                codecs.add(
                    (
                        stream["codec_name"],
                        int(stream["channels"]),
                        float(stream["sample_rate"]),
                        round(float(stream["bit_rate"]) / 10) * 10,
                    )
                )
                valid_files.append(file)
                streams.append(idx)
                break
        else:
            raise ValueError(f"File {file} contains no usable audio stream")

    return ProbeResult(files=valid_files, streams=streams, codecs=codecs)


def generate_intermediates(files: list[Path], intermediate_args: list[str]) -> list[Path]:
    intermediates = []
    for idx, filen in enumerate(files):
        outfilen = filen.with_name(f"_intermediate_{idx:04d}.ts")
        intermediates.append(outfilen)
        subprocess.check_call(
            [
                "ffmpeg",
                "-hide_banner",
                "-y",
                "-i",
                str(filen),
                *intermediate_args,
                str(outfilen),
            ],
        )
    return intermediates


def main(files: list[Path]) -> int:
    result = probe_files(files)
    if result.can_be_concatenated:
        print("Can be concatenated")
        intermediate_args = [
            "-c:a",
            "copy",
        ]
    else:
        print("Will transcode")
        _, _, sample_rate, bit_rate = max(result.codecs, key=itemgetter(2, 3))
        intermediate_args = [
            "-c:a",
            "libfdk_aac",
            "-b:a",
            str(max(bit_rate, MIN_BITRATE)),
            "-ar",
            str(sample_rate),
        ]

    intermediates = generate_intermediates(result.files, intermediate_args)
    inputs = "concat:" + "|".join(str(i) for i in intermediates)
    first_file = result.files[0]
    output = first_file.with_stem(first_file.stem + "_merged").with_suffix(".m4b")
    subprocess.check_call(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-i",
            inputs,
            "-c:a",
            "copy",
            "-bsf:a",
            "aac_adtstoasc",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )

    for intermediate in intermediates:
        intermediate.unlink()
    return 0


parser = argparse.ArgumentParser()
parser.add_argument(
    "files",
    nargs="+",
    metavar="FILES",
    type=Path,
)

if __name__ == "__main__":
    args = parser.parse_args()
    raise SystemExit(main(args.files))
