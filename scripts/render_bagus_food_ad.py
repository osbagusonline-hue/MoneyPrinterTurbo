"""Render a tested 10-second portrait commercial; optional Ark Seedance footage.

Default mode animates images. Product pixels never pass through a video model.
"""
import argparse
import asyncio
import importlib
import json
import math
import os
from pathlib import Path
import re
import ssl
import subprocess
import tempfile
import wave
from array import array

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets/food_ads'
VOICE = 'ms-MY-YasminNeural'
SPEECH = 'Nasi putih, ulam, ikan goreng. Lagi berselera dengan Bagus Sambal Belacan. Dapatkan di Bagusmart!'
W, H, FPS = 1080, 1920, 30
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def run(*args):
    subprocess.run([str(a) for a in args], check=True, timeout=300)


def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))


def validate(path):
    data = probe(path)
    v = next(s for s in data['streams'] if s['codec_type'] == 'video')
    a = next(s for s in data['streams'] if s['codec_type'] == 'audio')
    if (v['width'], v['height'], v['codec_name'], v['pix_fmt']) != (W, H, 'h264', 'yuv420p'):
        raise ValueError('Output is not compatible 1080x1920 H.264/yuv420p')
    if abs(float(data['format']['duration']) - 10) > 0.05 or a['codec_name'] != 'aac':
        raise ValueError('Output must be 10 seconds with AAC audio')
    return data


def text(draw, y, message, size=64, color='#fff6df', bold=False):
    font = ImageFont.truetype(BOLD if bold else FONT, size)
    # Fit long CTA strings within title-safe horizontal margins.
    while draw.textbbox((0, 0), message, font=font)[2] > W - 150 and size > 20:
        size -= 2
        font = ImageFont.truetype(BOLD if bold else FONT, size)
    draw.text((W // 2, y), message, font=font, fill=color, anchor='mt')


def layouts(bottle, directory, cta):
    bottle = Image.open(bottle).convert('RGBA')
    # Contain the complete supplied reference including its label; no invented packaging.
    for i in range(3):
        card = Image.new('RGBA', (W, H))
        d = ImageDraw.Draw(card)
        for y in range(H):
            alpha = int(165 * max(0, 1-y/650)) + int(210 * max(0, (y-1400)/520))
            d.line((0, y, W, y), fill=(12, 19, 11, min(240, alpha)))
        if i == 0:
            text(d, 200, 'Biar ringkas.', 86, bold=True)
            text(d, 310, 'Asal berselera.', 74)
            text(d, 440, 'NASI PUTIH  ·  ULAM  ·  IKAN GORENG', 30, '#e5ca87')
        else:
            d.rectangle((0, 0, W, H), fill=(14, 27, 18, 100 if i == 1 else 175))
            text(d, 170, 'BAGUS', 54, '#e4be6b', True)
            text(d, 260, 'Sambal Belacan', 84, bold=True)
            text(d, 365, 'TRADITIONAL', 29, '#e4be6b')
            d = ImageDraw.Draw(card)
            if i == 1:
                text(d, 1460, 'Sekali cicah, lagi berselera.', 45)
            else:
                d.rounded_rectangle((150, 1330, 930, 1445), radius=57, fill='#e4be6b')
                text(d, 1360, 'DAPATKAN DI BAGUSMART', 40, '#102218', True)
                text(d, 1490, cta, 49)
        card.save(directory / f'card{i}.png')
    height = 780
    bottle.resize((round(bottle.width * height / bottle.height), height), Image.Resampling.LANCZOS).save(directory / 'pack.png')


def compose_music(path):
    """Original instrumental bed, generated locally: soft plucks, pad and pulse."""
    rate = 44100
    samples = array('h')
    notes = [220, 261.63, 329.63, 392, 329.63, 261.63, 293.66, 329.63]
    for n in range(rate * 10):
        t = n / rate
        beat = int(t / 0.375)
        u = t % 0.375
        f = notes[beat % len(notes)]
        pluck = math.exp(-u * 10) * (math.sin(2*math.pi*f*t) + .3*math.sin(4*math.pi*f*t))
        pad = sum(math.sin(2*math.pi*f0*t) for f0 in (110, 130.81, 164.81)) / 6
        kick = math.exp(-(t % .75)*24) * math.sin(2*math.pi*58*t)
        fade = min(1, t/.3, (10-t)/.7)
        samples.append(int(6000 * fade * (.55*pluck + .30*pad + .15*kick)))
    with wave.open(str(path), 'wb') as out:
        out.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        out.writeframes(samples.tobytes())


async def generate_voice(audio, subtitles):
    import edge_tts
    # Honor managed proxy trust while keeping TLS verification enabled.
    if os.getenv('SSL_CERT_FILE'):
        importlib.import_module('edge_tts.communicate')._SSL_CTX = ssl.create_default_context(cafile=os.environ['SSL_CERT_FILE'])
    c = edge_tts.Communicate(SPEECH, VOICE, rate='+5%', boundary='WordBoundary',
                            proxy=os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY'))
    words = edge_tts.SubMaker()
    with audio.open('wb') as f:
        async for chunk in c.stream():
            if chunk['type'] == 'audio':
                f.write(chunk['data'])
            elif chunk['type'] == 'WordBoundary':
                words.feed(chunk)
    subtitles.write_text(words.get_srt(), encoding='utf-8')


def grouped_subtitles(source, target):
    # Group the actual TTS word boundaries into short readable captions.
    blocks = re.split(r'\n\s*\n', source.read_text(encoding='utf-8-sig').strip())
    entries = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) >= 3 and ' --> ' in lines[1]:
            start, end = lines[1].split(' --> ')
            entries.append((start, end, ' '.join(lines[2:])))
    if not entries:
        raise ValueError('No timed subtitle cues supplied')
    groups = []
    for start, end, word in entries:
        if not groups or word in ('Lagi', 'Dapatkan'):
            groups.append([start, end, word])
        else:
            groups[-1][1] = end
            groups[-1][2] += ' ' + word
    target.write_text('\n\n'.join(f'{i}\n{s} --> {e}\n{txt}' for i, (s,e,txt) in enumerate(groups, 1))+'\n', encoding='utf-8')


def render(args):
    for path in (args.bottle, args.meal):
        with Image.open(path) as im:
            im.verify()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    audio, words = args.voice_audio, args.subtitles
    if bool(audio) != bool(words):
        raise ValueError('Supply both --voice-audio and --subtitles')
    with tempfile.TemporaryDirectory() as temp:
        t = Path(temp)
        if not audio:
            audio, words = t/'voice.mp3', t/'words.srt'
            asyncio.run(generate_voice(audio, words))
        voice_length = float(probe(audio)['format']['duration'])
        if voice_length > 10:
            raise ValueError('Voiceover exceeds 10s; shorten or speed it up before rendering')
        caption_path = args.output.with_suffix('.srt')
        grouped_subtitles(words, caption_path)
        # Use a simple temp name so user paths cannot inject FFmpeg filter syntax.
        (t/'captions.srt').write_bytes(caption_path.read_bytes())
        layouts(args.bottle, t, args.cta)
        music = args.music or t/'music.wav'
        if not args.music:
            compose_music(music)
        footage = args.footage
        if args.provider == 'seedance':
            if footage:
                raise ValueError('Choose --footage or --provider seedance')
            from food_ad_provider import generate_meal
            footage = generate_meal(args.meal, args.cache)
        if footage:
            if float(probe(footage)['format']['duration']) < 9.9:
                raise ValueError('Generated/supplied footage must be at least 10 seconds')
            source = ['-i', footage]
            background = f'scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps=30,setsar=1'
        else:
            source = ['-loop', '1', '-framerate', '30', '-i', args.meal]
            background = (f'scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,'
                          f"zoompan=z='1.16-0.00035*on':x='iw/2-iw/zoom/2+45*sin(on/110)':y='ih/2-ih/zoom/2+30*cos(on/120)':d=1:s={W}x{H}:fps=30,setsar=1")
        vf = f'[0:v]{background}[bg];'
        # Overlapping alpha dissolves keep the meal moving through every scene.
        fades = ["fade=t=in:st=0:d=0.35:alpha=1,fade=t=out:st=2.5:d=0.6:alpha=1",
                 "fade=t=in:st=2.6:d=0.7:alpha=1,fade=t=out:st=6.7:d=0.7:alpha=1",
                 "fade=t=in:st=6.7:d=0.7:alpha=1"]
        for i, fade in enumerate(fades):
            prev = 'bg' if i == 0 else f'v{i-1}'
            vf += f"[{i+1}:v]format=rgba,{fade}[card{i}];"
            vf += f"[{prev}][card{i}]overlay[v{i}];"
        # A single packshot glides into frame, then remains continuous into the CTA.
        vf += "[4:v]format=rgba,fade=t=in:st=3:d=0.7:alpha=1[pack];"
        vf += ("[v2][pack]overlay=x='(W-w)/2+200*exp(-max(t-3,0)*3)':"
               "y='475+50*exp(-max(t-3,0)*3)-3*max(t-3,0)'[hero];")
        style = 'FontName=DejaVu Sans,FontSize=8,PrimaryColour=&H00FFFFFF,OutlineColour=&H00131B10,BorderStyle=3,Outline=2,Shadow=0,MarginV=22'
        vf += f"[hero]subtitles=filename={t/'captions.srt'}:force_style='{style}',format=yuv420p[v];"
        vf += ('[5:a]aresample=48000,apad,atrim=duration=10,asetpts=PTS-STARTPTS,asplit=2[voice][sc];'
               '[6:a]aresample=48000,apad,atrim=duration=10,volume=0.55[bed];'
               '[bed][sc]sidechaincompress=threshold=0.025:ratio=6:attack=10:release=250[duck];'
               '[voice][duck]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[a]')
        command = ['ffmpeg','-hide_banner','-loglevel','error','-y','-filter_complex_threads','2',*source]
        for i in range(3):
            command += ['-loop','1','-framerate','30','-i',t/f'card{i}.png']
        command += ['-loop','1','-framerate','30','-i',t/'pack.png']
        command += ['-i',audio,'-i',music,'-filter_complex',vf,'-map','[v]','-map','[a]',
                    '-t','10','-r','30','-c:v','libx264','-threads','2','-preset','medium','-crf','19',
                    '-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',args.output]
        run(*command)
    info = validate(args.output)
    args.output.with_suffix('.probe.json').write_text(json.dumps(info, indent=2))
    args.output.with_suffix('.manifest.json').write_text(json.dumps({
        'duration_seconds':10, 'mode':'seedance' if args.provider=='seedance' else 'supplied_footage' if args.footage else 'animated_stills',
        'bottle':str(args.bottle), 'meal':str(args.meal), 'voice':VOICE, 'speech':SPEECH,
        'music':'supplied' if args.music else 'original procedural instrumental', 'cta':args.cta,
        'note':'Food is an AI-generated serving illustration. Actual supplied bottle image is composited unchanged.'
    }, indent=2))
    print(f'Created and validated {args.output}')


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bottle', type=Path, default=ASSETS/'bagus_bottle.png')
    p.add_argument('--meal', type=Path, default=ASSETS/'nasi_putih_ulam_fried_fish.png')
    p.add_argument('--output', type=Path, default=ROOT/'dist/bagus_sambal_belacan_10s.mp4')
    p.add_argument('--provider', choices=['stills','seedance'], default='stills')
    p.add_argument('--footage', type=Path)
    p.add_argument('--cache', type=Path, default=ROOT/'storage/food_ad_provider')
    p.add_argument('--voice-audio', type=Path)
    p.add_argument('--subtitles', type=Path)
    p.add_argument('--music', type=Path)
    p.add_argument('--cta', default='bagusmart.sg')
    return p


if __name__ == '__main__':
    try:
        render(parser().parse_args())
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        raise SystemExit(str(exc)) from None
