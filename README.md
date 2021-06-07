# Lecture video re-encoding helper

I made this tool to crunch down lecture videos collected during my 2020-202x corona semesters.

### Usage:
```
usage: reencode.py [-h] [-2] [-d [DISTINGUISHER]] [-o] [-q] [--cap-framerate] [--merge-stereo] [--decimate] [-a]
                   [--video-crf [VIDEO_CRF]] [--video-bitrate [VIDEO_BITRATE]] [--audio-bitrate [AUDIO_BITRATE]]
                   file [container]

Lecture re-encoding helper

positional arguments:
  file                  The file to reencode
  container             Use a different container format

optional arguments:
  -h, --help            show this help message and exit
  -2, --two-pass        Use two-pass encoding instead of single-pass
  -d [DISTINGUISHER], --distinguisher [DISTINGUISHER]
                        File suffix to add to re-encoded files
  -o, --overwrite       Overwrite the original file after re-encoding
  -q, --quiet           Only display errors
  --cap-framerate       Limit framerate to 5fps
  --merge-stereo        Merge the stereo channels into each other
  --decimate            Drop similar frames
  -a, --reencode-audio  Reencode audio as opus
  --video-crf [VIDEO_CRF]
                        Set the crf to use, if applicable
  --video-bitrate [VIDEO_BITRATE]
                        Set the two-pass video bitrate to target
  --audio-bitrate [AUDIO_BITRATE]
                        Set the audio bitrate to use
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
