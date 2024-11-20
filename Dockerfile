# syntax=docker/dockerfile:1
FROM ubuntu:24.04 AS build

# SHA of version 7.1
ENV FFMPEG_COMMIT_SHA=507a51fbe9732f0f6f12f43ce12431e8faa834b7

ARG ENABLE_FDKAAC=

WORKDIR /src
RUN \
    set -e; \
    export DEBIAN_FRONTEND=noninteractive; \
    apt-get update -qq; \
    apt-get -y install \
        autoconf \
        automake \
        build-essential \
        cmake \
        git \
        libass-dev \
        libfdk-aac-dev \
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
    git init ffmpeg; \
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

FROM ubuntu:24.04

ARG ENABLE_FDKAAC=

RUN set -e; \
    FDKAAC_PKG=$(test -z "$ENABLE_FDKAAC" || echo "libfdk-aac2"); \
    export DEBIAN_FRONTEND=noninteractive; \
    apt-get update && apt-get install -y --no-install-recommends \
        $FDKAAC_PKG \
        libmp3lame0 \
        libopus0 \
        libvorbis0a \
        libvorbisenc2 \
        tini \
        python3 \
    ; \
    apt-get clean; \
    rm -rf \
        /usr/share/doc \
        /var/lib/dpkg/* \
        /var/lib/apt/* \
        /var/cache/* \
        /var/log/* \
    ; \
    find / \
        \( \
        -name '*__pycache__*' \
        -o -name '*.pyc' \
        -o -name '*.pyo' \
        \) \
        -exec rm -rf {} \+

ENV PYTHONPATH=/src
ENV PYTHONUNBUFFERED=1

WORKDIR /src
COPY makem4b ./makem4b
COPY --from=build /src/ffmpeg/ffprobe /src/ffmpeg/ffmpeg /usr/local/bin/


ENTRYPOINT [ "tini", "--", "python3", "-m", "makem4b" ]
CMD [ "--help" ]
