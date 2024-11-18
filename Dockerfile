FROM ghcr.io/jrottenberg/ffmpeg:7-ubuntu

RUN set -e; \
    export DEBIAN_FRONTEND=noninteractive; \
    apt-get update && apt-get install -y --no-install-recommends \
        tini \
        python3 \
    ; \
    apt-get clean; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /
COPY makem4b.py ./

ENTRYPOINT [ "tini", "--", "python3", "/makem4b.py" ]
CMD [ "--help" ]
