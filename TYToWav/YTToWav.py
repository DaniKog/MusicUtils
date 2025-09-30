from __future__ import unicode_literals
import yt_dlp
import ffmpeg
import sys


def download_from_url(url,format):
    ydl.download([url])
    stream = ffmpeg.input('output/output.m4a')
    stream = ffmpeg.output(stream, f'output/output.{format}')



args = sys.argv[1:]
url = ""
format = ""
if len(args) > 1:
    print("Too many arguments.")
    print("Usage: python youtubetowav.py <optional link>")
    print("If a link is given it will automatically convert it to .wav. Otherwise a prompt will be shown")
    exit()
if len(args) == 0:
    url=input("Enter Youtube URL: ")
   
    format_choice = 0
    print("FORMAT")
    while format_choice < 1 or format_choice > 2:
        print("Choose a format")
        print("1. Wav")
        print("2. mp3")
        format_choice = int(input(""))
    
    if format_choice == 1: 
        format = "wav"
    elif format_choice == 2:
        format = "mp3"
else:
    url = args[0]
    format = args[1]

ydl_opts = {
    'format': 'bestaudio/best',
#    'outtmpl': 'output.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': format,
    }],
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        download_from_url(url,format)

