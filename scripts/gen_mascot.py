#!/usr/bin/env python3
"""Generate H-CLI mascot sprite — 48×48 chibi anime girl pixel art.

Run once to create mascot.png (+ variants), then delete this script.
Authentic GBA/DS-era chibi: oversized head, huge sparkly eyes, fluffy hair.
Uses H-CLI theme palette: pinks, purples, peach skin tones.
"""

from PIL import Image

# ── Palette (RGBA) ──────────────────────────────────────────────────────────
T  = (0, 0, 0, 0)             # transparent
BK = (40, 25, 45, 255)        # outline — dark plum
OL = (80, 40, 70, 255)        # soft outline (anti-alias edge)

H1 = (255, 110, 175, 255)     # hair — hot pink main
H2 = (230, 65, 140, 255)      # hair — deep pink shadow
H3 = (255, 170, 210, 255)     # hair — highlight
H4 = (255, 200, 225, 255)     # hair — specular highlight

S1 = (255, 218, 190, 255)     # skin — light peach
S2 = (245, 195, 165, 255)     # skin — mid shadow
S3 = (230, 175, 145, 255)     # skin — deep shadow

BL = (255, 170, 190, 255)     # blush circles

E1 = (50, 35, 60, 255)        # eye — outline/pupil dark
E2 = (130, 105, 210, 255)     # eye — iris mid purple
E3 = (165, 145, 235, 255)     # eye — iris light purple
EW = (255, 255, 255, 255)     # eye — white / highlight sparkle

D1 = (255, 130, 210, 255)     # dress — main pink
D2 = (220, 95, 175, 255)      # dress — shadow
D3 = (255, 180, 230, 255)     # dress — highlight / ribbon
D4 = (255, 210, 240, 255)     # dress — light trim

W  = (255, 255, 255, 255)     # white (collar, eye whites)
RB = (255, 60, 120, 255)      # ribbon / bow accent

SK = (80, 55, 70, 255)        # shoe dark
SL = (130, 90, 110, 255)      # shoe light

# ── 48×48 pixel grid ───────────────────────────────────────────────────────
# Legend:
#   .=transparent  K=outline(BK)  O=soft-outline(OL)
#   1=hair-main  2=hair-shadow  3=hair-highlight  4=hair-specular
#   s=skin  a=skin-shadow  b=skin-deep-shadow
#   B=blush
#   E=eye-outline  e=eye-iris-mid  f=eye-iris-light  W=eye-white/sparkle
#   d=dress  D=dress-shadow  r=dress-highlight  t=dress-trim
#   w=white(collar)  R=ribbon/bow
#   h=shoe-dark  l=shoe-light
#   m=mouth

# fmt: off
PIXELS = [
    #0         1         2         3         4
    #0123456789012345678901234567890123456789012345678
    "................................................",  # 0
    "...................KKKKKKKK.....................",  # 1
    "................KKK11111111KKK.................",  # 2
    "..............KK1111111111111KK................",  # 3
    ".............K111133333331111KK................",  # 4
    "............K11113344443311111KK...............",  # 5
    "...........K1111334444433111111K...............",  # 6
    "..........K211133344443311111112K..............",  # 7
    ".........K22111333333333111111122K.............",  # 8
    "........K221113333333333111111122K.............",  # 9
    "........K2211133333333331111112K...............",  # 10
    ".......K22111111111111111111112K...............",  # 11
    ".......K2211111ssssssssss111112K...............",  # 12
    "......K221111sssssssssssss11112K...............",  # 13
    "......K22111ssssssssssssssss112K...............",  # 14
    "......K2111sssssssssssssssss12KK...............",  # 15
    ".....K2211ssEEEsssssssEEEsss12K...............",  # 16
    ".....K2211sEeeeEsssssEeeeEss12K...............",  # 17
    ".....K211ssEefeEsssssEefeEsss1K...............",  # 18
    ".....K211ssEeWfEsssssEeWfEsss1K...............",  # 19
    ".....K211ssEeeeEsssssEeeeEsss1K...............",  # 20
    ".....K211sssEEEssBBsssEEEssss1K...............",  # 21
    ".....K211ssssssssBBsssssssssssK...............",  # 22
    "......K21sssssssssmssssssssss1K...............",  # 23
    "......K211ssssssssssssssssss1KK...............",  # 24
    "......K2111sssssssssssssss112K................",  # 25
    ".......K21111sssssssssss1112K.................",  # 26
    ".......KK211111sssssss11112KK.................",  # 27
    "........KK2111111111111112KK..................",  # 28
    ".........KKKK21111111112KKK...................",  # 29
    "...........K2KKKsssssKKK12K...................",  # 30
    "..........K21sswwwwwwwwss12K..................",  # 31
    ".........KK1sswwddddddwwss1K.................",  # 32
    ".........K1ssddddddddddddss1K................",  # 33
    "........KK1sdddddrrrdddddsssK................",  # 34
    "........K1ssddddrrrrrddddsssK................",  # 35
    "........K1ssddDDrrrrrddddsssK................",  # 36
    "........K1ssdDDDdrrrdDDddss1K.................",  # 37
    ".........K1ssdDDdddddDDdss1K.................",  # 38
    ".........K1sssdddddddddsss1K.................",  # 39
    "..........K1sssddddddddsss1K.................",  # 40
    "..........KK1ssssddddssss1KK.................",  # 41
    "...........K11sssssssssss11K..................",  # 42
    "...........KK1ssss..ssss1KK..................",  # 43
    "............K1sss....sss1K....................",  # 44
    "............Kkhh......hhkK....................",  # 45
    ".............KK........KK.....................",  # 46
    "................................................",  # 47
]
# fmt: on

CHARMAP = {
    ".": T,
    "K": BK,     # hard outline
    "O": OL,     # soft outline
    "1": H1,     # hair main
    "2": H2,     # hair shadow
    "3": H3,     # hair highlight
    "4": H4,     # hair specular
    "s": S1,     # skin
    "a": S2,     # skin shadow
    "b": S3,     # skin deep shadow
    "B": BL,     # blush
    "E": E1,     # eye outline
    "e": E2,     # eye iris mid
    "f": E3,     # eye iris light
    "W": EW,     # eye white / sparkle
    "d": D1,     # dress
    "D": D2,     # dress shadow
    "r": D3,     # dress highlight / ribbon
    "t": D4,     # dress trim
    "w": W,      # white collar
    "R": RB,     # ribbon bow
    "h": SK,     # shoe dark
    "k": SL,     # shoe light / ankle
    "l": SL,     # shoe light
    "m": (235, 110, 130, 255),  # mouth — soft pink-red
}


def make_image(pixels: list) -> Image.Image:
    """Convert pixel grid to RGBA Image."""
    img = Image.new("RGBA", (48, 48), T)
    for y, row in enumerate(pixels):
        for x, ch in enumerate(row):
            img.putpixel((x, y), CHARMAP.get(ch, T))
    return img


def make_blink(pixels: list) -> list:
    """Create blink frame — close the eyes (replace iris rows with skin)."""
    out = []
    for i, row in enumerate(pixels):
        if i in (17, 18, 19, 20):
            # Replace eye interior with closed-eye line
            new = list(row)
            for j, ch in enumerate(new):
                if ch in ("e", "f", "W"):
                    new[j] = "s"
            out.append("".join(new))
        else:
            out.append(row)
    return out


def make_heart(pixels: list) -> list:
    """Create heart frame — add a floating heart to the right of head."""
    out = []
    for i, row in enumerate(pixels):
        if i == 8:
            # Place a small heart shape at the right side
            new = list(row)
            # Heart at columns 38-42 area (in the transparent space)
            heart_pixels = {
                (38, 7): RB, (39, 7): RB, (41, 7): RB, (42, 7): RB,
                (37, 8): RB, (38, 8): RB, (39, 8): RB, (40, 8): RB,
                (41, 8): RB, (42, 8): RB, (43, 8): RB,
            }
            for (hx, hy), _ in heart_pixels.items():
                if hy == i and 0 <= hx < 48:
                    new[hx] = "R"
            out.append("".join(new))
        elif i == 7:
            new = list(row)
            for hx in [38, 39, 41, 42]:
                if 0 <= hx < 48:
                    new[hx] = "R"
            out.append("".join(new))
        elif i == 9:
            new = list(row)
            for hx in [38, 39, 40, 41, 42]:
                if 0 <= hx < 48:
                    new[hx] = "R"
            out.append("".join(new))
        elif i == 10:
            new = list(row)
            for hx in [39, 40, 41]:
                if 0 <= hx < 48:
                    new[hx] = "R"
            out.append("".join(new))
        elif i == 11:
            new = list(row)
            for hx in [40]:
                if 0 <= hx < 48:
                    new[hx] = "R"
            out.append("".join(new))
        else:
            out.append(row)
    return out


def generate():
    base = make_image(PIXELS)

    # Frame 0: idle (scale 2× for crisp rendering)
    idle_2x = base.resize((96, 96), Image.NEAREST)
    idle_2x.save("mascot.png")
    print("Saved mascot.png (96×96, idle)")

    base.save("mascot_48.png")
    print("Saved mascot_48.png (48×48, idle)")

    # Frame 1: blink
    blink = make_image(make_blink(PIXELS))
    blink_2x = blink.resize((96, 96), Image.NEAREST)
    blink_2x.save("mascot_blink.png")
    print("Saved mascot_blink.png (96×96, blink)")

    # Frame 2: heart
    heart = make_image(make_heart(PIXELS))
    heart_2x = heart.resize((96, 96), Image.NEAREST)
    heart_2x.save("mascot_heart.png")
    print("Saved mascot_heart.png (96×96, heart)")


if __name__ == "__main__":
    generate()
