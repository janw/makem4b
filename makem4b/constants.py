from pathlib import Path

PROG_NAME = "makem4b"

ENVVAR_PREFIX = PROG_NAME.upper()

CWD = Path.cwd()


TIMEBASE = 1000
CHAPTER_HEADER = f"[CHAPTER]\nTIMEBASE=1/{TIMEBASE}"
SUPPORT_REMUX_CODECS = ("aac", "libfdk_aac")
