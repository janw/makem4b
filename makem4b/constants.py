from pathlib import Path

PROG_NAME = "makem4b"

ENVVAR_PREFIX = PROG_NAME.upper()

CWD = Path.cwd()

CACHEDIR_TAG = "CACHEDIR.TAG"

TIMEBASE = 10_000_000
CHAPTER_HEADER = f"[CHAPTER]\nTIMEBASE=1/{TIMEBASE}"
SUPPORT_REMUX_CODECS = ("aac", "libfdk_aac")

AAC_SAMPLE_RATES = (
    8000,
    11025,
    12000,
    16000,
    22050,
    24000,
    32000,
    44100,
    48000,
    64000,
    88200,
    96000,
)
