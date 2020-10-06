"""Lecture re-encoder helper script."""

import argparse
import os
import subprocess
import sys

def get_audio_encoding():
    #ffprobe -v error -select_streams a:0 -show_entries stream=codec_name -of default=noprint_wrappers=1:nokey=1 video.mkv
    pass

def main():
    parser = argparse.ArgumentParser(description='Lecture re-encoding helper')
    parser.add_argument('file', help='The file to reencode')
    parser.add_argument('container', nargs='?', default=None, help='Use a different container format')
    parser.add_argument('-2', '--two-pass', action='store_true', help='Use two-pass encoding instead of single-pass')
    parser.add_argument('-d', '--distinguisher', nargs='?', default='.2', help='File suffix to add to re-encoded files')
    parser.add_argument('-o', '--overwrite', action='store_true', help='Overwrite the original file after re-encoding')
    parser.add_argument('-q', '--quiet', action='store_true', help='Only display errors')
    #parser.add_argument('--av1', action='store_true', help='Use AV1 instead of h265.')
    parser.add_argument('--cap-framerate', action='store_true', help='Limit framerate to 5fps')
    parser.add_argument('--merge-stereo', action='store_true', help='Merge the stereo channels into each other')
    parser.add_argument('--decimate', action='store_true', help='Drop similar frames')
    parser.add_argument('--reencode-audio', action='store_true', help='Reencode audio as opus')
    parser.add_argument('--video-crf', nargs='?', default='23', help='Set the crf to use, if applicable')
    parser.add_argument('--video-bitrate', nargs='?', default='128', help='Set the two-pass video bitrate to target')
    parser.add_argument('--audio-bitrate', nargs='?', default='32', help='Set the audio bitrate to use')

    args = parser.parse_args()

    ffmpeg = ['ffmpeg', '-hide_banner']
    if args.quiet:
        ffmpeg += ['-loglevel', 'warning', '-nostats']

    # output filename
    if args.container is None:
        filename, orig_ext = os.path.splitext(args.file)
        ext = orig_ext
    else:
        filename, orig_ext = os.path.splitext(args.file)
        ext = args.container
        if not '.' in ext:
            ext = '.' + ext

    if not args.quiet:
        print("{}{} => {}{}{}".format(filename, orig_ext, filename, args.distinguisher, ext))

    two_minutes = '-ss 0 -t 120'

    in_file = args.file
    in_param = ['-i', in_file]
    out_file = '{}{}{}'.format(filename, args.distinguisher, ext)
    out_param = [out_file]

    # set up encoding
    video_encode = []
    # do not init video_encode to video_copy, this will break if you apply filters
    video_copy = ['-c:v', 'copy']
    if ext == '.webm': # if webm, use vp9
        if args.two_pass:
            video_encode.append(['-c:v', 'libvpx-vp9', '-b:v', '{}k'.format(args.video_bitrate), '-pass', '1'])
            video_encode.append(['-c:v', 'libvpx-vp9', '-b:v', '{}k'.format(args.video_bitrate), '-pass', '2'])
        else:
            video_encode.append(['-c:v', 'libvpx-vp9', '-b:v', '{}k'.format(args.video_bitrate)])
        
        # force reencode audio in case source is not opus
        args.reencode_audio = True
    elif ext == '.mp4': # if mp4, use h265 (or av1)
        if args.two_pass:
            params = ['pass=1']
            if args.quiet:
                params.append('log-level=error')
            video_encode.append(['-c:v', 'libx265', '-x265-params', ':'.join(params), '-b:v', '{}k'.format(args.video_bitrate)])
            params = ['pass=2']
            if args.quiet:
                params.append('log-level=error')
            video_encode.append(['-c:v', 'libx265', '-x265-params', ':'.join(params), '-b:v', '{}k'.format(args.video_bitrate)])
        else:
            params = ['crf={}'.format(args.video_crf)]
            if args.quiet:
                params.append('log-level=error')
            video_encode.append(['-c:v',  'libx265', '-preset', 'fast', '-x265-params', ':'.join(params)])

    audio_encode = []
    # do not init audio_encode to audio_copy, this will break if you apply filters
    audio_copy = ['-c:a', 'copy']
    if args.reencode_audio:
        if ext == '.mp4' or ext == '.webm': # todo: only if not already using opus (e.g. coming from an mp4)
            audio_encode += ['-c:a', 'libopus', '-b:a', '{}k'.format(args.audio_bitrate)]
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
        video_filter_extras += ['-vsync', 'vfr']
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

    # execute
    if args.two_pass:
        r = subprocess.run(ffmpeg + ['-y'] + in_param + video_encode[0] + two_pass)
        if r.returncode == 0:
            subprocess.run(ffmpeg + in_param + video_encode[1] + video_filters + audio_encode + audio_filters + out_param)
    else:
        subprocess.run(ffmpeg + in_param + video_encode[0] + video_filters + audio_encode + audio_filters + out_param)

    if args.overwrite:
        os.replace('{}{}{}'.format(filename, args.distinguisher, ext), '{}{}'.format(filename, ext))

if __name__ == "__main__":
    main()
