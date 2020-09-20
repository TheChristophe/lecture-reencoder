"""Lecture re-encoder helper script."""

import argparse
import os
import subprocess
import sys

parser = argparse.ArgumentParser(description='Lecture re-encoding helper')
parser.add_argument('file', help='The file to reencode')
parser.add_argument('container', nargs='?', default='', help='Use a different container format')
parser.add_argument('-2', '--two-pass', action='store_true', help='Use two-pass encoding instead of single-pass')
parser.add_argument('-d', '--distinguisher', nargs='?', default='.2', help='File suffix to add to re-encoded files')
parser.add_argument('-o', '--overwrite', action='store_true', help='Overwrite the original file after re-encoding')
#parser.add_argument('--av1', action='store_true', help='Use AV1 instead of h265.')
parser.add_argument('--cap-framerate', action='store_true', help='Limit framerate to 5fps')
parser.add_argument('--merge-stereo', action='store_true', help='Merge the stereo channels into each other')
parser.add_argument('--no-decimate', action='store_true', help='Do not drop similar frames')
parser.add_argument('--reencode-audio', action='store_true', help='Reencode audio as 128k AAC')
parser.add_argument('--video-bitrate', nargs='?', default='128', help='Set a  two-pass video bitrate to use')

args = parser.parse_args()

# output filename
if len(args.container) == 0:
    filename, orig_ext = os.path.splitext(args.file)
    ext = orig_ext
else:
    filename, orig_ext = os.path.splitext(args.file)
    ext = args.container
    if not '.' in ext:
        ext = '.' + ext

print("{}{} => {}{}{}".format(filename, orig_ext, filename, args.distinguisher, ext))

two_minutes = '-ss 0 -t 120'

in_file = ['-i', '{}'.format(args.file)]
out_file = ['{}{}{}'.format(filename, args.distinguisher, ext)]

# set up encoding
encode_params = []
if ext == '.webm': # if webm, use vp9
    encode_params.append([]) # todo: vp9
elif ext == '.mp4': # if mp4, use h265 (or av1)
    if args.two_pass:
        encode_params.append(['-c:v', 'libx265', '-x265-params', 'pass=1', '-b:v {args.video_bitrate}k'])
        encode_params.append(['-c:v', 'libx265', '-b:v', '{args.video_bitrate}k', '-x265-params', 'pass=2'])
    else:
        encode_params.append(['-c:v',  'libx265', '-preset', 'fast', '-x265-params', 'crf=23'])

if args.reencode_audio:
    if ext == '.mp4':
        encode_params += ['-c:a', 'aac', '-b:a', '128k']
    else:
        print('AAC not allowed outside mp4')
        sys.exit(-1)

two_pass = ['-an', '-f', 'null', 'NUL']

# set up filters
video_filter_args = []
video_filter_extras = []
if not args.no_decimate:
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

filters = video_filters + audio_filters

# execute
if args.two_pass:
    r = subprocess.run(['ffmpeg', '-y', in_file, encode_params[0], two_pass])
    if r == 0:
        subprocess.run(['ffmpeg', in_file, encode_params[1], filters, out_file])
else:
    subprocess.run(['ffmpeg'] + in_file + encode_params[0] + filters + out_file)

if args.overwrite:
    os.replace(out_file, in_file)
