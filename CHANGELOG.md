## v1.3.0 (2024-12-01)

### Feat

- Bail early if analysis returns irreconcilable results

## v1.2.1 (2024-12-01)

### Fix

- Sort recursive subdirs consistently

## v1.2.0 (2024-12-01)

### Feat

- Consider bit rates equal with less than 128bit variance

### Refactor

- Move sr/br calculation to ffmpeg mod

## v1.1.4 (2024-12-01)

### Fix

- Ensure -Tr work together

## v1.1.3 (2024-12-01)

### Fix

- Ensure temp storage is ignored by Plex, Audiobookshelf
- Prevent transcode with -T but no -r

## v1.1.2 (2024-11-30)

### Fix

- Extract cover image from webp

## v1.1.1 (2024-11-30)

### Fix

- Fix broken chapter timestamps by always remuxing to TS

## v1.1.0 (2024-11-30)

### Feat

- Parse grouping metadata to series+part

## v1.0.0 (2024-11-30)

### Feat

- Introduce --prefer-remux and --no-transcode

### Fix

- Use a supported AAC sample rate when transcoding

### Refactor

- Parse FFprobe output into model
- Disable live progress in debug mode

## v0.6.0 (2024-11-30)

### Feat

- Merge cover into file in recursive mode

## v0.5.3 (2024-11-30)

### Fix

- Improve precision of chapter marker timestamps

## v0.5.2 (2024-11-29)

### Fix

- Fix cover stream disposition
- Make safe filenames

## v0.5.1 (2024-11-29)

### Fix

- Complete subcommand transition

## v0.5.0 (2024-11-29)

### Feat

- Make subcommands; merge, recursive

## v0.4.4 (2024-11-29)

### Fix

- Swap GID/UID

## v0.4.3 (2024-11-29)

### Fix

- Update PyPI metadata, entrypoint

## v0.4.2 (2024-11-29)

### Fix

- Point poetry to correct package dir

## v0.4.1 (2024-11-29)

### Fix

- Make sure poetry can build

## v0.4.0 (2024-11-29)

### Feat

- Publish to PyPI

### Fix

- Ensure privileges are dropped on entry

## v0.3.0 (2024-11-29)

### Feat

- Set atime+mtime from input

## v0.2.6 (2024-11-29)

### Fix

- Move files across filesystems

## v0.2.5 (2024-11-28)

### Fix

- Correct docker entrypoint, improve build

## v0.2.4 (2024-11-26)

### Fix

- Remove extraneous parens

## v0.2.3 (2024-11-26)

### Fix

- Reduce caching complexity
- Avoid duplicate container build

## v0.2.2 (2024-11-26)

### Fix

- Cache from edge+latest

## v0.2.1 (2024-11-26)

### Fix

- Point edge to main HEAD

## v0.2.0 (2024-11-25)

### Feat

- skip ts/aac remux intermediates

## v0.1.0 (2024-11-24)

### Feat

- Add bump-version workflow
