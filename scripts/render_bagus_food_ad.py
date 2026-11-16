"""Render a 10-second 9:16 Bagus commercial with real product/meal images.

Requires ffmpeg, ffprobe, edge-tts and network access for Microsoft Edge TTS.
This is a motion-graphics MP4, not generative image-to-video footage.
"""
import argparse
import asyncio
import os
from pathlib import Path
import subprocess
import tempfile

import edge_tts

VOICE = "ms-MY-YasminNeural"
SPEECH = "Nak makan lebih berselera? Cuba Bagus Sambal Belacan! Dapatkan sekarang di Bagusmart!"
W, H = 1080, 1920


def run(*args):
    subprocess.run(args, check=True)


def filter_text(value):
    # FFmpeg drawtext requires escaping punctuation that affects filter parsing.
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")


def image_segment(image, output, seconds, title, subtitle):
    # Render the image uncropped and with a dark background; animated zoom on
    # stills is intentionally avoided to preserve legibility of bottle labels.
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x17100e,"
        "format=yuv420p,"
        f"drawbox=x=0:y=1540:w=iw:h=380:color=black@0.64:t=fill,"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{filter_text(title)}':fontcolor=white:fontsize=64:x=(w-text_w)/2:y=1580,"
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        f"text='{filter_text(subtitle)}':fontcolor=white:fontsize=42:x=(w-text_w)/2:y=1700"
    )
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-framerate", "30", "-i", str(image),
        "-t", str(seconds), "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
        "-an", str(output))


async def generate_voice(path):
    await edge_tts.Communicate(SPEECH, VOICE, rate="+12%").save(str(path))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bottle", required=True, type=Path)
    p.add_argument("--meal", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    for path in (args.bottle, args.meal):
        if not path.is_file() or path.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            p.error(f"Missing valid image: {path}. Upload real assets before running.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        t = Path(temp)
        parts = [t / f"part{i}.mp4" for i in range(3)]
        image_segment(args.bottle, parts[0], 3, "BAGUS SAMBAL BELACAN", "Traditional")
        image_segment(args.meal, parts[1], 4, "NASI, ULAM & IKAN GORENG", "Sedap dengan sambal belacan")
        image_segment(args.bottle, parts[2], 3, "SHOP NOW", "bagusmart.sg  |  TikTok Bagusmart")
        playlist = t / "concat.txt"
        playlist.write_text("".join(f"file '{part.as_posix()}'\n" for part in parts))
        video = t / "video.mp4"
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "concat", "-safe", "0", "-i", str(playlist),
            "-c", "copy", str(video))
        voice = t / "voice.mp3"
        asyncio.run(generate_voice(voice))
        # Pad or trim audio to precisely 10 seconds, preserving video duration.
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(video), "-i", str(voice),
            "-filter_complex", "[1:a]apad,atrim=duration=10,asetpts=N/SR/TB[a]",
            "-map", "0:v:0", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
            "-t", "10", "-movflags", "+faststart", str(args.output))
    print(f"Created {args.output}")


if __name__ == "__main__":
    main()
