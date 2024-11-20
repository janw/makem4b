import argparse
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from makem4b import ffmpeg
from makem4b.analysis import probe_files
from makem4b.metadata import generate_metadata
from makem4b.models import ProbedFile


@contextmanager
def generate_intermediates(files: list[ProbedFile], copy: bool, keep: bool) -> Generator[Path, None, None]:
    if copy:
        print("\nRemuxing individual files (lossless conversion) ...")
        args = ffmpeg.COPY_CMD_ARGS
    else:
        print("\nTranscoding individual files ...")
        first_file = files[0]
        args = ffmpeg.make_transcoding_args(first_file)

    intermediates: list[Path] = []
    try:
        for filen in files:
            print(f" -> {filen.filename} ... ", end="")
            outfilen = filen.filename.with_suffix(".intermed.ts")
            intermediates.append(outfilen)
            ffmpeg.convert([filen.filename], args, output=outfilen)
            print("done.")
        yield intermediates
    finally:
        if not keep:
            for intermediate in intermediates:
                intermediate.unlink()


def main(files: list[Path], keep_intermediates: bool) -> int:
    result = probe_files(files)
    output = result.files[0].filename.with_suffix(".merged.m4b")
    with (
        generate_metadata(result.files) as metadata_file,
        generate_intermediates(
            result.files,
            copy=result.can_copy,
            keep=keep_intermediates,
        ) as intermediates,
    ):
        print("\nMerging ... ", end="")
        concat_files = "concat:" + "|".join(str(i) for i in intermediates)
        ffmpeg.convert([metadata_file, concat_files], ffmpeg.CONCAT_CMD_ARGS, output=output)
        print(f"done.\n\nSaved to '{output}'")

    return 0


parser = argparse.ArgumentParser()
parser.add_argument(
    "files",
    nargs="+",
    metavar="FILES",
    type=Path,
)
parser.add_argument(
    "-k",
    "--keep-intermediates",
    action="store_true",
)

if __name__ == "__main__":
    args = parser.parse_args()
    raise SystemExit(
        main(
            args.files,
            keep_intermediates=args.keep_intermediates,
        )
    )
