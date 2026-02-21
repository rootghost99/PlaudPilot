# FFmpeg Binaries

Place `ffmpeg.exe` and `ffprobe.exe` here for bundled distribution.

## Download

1. Go to https://www.gyan.dev/ffmpeg/builds/ or https://github.com/BtbN/FFmpeg-Builds/releases
2. Download a **static** Windows build (e.g., `ffmpeg-release-essentials.zip`)
3. Extract `ffmpeg.exe` and `ffprobe.exe` from the `bin/` folder
4. Place them in this directory (`vendor/ffmpeg/`)

## Licensing

FFmpeg is licensed under the LGPL 2.1 or later, with optional GPL components.
See https://ffmpeg.org/legal.html for details.

When distributing PlaudPilot with bundled FFmpeg binaries, ensure compliance
with the applicable FFmpeg license terms (include license text with distribution).

## Files expected

```
vendor/ffmpeg/
  ffmpeg.exe
  ffprobe.exe
  README.md   (this file)
```
