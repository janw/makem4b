# syntax=docker/dockerfile:1
FROM python:3.12 AS build

# SHA of version 7.1
ENV FFMPEG_COMMIT_SHA=507a51fbe9732f0f6f12f43ce12431e8faa834b7

ARG ENABLE_FDKAAC=

WORKDIR /src
RUN \
    set -e; \
    FDKAAC_PKG=$(test -z "$ENABLE_FDKAAC" || echo "libfdk-aac-dev"); \
    test -z "$ENABLE_FDKAAC" || sed -i '/Components/ s/$/ non-free/' \
        /etc/apt/sources.list.d/debian.sources; \
    export DEBIAN_FRONTEND=noninteractive; \
    apt-get update -qq; \
    apt-get -y install \
        $FDKAAC_PKG \
        autoconf \
        automake \
        build-essential \
        cmake \
        git \
        libass-dev \
        libfreetype6-dev \
        libgnutls28-dev \
        libmp3lame-dev \
        libopus-dev \
        libtool \
        libunistring-dev \
        libvorbis-dev \
        meson \
        ninja-build \
        pkg-config \
        texinfo \
        wget \
        yasm \
        zlib1g-dev \
    ;


RUN \
    set -e; \
    FDKAAC_FLAGS=$(test -z "$ENABLE_FDKAAC" || echo " --enable-libfdk-aac --enable-nonfree "); \
    git init -q ffmpeg; \
    cd ffmpeg; \
    git remote add origin https://git.ffmpeg.org/ffmpeg.git; \
    git fetch origin --depth=1 "$FFMPEG_COMMIT_SHA"; \
    git reset --hard FETCH_HEAD; \
    \
    ./configure \
        --pkg-config-flags="--static" \
        --ld="g++" \
        --disable-doc \
        --enable-gpl \
        --enable-libmp3lame \
        --enable-libopus \
        --enable-libvorbis \
        $FDKAAC_FLAGS \
    ; \
    make -j8

ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VERSION=1.8.4

COPY pyproject.toml poetry.lock ./

RUN \
    set -e; \
    pip install  pip "poetry==$POETRY_VERSION"; \
    python -m venv /venv; \
    . /venv/bin/activate; \
    poetry install \
    --no-directory \
    --no-root \
    --only main \
    ; \
    find / \
        \( \
        -name '*__pycache__*' \
        -o -name '*.pyc' \
        -o -name '*.pyo' \
        \) \
        -exec rm -rf {} \+

FROM python:3.12-slim

ARG ENABLE_FDKAAC=

RUN set -e; \
    FDKAAC_PKG=$(test -z "$ENABLE_FDKAAC" || echo "libfdk-aac2"); \
    test -z "$ENABLE_FDKAAC" || sed -i '/Components/ s/$/ non-free/' \
        /etc/apt/sources.list.d/debian.sources; \
    export DEBIAN_FRONTEND=noninteractive; \
    apt-get update && apt-get install -y --no-install-recommends \
        $FDKAAC_PKG \
        libmp3lame0 \
        libopus0 \
        libvorbis0a \
        libvorbisenc2 \
        libxcb1 \
        libxcb-shm0 \
        tini \
    ; \
    apt-get clean; \
    rm -rf \
        /usr/share/doc \
        /var/lib/dpkg/* \
        /var/lib/apt/* \
        /var/cache/* \
        /var/log/*


ENV PATH=/venv/bin:$PATH
ENV PYTHONPATH=/src
ENV PYTHONUNBUFFERED=1

WORKDIR /src
COPY --from=build /src/ffmpeg/ffprobe /src/ffmpeg/ffmpeg /usr/local/bin/
COPY --from=build /venv /venv
COPY makem4b ./makem4b

ENTRYPOINT [ "tini", "--", "python3", "-m", "makem4b" ]
CMD [ "--help" ]
