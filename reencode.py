#!/usr/bin/env python
"""Lecture re-encoder helper script."""

import argparse
import os
import subprocess
import sys
import textwrap


# https://stackoverflow.com/a/287944
# replace with library eventually (or not, to keep dependencies at 0 for ease of use)
class TermColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_audio_encoding(file):
    p = subprocess.Popen(
        ['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_name', '-of',
         'default=noprint_wrappers=1:nokey=1', file], stdout=subprocess.PIPE)
    line = p.stdout.readline().decode('utf-8').rstrip()
    return line


def get_video_encoding(file):
    p = subprocess.Popen(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name', '-of',
         'default=noprint_wrappers=1:nokey=1', file], stdout=subprocess.PIPE)
    line = p.stdout.readline().decode('utf-8').rstrip()
    return line


SUPPORTED_CONTAINERS = ['.mp4', '.webm']


def main():

    parser = argparse.ArgumentParser(
        prog='lecture-reencoder',
        description='Lecture re-encoding helper',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=textwrap.indent(textwrap.dedent("""\
        Best used in conjunction with something like find:
          find . -name "*.mp4" -exec reencode.py -ao {} ";"
          
        If you have too many cores and want to improve core usage:
          find . -name "*.mp4" -print0 | xargs -0 -P 2 -n 1 reencode.py -aoq
        where -P 2 indicates the number of parallel instances you wish to run.
        
        For videos with just slides, -D / --decimate can greatly improve filesize
        (≥ 66% smaller) at effectively no visual loss, however comes at the cost
        of reducing the framerate into the seconds-per-frame range, which some
        video players do not like.
        
        """), "  ")
    )
    parser.add_argument('file', help='The file to reencode')
    parser.add_argument('container', nargs='?', default=None, help='Use a different container format')
    parser.add_argument('-2', '--two-pass', action='store_true', help='Use two-pass encoding instead of single-pass')
    parser.add_argument('-d', '--distinguisher', nargs='?', default='.2', help='File suffix to add to re-encoded files')
    parser.add_argument('-o', '--overwrite', action='store_true', help='Overwrite the original file after re-encoding')
    parser.add_argument('-q', '--quiet', action='store_true', help='Only display errors')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show all output')
    # parser.add_argument('--av1', action='store_true', help='Use AV1 instead of h265.')
    parser.add_argument('-m', '--merge-stereo', action='store_true', help='Merge the stereo channels into each other')
    parser.add_argument('-D', '--decimate', action='store_true', help='Drop similar frames')
    parser.add_argument('-a', '--reencode-audio', action='store_true', help='Reencode audio as opus')
    parser.add_argument('--cap-framerate', action='store_true', help='Limit framerate to 5fps')
    parser.add_argument('--video-crf', nargs='?', default='23', help='Set the crf to use, if applicable')
    parser.add_argument('--video-bitrate', nargs='?', default='128', help='Set the two-pass video bitrate to target (in kb)')
    parser.add_argument('--audio-bitrate', nargs='?', default='32', help='Set the audio bitrate to use (in kb)')

    args = parser.parse_args()

    ffmpeg = ['ffmpeg', '-hide_banner']
    if args.quiet:
        ffmpeg += ['-loglevel', 'warning', '-nostats']
    elif not args.verbose:
        ffmpeg += ['-stats']

    # output filename
    if args.container is None:
        filename, orig_ext = os.path.splitext(args.file)
        ext = orig_ext
    else:
        filename, orig_ext = os.path.splitext(args.file)
        ext = args.container
        if not '.' in ext:
            ext = '.' + ext

    if ext not in SUPPORTED_CONTAINERS:
        print(f'{TermColors.FAIL}Unsupported container: {TermColors.ENDC}{ext} ({args.file})')
        print(f'{TermColors.WARNING}Supported containers: {TermColors.ENDC}{", ".join(SUPPORTED_CONTAINERS)}')
        sys.exit(1)
        return

    two_minutes = '-ss 0 -t 120'

    in_file = args.file
    in_param = ['-i', in_file]
    out_file = f'{filename}{args.distinguisher}{ext}'
    out_param = [out_file]

    # set up encoding
    video_encode = []
    # do not init video_encode to video_copy, this will break if you apply filters
    # TODO: allow copying video, only reencoding audio
    video_copy = ['-c:v', 'copy']
    if ext == '.webm':  # if webm, use vp9
        if get_video_encoding(args.file) == 'vp9':
            print(f'{TermColors.WARNING}Skipped: {TermColors.ENDC}{filename}{orig_ext}.')
            return
        if args.two_pass:
            video_encode.append(['-c:v', 'libvpx-vp9', '-b:v', f'{args.video_bitrate}k', '-pass', '1'])
            video_encode.append(['-c:v', 'libvpx-vp9', '-b:v', f'{args.video_bitrate}k', '-pass', '2'])
        else:
            video_encode.append(['-c:v', 'libvpx-vp9', '-b:v', f'{args.video_bitrate}k'])

        # force reencode audio in case source is not opus
        args.reencode_audio = True
    elif ext == '.mp4':  # iyf mp4, use h265 (or av1)
        if get_video_encoding(args.file) == 'hevc':
            print(f'{TermColors.WARNING}Skipped: {TermColors.ENDC}{filename}{orig_ext}')
            return
        if args.two_pass:
            params = ['pass=1']
            if args.quiet or not args.verbose:
                params.append('log-level=error')
            video_encode.append(['-c:v', 'libx265', '-preset', 'slow', '-x265-params', ':'.join(params), '-b:v',
                                 f'{args.video_bitrate}k'])
            params = ['pass=2']
            if args.quiet or not args.verbose:
                params.append('log-level=error')
            video_encode.append(['-c:v', 'libx265', '-preset', 'slow', '-x265-params', ':'.join(params), '-b:v',
                                 f'{args.video_bitrate}k'])
        else:
            params = [f'crf={args.video_crf}']
            if args.quiet or not args.verbose:
                params.append('log-level=error')
            video_encode.append(['-c:v', 'libx265', '-preset', 'fast', '-x265-params', ':'.join(params)])

    audio_encode = []
    # do not init audio_encode to audio_copy, this will break if you apply filters
    audio_copy = ['-c:a', 'copy']
    opus_encode = ['-c:a', 'libopus', '-b:a', f'{args.audio_bitrate}k']
    if args.reencode_audio:
        if ext == '.mp4' or ext == '.webm':
            audio_encode = opus_encode
    else:
        if ext == '.webm' and get_audio_encoding(args.file) != 'opus':
            # reencoding is required if converting to webm and opus is not available
            audio_encode = opus_encode
        else:
            audio_encode = audio_copy

    null_path = ''
    if os.name == 'nt':
        null_path = 'NUL'
    else:
        null_path = '/dev/null'

    two_pass = ['-an', '-f', 'null', null_path]

    # set up filters
    video_filter_args = []
    video_filter_extras = []
    if args.decimate:
        video_filter_args.append('mpdecimate')
        video_filter_extras += ['-fps_mode', 'vfr']
        # matroska: -max_interleave_delta 0?
        # fixes the warning but not the output files
    if args.cap_framerate:
        video_filter_args.append('fps=fps=5')

    if len(video_filter_args) > 0:
        video_filters = ['-filter:v', ','.join(video_filter_args)] + video_filter_extras
    else:
        video_filters = video_filter_extras

    audio_filter_args = []
    if args.merge_stereo:
        audio_filter_args.append('pan=stereo|c0<c0+c1|c1<c0+c1')

    if len(audio_filter_args) > 0:
        audio_filters = ['-af', ','.join(audio_filter_args)]
    else:
        audio_filters = []

    if args.overwrite:
        print(f"{TermColors.OKGREEN}Processing{TermColors.ENDC} {in_file}", flush=True)
    else:
        print(f"{in_file} {TermColors.OKGREEN}=>{TermColors.ENDC} {out_file}", flush=True)

    # execute
    if args.two_pass:
        extra_params = []
        if args.overwrite:
            extra_params.append('-y')
        r = subprocess.run(ffmpeg + extra_params + in_param + video_encode[0] + two_pass)
        if r.returncode == 0:
            subprocess.run(ffmpeg + extra_params + in_param + video_encode[
                1] + video_filters + audio_encode + audio_filters + out_param)
            possible_dirt = ['x265_2pass.log', 'x265_2pass.log.cutree']
            for dirt in possible_dirt:
                os.remove(dirt)
    else:
        subprocess.run(ffmpeg + in_param + video_encode[0] + video_filters + audio_encode + audio_filters + out_param)

    if args.overwrite:
        os.replace('{}{}{}'.format(filename, args.distinguisher, ext), '{}{}'.format(filename, ext))


if __name__ == "__main__":
    main()
