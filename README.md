# makem4b

<!-- markdownlint-disable MD033 MD013 -->
<div align="center">

[![Docker Build](https://github.com/janw/makem4b/actions/workflows/docker-build.yaml/badge.svg)](https://ghcr.io/janw/makem4b)
![GitHub Release](https://img.shields.io/github/v/release/janw/makem4b)
[![python](https://img.shields.io/pypi/pyversions/makem4b.svg)](https://pypi.org/project/makem4b/)
[![downloads](https://img.shields.io/pypi/dm/makem4b)](https://pypi.org/project/makem4b/)

[![Maintainability](https://api.codeclimate.com/v1/badges/7ebb6f412bbbd1b27a5c/maintainability)](https://codeclimate.com/github/janw/makem4b/maintainability)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://docs.astral.sh/ruff/)
[![poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/docs/)
[![pre-commit](https://img.shields.io/badge/-pre--commit-f8b424?logo=pre-commit&labelColor=grey)](https://github.com/pre-commit/pre-commit)

</div>

Merge audio files into an audiobook.

## Setup

Recommended: use it via Docker:

```bash
docker run --tty --rm ghcr.io/janw/makem4b --help
```

Or install via [pipx](https://pipx.pypa.io/stable/) (requires you to supply [FFmpeg](https://ffmpeg.org/download.html) yourself)

```bash
pipx install makem4b
```

## Usage

Basic

```sh
docker run --tty --rm -w /here -v "$PWD:/here" ghcr.io/janw/makem4b glob/of/files/*.mp3
```

Slightly more advanced:

```sh
docker run --tty --rm -e PUID=816 -e PGID=1006 -v /here -v "$PWD:/here" ghcr.io/janw/makem4b -Tr -m originals glob/of/files/*.mp3
```

* `-e PUID=816 -e PGID=1006` Writing/moving files as user:group 816:1006
* `-T`: Never transcode, bail if files use different codec parameters
* `-r`: Prefer remuxing, saving output with original filetype (mp3) as long as code parameters match
* `-m originals`: Move original files to a subdirectory within `originals` after completion

### Fraunhofer FDK AAC

Fraunhofer FDK AAC, aka `libfdk-aac`, is a high-quality AAC encoder and thus predestined to encode audiobooks with. But due to licensing issues with FFmpeg, the `makem4b` docker image cannot include `libfdk-aac` by default. A docker image including libfdk-aac can be built by passing a non empty value to the build-arg `ENABLE_FDKAAC`:

```sh
docker build --build-arg ENABLE_FDKAAC=1 . -t my-makem4b:latest
```
