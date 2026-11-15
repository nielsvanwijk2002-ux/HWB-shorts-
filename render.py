#!/usr/bin/env python3
"""Hoops Without Borders – Shorts renderer.
Usage: python3 render.py script.json out.mp4
script.json: {"segments":[{"vo":"...", "lines":["BIG","TEXT"], "bg":"dark|red|gold|blue", "big":"optional big number"}], "voice":"am_michael", "speed":1.08}
Fully graphic: kinetic typography, word-by-word captions, synthesized beat + whooshes. Free (Kokoro TTS, ffmpeg, Pillow).
"""
import json, math, os, random, subprocess, sys, tempfile
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS, SR = 1080, 1920, 30, 24000
FONT_DIR = "/usr/share/fonts/opentype/inter"
BLACK = os.path.join(FONT_DIR, "Inter-Black.otf")
BOLD = os.path.join(FONT_DIR, "Inter-ExtraBold.otf")
RED, GOLD, ORANGE, BLUE, WHITE = (232, 40, 48), (245, 195, 70), (245, 120, 35), (40, 70, 160), (255, 255, 255)
BGS = {"dark": ((8, 8, 12), RED), "red": ((40, 4, 8), RED), "gold": ((30, 22, 4), GOLD), "blue": ((6, 12, 40), BLUE), "orange": ((36, 14, 2), ORANGE)}
_fonts = {}


def font(path, size):
    k = (path, size)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(path, size)
    return _fonts[k]


def tts(segments, voice, speed, tmp):
    from kokoro_onnx import Kokoro
    k = Kokoro(os.path.join(HERE, "kokoro-v1.0.onnx"), os.path.join(HERE, "voices-v1.0.bin"))
    clips = []
    for s in segments:
        a, sr = k.create(s["vo"], voice=voice, speed=speed, lang="en-us")
        a = np.asarray(a, dtype=np.float32)
        # trim silence
        idx = np.where(np.abs(a) > 0.01)[0]
        if len(idx):
            a = a[max(0, idx[0] - 600): idx[-1] + 1200]
        gap = np.zeros(int(sr * s.get("pause", 0.12)), dtype=np.float32)
        clips.append(np.concatenate([a, gap]))
    return clips, sr


def synth_music(n, sr, cut_times, mute_ranges):
    t = np.arange(n) / sr
    out = np.zeros(n, dtype=np.float32)
    bpm = 126.0
    beat = 60.0 / bpm
    rng = np.random.default_rng(7)
    kick_len = int(0.25 * sr)
    kt = np.arange(kick_len) / sr
    kick = np.sin(2 * np.pi * (50 + 90 * np.exp(-kt * 30)) * kt) * np.exp(-kt * 9)
    hat_len = int(0.05 * sr)
    hat = rng.standard_normal(hat_len) * np.exp(-np.arange(hat_len) / sr * 80)
    hat = np.diff(np.concatenate([[0], hat]))  # crude highpass
    bass_f = [55, 55, 65.4, 49]
    i = 0
    while i * beat * sr < n:
        p = int(i * beat * sr)
        e = min(n, p + kick_len)
        out[p:e] += 0.9 * kick[: e - p]
        hp = int((i + 0.5) * beat * sr)
        if hp < n:
            e2 = min(n, hp + hat_len)
            out[hp:e2] += 0.25 * hat[: e2 - hp]
        # bass note per beat
        f = bass_f[(i // 4) % 4]
        bl = int(beat * sr * 0.9)
        e3 = min(n, p + bl)
        bt = np.arange(e3 - p) / sr
        out[p:e3] += 0.22 * np.sign(np.sin(2 * np.pi * f * bt)) * np.exp(-bt * 3)
        i += 1
    for a, b in mute_ranges:
        out[int(a * sr): int(b * sr)] *= 0.08
    # whooshes / impacts at cuts
    wl = int(0.35 * sr)
    for c in cut_times:
        p = int(max(0, c - 0.2) * sr)
        e = min(n, p + wl)
        noise = rng.standard_normal(e - p).astype(np.float32)
        env = np.sin(np.linspace(0, np.pi, e - p)) ** 2
        k = np.ones(9) / 9
        out[p:e] += 0.35 * np.convolve(noise, k, mode="same") * env
        ip = int(c * sr)
        il = min(n - ip, int(0.3 * sr))
        if il > 0:
            it = np.arange(il) / sr
            out[ip: ip + il] += 0.6 * np.sin(2 * np.pi * 45 * it) * np.exp(-it * 14)
    out /= max(1e-6, np.abs(out).max())
    return out * 0.16


def bg_image(kind, rng):
    base, glow = BGS.get(kind, BGS["dark"])
    img = Image.new("RGB", (W, H), base)
    g = Image.new("RGB", (W, H), (0, 0, 0))
    d = ImageDraw.Draw(g)
    cx, cy = W // 2 + rng.randint(-200, 200), H // 2 - 200
    for r in range(900, 0, -60):
        a = (1 - r / 900) ** 2
        col = tuple(int(c * a * 0.55) for c in glow)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    img = Image.fromarray(np.clip(np.asarray(img, np.int16) + np.asarray(g.filter(ImageFilter.GaussianBlur(80)), np.int16), 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    # court arc + diagonal stripes
    d.arc([W // 2 - 520, H - 700, W // 2 + 520, H + 340], 180, 360, fill=tuple(min(255, c + 40) for c in base), width=6)
    for k in range(-H, W, 140):
        d.line([(k, 0), (k + H, H)], fill=tuple(min(255, c + 10) for c in base), width=3)
    return img


def fit_size(text, maxw, start):
    s = start
    while s > 40:
        f = font(BLACK, s)
        if f.getlength(text) <= maxw:
            return s
        s -= 6
    return s


def draw_lines(img, lines, t_local, accent, big):
    d = ImageDraw.Draw(img)
    y = 560 if not big else 420
    if big:
        p = min(1.0, t_local / 0.25)
        sc = 1.6 - 0.6 * (1 - (1 - p) ** 3)
        size = int(fit_size(big, 960, 330) * sc)
        f = font(BLACK, size)
        tw = f.getlength(big)
        d.text(((W - tw) / 2 + 8, y + 8), big, font=f, fill=(0, 0, 0))
        d.text(((W - tw) / 2, y), big, font=f, fill=accent)
        y += int(size * 1.15)
    for i, line in enumerate(lines):
        start = 0.12 * i
        if t_local < start:
            break
        p = min(1.0, (t_local - start) / 0.18)
        ease = 1 - (1 - p) ** 3
        size = fit_size(line, 960, 150)
        f = font(BLACK, size)
        tw = f.getlength(line)
        x = (W - tw) / 2 + (1 - ease) * (220 if i % 2 == 0 else -220)
        hi = i == len(lines) - 1 and len(lines) > 1
        if hi:
            pad = 18
            d.rectangle([x - pad, y - 6, x + tw + pad, y + size * 1.05], fill=accent)
            d.text((x, y - size * 0.08), line, font=f, fill=WHITE)
        else:
            d.text((x + 6, y + 6 - size * 0.08), line, font=f, fill=(0, 0, 0))
            d.text((x, y - size * 0.08), line, font=f, fill=WHITE)
        y += int(size * 1.25)


def draw_caption(img, words, t_local, dur):
    # proportional word timing
    if not words:
        return
    lens = np.array([len(w) + 2 for w in words], float)
    ends = np.cumsum(lens) / lens.sum() * dur * 0.97
    k = int(np.searchsorted(ends, t_local))
    k = min(k, len(words) - 1)
    g0 = (k // 3) * 3
    group = words[g0: g0 + 3]
    d = ImageDraw.Draw(img)
    size = 76
    while True:
        f = font(BLACK, size)
        total = sum(f.getlength(w.upper() + " ") for w in group)
        if total <= 960 or size <= 44:
            break
        size -= 4
    x = (W - total) / 2
    y = 1400
    for j, w in enumerate(group):
        txt = w.upper()
        tw = f.getlength(txt)
        if g0 + j == k:
            d.rectangle([x - 12, y - 4, x + tw + 12, y + size * 1.16], fill=RED)
        else:
            d.text((x + 4, y + 4), txt, font=f, fill=(0, 0, 0))
        d.text((x, y), txt, font=f, fill=WHITE)
        x += f.getlength(txt + " ")


def brand(img):
    d = ImageDraw.Draw(img)
    f = font(BOLD, 34)
    txt = "HOOPS WITHOUT BORDERS"
    tw = f.getlength(txt)
    d.text(((W - tw) / 2, 150), txt, font=f, fill=GOLD)
    d.rectangle([(W - 120) / 2, 200, (W + 120) / 2, 206], fill=RED)


def main(script_path, out_path):
    spec = json.load(open(script_path))
    segs = spec["segments"]
    tmp = tempfile.mkdtemp()
    clips, sr = tts(segs, spec.get("voice", "am_michael"), spec.get("speed", 1.08), tmp)
    durs = [len(c) / sr for c in clips]
    starts = np.concatenate([[0], np.cumsum(durs)[:-1]])
    voice = np.concatenate(clips)
    n = len(voice)
    total = n / sr
    mute = [(starts[i], starts[i] + durs[i]) for i, s in enumerate(segs) if s.get("mute_beat")]
    music = synth_music(n, sr, list(starts[1:]), mute)
    mix = voice * 0.95 + music
    mix /= max(1.0, np.abs(mix).max() / 0.98)
    wav = os.path.join(tmp, "a.wav")
    sf.write(wav, mix, sr)

    rng = random.Random(3)
    bgs = [bg_image(s.get("bg", "dark"), rng) for s in segs]
    grain = [Image.fromarray((np.random.default_rng(i).integers(0, 12, (H // 4, W // 4), dtype=np.uint8))).resize((W, H)).convert("RGB") for i in range(4)]
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "25", "-pix_fmt", "yuv420p",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_path], stdin=subprocess.PIPE)
    nf = int(math.ceil(total * FPS))
    for fi in range(nf):
        t = fi / FPS
        si = int(np.searchsorted(starts, t, side="right") - 1)
        si = max(0, min(si, len(segs) - 1))
        s = segs[si]
        tl = t - starts[si]
        base, accent = BGS.get(s.get("bg", "dark"), BGS["dark"])
        if s.get("bg") == "dark":
            accent = GOLD if s.get("big") else RED
        # slow zoom of bg
        z = 1.0 + 0.04 * (tl / max(durs[si], 0.1))
        bw, bh = int(W * z), int(H * z)
        frame = bgs[si].resize((bw, bh)).crop(((bw - W) // 2, (bh - H) // 2, (bw - W) // 2 + W, (bh - H) // 2 + H))
        draw_lines(frame, s.get("lines", []), tl, accent, s.get("big"))
        draw_caption(frame, s["vo"].replace("…", " ").split(), tl, durs[si])
        brand(frame)
        # flash + shake at segment start
        if tl < 0.08:
            frame = Image.blend(frame, Image.new("RGB", (W, H), WHITE), 0.35 * (1 - tl / 0.08))
        arr = np.asarray(frame, np.int16)
        arr = arr + np.asarray(grain[fi % 4], np.int16) - 6
        if tl < 0.2 and s.get("shake", True):
            dx = int(14 * math.sin(tl * 90) * (1 - tl / 0.2))
            arr = np.roll(arr, dx, axis=1)
        # vignette-ish progress bar
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        arr[H - 14:, : int(W * t / total)] = RED
        ff.stdin.write(arr.tobytes())
    ff.stdin.close()
    ff.wait()
    print(json.dumps({"out": out_path, "duration": round(total, 2)}))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
