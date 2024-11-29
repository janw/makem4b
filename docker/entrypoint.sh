#!/bin/sh
set -e

CLI_CMD='python3 -m makem4b.cli'

groupmod -o -g "${PUID:-911}" abc >/dev/null
usermod -o -u "${PGID:-911}" abc >/dev/null


case $1 in
bash | sh | ffmpeg | ffprobe)
    CLI_CMD=
    ;;
makem4b)
    shift
    ;;
*)
    ;;
esac

# shellcheck disable=SC2086
exec gosu abc:abc $CLI_CMD "$@"