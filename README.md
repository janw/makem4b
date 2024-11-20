# makem4b

Merge audio files into an audiobook.

## Usage

```sh
docker run --rm -w /here -v "$PWD:/here" ghcr.io/janw/makem4b glob/of/files/*.mp3
```

### Fraunhofer FDK AAC

Fraunhofer FDK AAC, aka `libfdk-aac`, is a high-quality AAC encoder and thus predestined to encode audiobooks with. But due to licensing issues with FFmpeg, the `makem4b` docker image cannot include `libfdk-aac` by default. A docker image including libfdk-aac can be built by passing a non empty value to the build-arg `ENABLE_FDKAAC`:

```sh
docker build --build-arg ENABLE_FDKAAC=1 . -t my-makem4b:latest
```
