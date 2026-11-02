# StungKir - писательский блокнот. Copyright (C) 2026 KiriFesTung
# SPDX-License-Identifier: GPL-3.0-or-later
"""Звуки кубиков, монетки, рулетки и пупырки - синтез, без чужих записей. Запуск из корня проекта:
    python3 packaging/sounds/make_sounds.py
Пишет stungkir/sounds/*.wav (моно, 44,1 кГц, 16 бит). Нужен numpy - только здесь, не в самом блокноте."""

import wave
from pathlib import Path

import numpy as np

RATE = 44100
OUT = Path(__file__).resolve().parents[2] / "stungkir" / "sounds"
rng = np.random.default_rng(20261015)


def t_axis(seconds):
    return np.arange(int(seconds * RATE)) / RATE


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / RATE)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def wood(seconds, strength=1.0):
    """Глухой удар по деревянному столу."""
    t = t_axis(seconds)
    noise = lowpass(lowpass(rng.standard_normal(len(t)), 900), 900)
    body = noise / (np.abs(noise).max() + 1e-9) * np.exp(-t / 0.016)
    knock = np.sin(2 * np.pi * 165 * t) * np.exp(-t / 0.028) + 0.5 * np.sin(2 * np.pi * 310 * t) * np.exp(-t / 0.018)
    return strength * (0.75 * body + 0.6 * knock)


def metal(seconds, f0, ratios, amps, decays, wobble=0.0):
    """Звон металла: неровный ряд призвуков, каждый гаснет со своей скоростью."""
    t = t_axis(seconds)
    out = np.zeros_like(t)
    for ratio, amp, decay in zip(ratios, amps, decays):
        f = f0 * ratio * (1 + rng.uniform(-0.004, 0.004))
        phase = rng.uniform(0, 2 * np.pi)
        tone = np.sin(2 * np.pi * f * t + phase)
        if wobble:
            tone *= 1 - wobble * (0.5 + 0.5 * np.sin(2 * np.pi * (7 + 20 * t) * t))   # монетка «дребезжит»
        out += amp * tone * np.exp(-t / decay)
    click = highpass(rng.standard_normal(len(t)), 3000) * np.exp(-t / 0.0012)
    return out + 0.35 * click


def place(track, sound, at):
    start = int(at * RATE)
    end = min(len(track), start + len(sound))
    track[start:end] += sound[:end - start]


def finish(x, peak=0.7):
    x = x - x.mean()
    fade = min(len(x), int(0.02 * RATE))
    x[-fade:] *= np.linspace(1, 0, fade)
    attack = int(0.0008 * RATE)
    x[:attack] *= np.linspace(0, 1, attack)
    return x / (np.abs(x).max() + 1e-9) * peak


def save(name, x):
    OUT.mkdir(parents=True, exist_ok=True)
    data = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)


def die_hit(f0, length=0.42):
    """Металлический кубик стукнулся о стол."""
    ratios = [1.0, 1.53, 2.27, 2.94, 3.71, 4.62]
    amps = [1.0, 0.7, 0.5, 0.33, 0.22, 0.12]
    decays = [0.11, 0.085, 0.065, 0.05, 0.038, 0.03]
    ring = metal(length, f0, ratios, amps, decays)
    return finish(0.9 * wood(length) + 0.28 * ring)


def die_settle():
    """Докатился: два-три коротких перестука на ребре."""
    track = np.zeros(int(0.36 * RATE))
    for at, strength, f0 in ((0.0, 1.0, 3050), (0.045, 0.55, 3320), (0.078, 0.3, 2980)):
        place(track, strength * die_hit(f0, 0.22), at)
    return finish(track, 0.55)


def coin_flick():
    """Щелчок пальцем по монетке - тонкий высокий звон."""
    ring = metal(0.7, 4350, [1.0, 2.41, 3.92], [1.0, 0.25, 0.1], [0.42, 0.16, 0.08])
    return finish(ring, 0.45)


def coin_land():
    """Монетка упала на стол: мягкий короткий звяк, без долгого звона (долгий раздражал)."""
    ring = metal(1.1, 2150, [1.0, 1.006, 2.33, 3.81, 5.42], [1.0, 0.7, 0.22, 0.08, 0.03],
                 [0.16, 0.13, 0.07, 0.04, 0.025], wobble=0.35)
    track = 0.8 * lowpass(wood(1.1), 2400) + 0.22 * lowpass(ring, 3600)
    return finish(track, 0.42)


def drum_spin():
    """Барабан револьвера крутится: трещотка щелчков, всё реже, как он тормозит."""
    track = np.zeros(int(1.35 * RATE))
    at, gap = 0.0, 0.028
    while at < 1.2:
        tick = metal(0.05, 5200 + rng.uniform(-200, 200), [1.0, 1.9], [1.0, 0.4], [0.008, 0.005])
        place(track, (0.5 + 0.5 * (1 - at / 1.2)) * tick, at)
        at += gap
        gap *= 1.09
    return finish(track, 0.4)


def trigger_click():
    """Курок щёлкнул по пустому гнезду: сухой короткий металл."""
    hit = metal(0.12, 2600, [1.0, 2.7, 4.1], [1.0, 0.5, 0.3], [0.018, 0.012, 0.008])
    return finish(0.6 * hit + 0.4 * wood(0.12, 0.6), 0.55)


def bang():
    """«Выстрел» - глухой мультяшный хлопок, не оглушает."""
    t = t_axis(0.6)
    noise = lowpass(rng.standard_normal(len(t)), 1800) * np.exp(-t / 0.07)
    thump = np.sin(2 * np.pi * (70 + 60 * np.exp(-t / 0.05)) * t) * np.exp(-t / 0.16)
    return finish(0.8 * noise / (np.abs(noise).max() + 1e-9) + 0.9 * thump, 0.6)


def pop():
    """Лопнул пузырёк пупырки: короткий сухой щелчок с крошечным «чпок» вниз."""
    t = t_axis(0.09)
    burst = highpass(rng.standard_normal(len(t)), 1500) * np.exp(-t / 0.006)
    tone = np.sin(2 * np.pi * (900 * np.exp(-t / 0.02) + 300) * t) * np.exp(-t / 0.018)
    return finish(0.7 * burst + 0.5 * tone, 0.5)


def ball_bounce():
    """Резиновый мячик ударился: мягкий упругий «бум» с коротким призвуком резины."""
    t = t_axis(0.22)
    body = np.sin(2 * np.pi * (110 + 140 * np.exp(-t / 0.012)) * t) * np.exp(-t / 0.045)
    rubber = np.sin(2 * np.pi * 420 * t) * np.exp(-t / 0.012)
    slap = lowpass(rng.standard_normal(len(t)), 2500) * np.exp(-t / 0.004)
    return finish(body + 0.35 * rubber + 0.25 * slap / (np.abs(slap).max() + 1e-9), 0.6)


def type_key(f0):
    """Клавиша печатной машинки: удар литеры по валику - щелчок, металл и глухой стук."""
    t = t_axis(0.11)
    strike = highpass(rng.standard_normal(len(t)), 2000) * np.exp(-t / 0.0025)
    slug = metal(0.11, f0, [1.0, 2.3, 3.7], [1.0, 0.4, 0.2], [0.012, 0.008, 0.005])
    thud = np.sin(2 * np.pi * 180 * t) * np.exp(-t / 0.015)
    return finish(0.8 * strike + 0.35 * slug + 0.6 * thud, 0.5)


def type_space():
    """Пробел: широкая планка - стук глуше, без звона литеры."""
    t = t_axis(0.12)
    thud = np.sin(2 * np.pi * 140 * t) * np.exp(-t / 0.02)
    clack = lowpass(rng.standard_normal(len(t)), 1800) * np.exp(-t / 0.006)
    return finish(0.9 * thud + 0.6 * clack / (np.abs(clack).max() + 1e-9), 0.45)


def type_return():
    """Новая строка: звоночек каретки и протяжка валика."""
    track = np.zeros(int(0.7 * RATE))
    bell = metal(0.6, 2350, [1.0, 2.76, 5.4], [1.0, 0.3, 0.1], [0.35, 0.12, 0.05])
    place(track, 0.7 * bell, 0.0)
    t = t_axis(0.28)
    ratchet = np.zeros_like(t)
    for at in np.arange(0.0, 0.26, 0.022):
        start = int(at * RATE)
        n = min(len(t) - start, int(0.01 * RATE))
        ratchet[start:start + n] += highpass(rng.standard_normal(n), 2500) * np.exp(-np.arange(n) / RATE / 0.002)
    place(track, 0.5 * ratchet, 0.18)
    return finish(track, 0.5)


def chime():
    """Мягкий звоночек «пора отдохнуть глазам»: два тихих тона."""
    track = np.zeros(int(1.6 * RATE))
    place(track, metal(1.2, 880, [1.0, 2.0, 3.01], [1.0, 0.25, 0.08], [0.6, 0.3, 0.15]), 0.0)
    place(track, metal(1.2, 1318.5, [1.0, 2.0, 3.01], [1.0, 0.25, 0.08], [0.6, 0.3, 0.15]), 0.28)
    return finish(track, 0.4)


def spinner():
    """Спиннер: тихий подшипниковый шорох с ритмичным посвистом."""
    t = t_axis(0.5)
    hiss = highpass(lowpass(rng.standard_normal(len(t)), 5000), 900)
    hum = 0.5 + 0.5 * np.sin(2 * np.pi * 24 * t)
    env = np.minimum(1, t / 0.05) * np.exp(-t / 0.35)
    return finish(hiss * hum * env, 0.3)


def bone_hit(f0, length=0.2):
    """Костяной кубик о стол: сухой высокий «ток», почти без звона."""
    t = t_axis(length)
    tok = np.sin(2 * np.pi * f0 * t) * np.exp(-t / 0.009) + 0.5 * np.sin(2 * np.pi * f0 * 1.7 * t) * np.exp(-t / 0.006)
    click = highpass(rng.standard_normal(len(t)), 2500) * np.exp(-t / 0.0015)
    return finish(0.6 * wood(length, 0.7) + 0.55 * tok + 0.4 * click, 0.6)


def oak_hit(f0, length=0.26):
    """Дубовый кубик о стол: глухой тёплый стук, ниже и мягче кости."""
    t = t_axis(length)
    body = np.sin(2 * np.pi * f0 * t) * np.exp(-t / 0.03) + 0.4 * np.sin(2 * np.pi * f0 * 2.3 * t) * np.exp(-t / 0.012)
    return finish(wood(length, 1.0) + 0.6 * body, 0.6)


def rattle(hit, gaps=((0.0, 1.0), (0.05, 0.5), (0.085, 0.28))):
    """Докатился: два-три коротких перестука."""
    track = np.zeros(int(0.36 * RATE))
    for at, strength in gaps:
        place(track, strength * hit(), at)
    return finish(track, 0.5)


def ice_hit(f0, length=0.3):
    """Ледяной кубик о стол: звонкий стеклянный «цок» - высокие неровные призвуки гаснут быстро,
    под ними - лёгкий хруст и тихий стук о сукно."""
    ring = metal(length, f0, [1.0, 2.32, 3.86, 5.41], [1.0, 0.55, 0.32, 0.18], [0.07, 0.05, 0.035, 0.025])
    t = t_axis(length)
    crunch = highpass(rng.standard_normal(len(t)), 4500) * np.exp(-t / 0.004) * (0.6 + 0.4 * rng.random(len(t)))
    return finish(0.35 * wood(length, 0.6) + 0.5 * ring + 0.3 * crunch, 0.6)


def ornament_pop():
    """Лопнул ёлочный шарик: тонкий стеклянный «дзынь» и россыпь звона осколков."""
    track = np.zeros(int(0.45 * RATE))
    place(track, 0.9 * metal(0.3, 4200, [1.0, 1.47, 2.13, 2.9], [1.0, 0.7, 0.45, 0.3], [0.05, 0.04, 0.03, 0.02]), 0.0)
    for _ in range(9):                                           # осколки звенят вразнобой
        at = rng.uniform(0.03, 0.3)
        f0 = rng.uniform(5200, 8200)
        place(track, rng.uniform(0.15, 0.35) * metal(0.08, f0, [1.0, 1.6], [1.0, 0.5], [0.015, 0.01]), at)
    return finish(track, 0.5)


def round_in():
    """Патрон входит в гнездо барабана: короткий металлический щелчок с притиром."""
    t = t_axis(0.09)
    slide = highpass(rng.standard_normal(len(t)), 3500) * np.exp(-t / 0.02) * 0.25
    snap = metal(0.09, 3900, [1.0, 2.2], [1.0, 0.4], [0.01, 0.006])
    return finish(slide + snap, 0.45)


def sand_rake():
    """Грабли по песку: шуршание с крупинками, нарастает и стихает."""
    t = t_axis(0.42)
    hiss = lowpass(highpass(rng.standard_normal(len(t)), 700), 4200)
    grains = (rng.random(len(t)) < 0.012) * rng.standard_normal(len(t))
    grains = highpass(grains, 2500) * 2.5
    envelope = np.sin(np.pi * t / t[-1]) ** 1.5
    return finish((0.8 * hiss + grains) * envelope, 0.32)


def toggle(up=True):
    """Тумблер: пружина перескакивает - звонкий металлический щелчок с глухим упором."""
    t = t_axis(0.12)
    snap = metal(0.12, 4300 if up else 3700, [1.0, 1.9, 3.1], [1.0, 0.5, 0.25], [0.008, 0.005, 0.003])
    thud = np.sin(2 * np.pi * (330 if up else 260) * t) * np.exp(-t / 0.012)
    track = np.zeros(len(t) + int(0.02 * RATE))
    place(track, 0.35 * highpass(rng.standard_normal(len(t)), 2000) * np.exp(-t / 0.003), 0.0)   # сдвинул рычаг
    place(track, snap + 0.6 * thud, 0.012)
    return finish(track, 0.55)


def guard_open():
    """Откинул защитную крышку: лёгкий пластиковый щелчок петли."""
    t = t_axis(0.1)
    click = highpass(rng.standard_normal(len(t)), 1500) * np.exp(-t / 0.006)
    knock = np.sin(2 * np.pi * 520 * t) * np.exp(-t / 0.02)
    return finish(click + 0.5 * knock, 0.4)


def water_skip(f0=900):
    """Камень шлёпнул по воде и отскочил: короткий шлепок с булькающим «плип» вверх."""
    t = t_axis(0.16)
    slap = lowpass(rng.standard_normal(len(t)), 2500) * np.exp(-t / 0.012)
    plip = np.sin(2 * np.pi * (f0 + 2400 * t) * t) * np.exp(-t / 0.035)
    return finish(0.8 * slap + 0.5 * plip, 0.45)


def water_plunk():
    """Камень ушёл под воду: глухой «бульк» с пузырями."""
    t = t_axis(0.5)
    gloop = np.sin(2 * np.pi * (180 + 520 * np.exp(-t / 0.05)) * t) * np.exp(-t / 0.12)
    splash = lowpass(rng.standard_normal(len(t)), 1800) * np.exp(-t / 0.05)
    track = np.zeros(len(t))
    place(track, 0.9 * gloop + 0.6 * splash, 0.0)
    for at in (0.12, 0.19, 0.27):
        tb = t_axis(0.05)
        place(track, 0.25 * np.sin(2 * np.pi * rng.uniform(700, 1100) * tb) * np.exp(-tb / 0.012), at)
    return finish(track, 0.5)


def page_turn():
    """Перелистнули страницу: сухой шелест бумаги - нарастает и стихает, без щелчка."""
    seconds = 0.42
    t = t_axis(seconds)
    noise = highpass(lowpass(rng.standard_normal(len(t)), 5200), 700)
    swell = np.sin(np.pi * np.clip(t / seconds, 0, 1)) ** 1.6
    flutter = 0.75 + 0.25 * np.sin(2 * np.pi * (18 + 30 * t) * t)
    crisp = highpass(rng.standard_normal(len(t)), 3500) * np.exp(-((t - 0.3) / 0.03) ** 2) * 0.35
    return finish(noise * swell * flutter + crisp, 0.32)


if __name__ == "__main__":
    for i, f0 in enumerate((2750, 3080, 3420, 2900), 1):
        save(f"die_hit_{i}.wav", die_hit(f0))
    save("die_settle.wav", die_settle())
    save("coin_flick.wav", coin_flick())
    save("coin_land.wav", coin_land())
    save("drum_spin.wav", drum_spin())        # новые - после старых, чтобы старые звучали как раньше
    save("trigger_click.wav", trigger_click())
    save("bang.wav", bang())
    save("pop.wav", pop())
    save("ball_bounce.wav", ball_bounce())
    for i, f0 in enumerate((3100, 3350, 2950), 1):
        save(f"type_{i}.wav", type_key(f0))
    save("type_space.wav", type_space())
    save("type_return.wav", type_return())
    save("chime.wav", chime())
    save("spinner.wav", spinner())
    for i, f0 in enumerate((1750, 1980, 1620), 1):
        save(f"bone_hit_{i}.wav", bone_hit(f0))
    for i, f0 in enumerate((210, 245, 190), 1):
        save(f"oak_hit_{i}.wav", oak_hit(f0))
    save("bone_settle.wav", rattle(lambda: bone_hit(1850, 0.12)))
    save("oak_settle.wav", rattle(lambda: oak_hit(230, 0.14)))
    save("round_in.wav", round_in())
    save("sand_rake.wav", sand_rake())
    save("toggle_up.wav", toggle(True))
    save("toggle_down.wav", toggle(False))
    save("guard_open.wav", guard_open())
    for i, f0 in enumerate((850, 1000, 1150), 1):
        save(f"water_skip_{i}.wav", water_skip(f0))
    save("water_plunk.wav", water_plunk())
    save("page_turn.wav", page_turn())
    for i, f0 in enumerate((2600, 2900, 3250), 1):          # лёд - последним: старые звуки не меняются
        save(f"ice_hit_{i}.wav", ice_hit(f0))
    save("ice_settle.wav", rattle(lambda: ice_hit(3100, 0.16)))
    save("ornament_pop.wav", ornament_pop())                 # пупырка из ёлочных шариков
    print("готово:", ", ".join(sorted(p.name for p in OUT.glob("*.wav"))))
