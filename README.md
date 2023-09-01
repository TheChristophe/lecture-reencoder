# Lecture video re-encoding helper

I made this tool to crunch down lecture videos collected during my 2020-202x corona semesters.

### Usage:
```
usage: lecture-reencoder [-h] [-2] [-d [DISTINGUISHER]] [-o] [-q] [-v] [-m] [-D] [-a] [--cap-framerate] [--video-crf [VIDEO_CRF]] [--video-bitrate [VIDEO_BITRATE]] [--audio-bitrate [AUDIO_BITRATE]] file [container]

Lecture re-encoding helper

positional arguments:
  file                  The file to reencode
  container             Use a different container format

options:
  -h, --help            show this help message and exit
  -2, --two-pass        Use two-pass encoding instead of single-pass
  -d [DISTINGUISHER], --distinguisher [DISTINGUISHER]
                        File suffix to add to re-encoded files
  -o, --overwrite       Overwrite the original file after re-encoding
  -q, --quiet           Only display errors
  -v, --verbose         Show all output
  -m, --merge-stereo    Merge the stereo channels into each other
  -D, --decimate        Drop similar frames
  -a, --reencode-audio  Reencode audio as opus
  --cap-framerate       Limit framerate to 5fps
  --video-crf [VIDEO_CRF]
                        Set the crf to use, if applicable
  --video-bitrate [VIDEO_BITRATE]
                        Set the two-pass video bitrate to target (in kb)
  --audio-bitrate [AUDIO_BITRATE]
                        Set the audio bitrate to use (in kb)

  Best used in conjunction with something like find:
    find . -name "*.mp4" -exec reencode.py -ao {} ";"

  If you have too many cores and want to improve core usage:
    find . -name "*.mp4" -print0 | xargs -0 -P 2 -n 1 reencode.py -aoq
  where -P 2 indicates the number of parallel instances you wish to run.

  For videos with just slides, -D / --decimate can greatly improve filesize
  (≥ 66% smaller) at effectively no visual loss, however comes at the cost
  of reducing the framerate into the seconds-per-frame range, which some
  video players do not like.

```

Personal recommendation for parameters: `reencode.py -ao2 <file>`

### "Sane" video quality defaults

By default, the script is configured to use 128kbit h265 when using mp4. When using webm, the default is vp9. Audio can
also be encoded using `-a` or `--reencode-audio`, which will encode audio to 32kbit opus.

### Notes about experimental parameters

- `--decimate` uses mpdecimate to drop very similar frames. Example scenario: the video is just powerpoint slides. This
  will drastically drop filesize, however this may break playback in a lot of players.
- `--cap-framerate` is a test to reduce filesize by reducing the framerate. Results were unsatisfactory, but the flag
  is kept just in case.
- `--merge-stereo` will merge stereo audio channels into mono, and then split it into stereo again. This is useful to
  avoid sound glitches from certain microphone setups.
- `-2` will execute 2-pass encoding, which may take significantly longer, but yields better results.
