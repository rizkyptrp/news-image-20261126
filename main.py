#!/usr/bin/env python3
"""news-image-20261126: draws a newspaper front page summing up the world
news of Thursday 26 November 2026 as a deterministic 1024x1024 PNG.

Stdlib only, no network, no randomness, no timestamps: two runs write
byte-identical output. The image is drawn, not copied: every story on it
was verified against reporting dated 26 November 2026 (see README.md).
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------------------
# 5x7 bitmap font, written out by hand for this entry (A-Z, a-z, 0-9, punct).
# Each glyph is 7 rows; each row is a 5-bit number, bit 4 = leftmost pixel.
# ---------------------------------------------------------------------------
FONT = {
    'A': (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'B': (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    'C': (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    'D': (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    'E': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    'F': (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    'G': (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    'H': (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    'I': (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    'J': (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    'K': (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    'L': (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    'M': (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    'N': (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    'O': (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'P': (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    'Q': (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    'R': (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    'S': (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    'T': (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    'U': (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    'V': (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    'W': (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    'X': (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    'Y': (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    'Z': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    'a': (0x00, 0x00, 0x0E, 0x01, 0x0F, 0x11, 0x0F),
    'b': (0x10, 0x10, 0x16, 0x19, 0x11, 0x11, 0x1E),
    'c': (0x00, 0x00, 0x0E, 0x10, 0x10, 0x11, 0x0E),
    'd': (0x01, 0x01, 0x0D, 0x13, 0x11, 0x11, 0x0F),
    'e': (0x00, 0x00, 0x0E, 0x11, 0x1F, 0x10, 0x0E),
    'f': (0x06, 0x08, 0x08, 0x1E, 0x08, 0x08, 0x08),
    'g': (0x00, 0x0F, 0x11, 0x11, 0x0F, 0x01, 0x0E),
    'h': (0x10, 0x10, 0x16, 0x19, 0x11, 0x11, 0x11),
    'i': (0x04, 0x00, 0x0C, 0x04, 0x04, 0x04, 0x0E),
    'j': (0x02, 0x00, 0x06, 0x02, 0x02, 0x12, 0x0C),
    'k': (0x10, 0x10, 0x12, 0x14, 0x18, 0x14, 0x12),
    'l': (0x0C, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    'm': (0x00, 0x00, 0x1A, 0x15, 0x15, 0x15, 0x15),
    'n': (0x00, 0x00, 0x16, 0x19, 0x11, 0x11, 0x11),
    'o': (0x00, 0x00, 0x0E, 0x11, 0x11, 0x11, 0x0E),
    'p': (0x00, 0x00, 0x1E, 0x11, 0x11, 0x1E, 0x10),
    'q': (0x00, 0x00, 0x0D, 0x13, 0x11, 0x0F, 0x01),
    'r': (0x00, 0x00, 0x16, 0x19, 0x10, 0x10, 0x10),
    's': (0x00, 0x00, 0x0F, 0x10, 0x0E, 0x01, 0x1E),
    't': (0x08, 0x08, 0x1E, 0x08, 0x08, 0x09, 0x06),
    'u': (0x00, 0x00, 0x11, 0x11, 0x11, 0x13, 0x0D),
    'v': (0x00, 0x00, 0x11, 0x11, 0x11, 0x0A, 0x04),
    'w': (0x00, 0x00, 0x11, 0x15, 0x15, 0x15, 0x0A),
    'x': (0x00, 0x00, 0x11, 0x0A, 0x04, 0x0A, 0x11),
    'y': (0x00, 0x00, 0x11, 0x11, 0x0F, 0x01, 0x0E),
    'z': (0x00, 0x00, 0x1F, 0x02, 0x04, 0x08, 0x1F),
    '0': (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    '1': (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    '2': (0x0E, 0x11, 0x01, 0x06, 0x08, 0x10, 0x1F),
    '3': (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    '4': (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    '5': (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    '6': (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    '7': (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    '8': (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    '9': (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    ' ': (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00),
    '.': (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    ',': (0x00, 0x00, 0x00, 0x00, 0x0C, 0x04, 0x08),
    ':': (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00),
    ';': (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x04, 0x08),
    '!': (0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04),
    '?': (0x0E, 0x11, 0x01, 0x02, 0x04, 0x00, 0x04),
    "'": (0x04, 0x04, 0x08, 0x00, 0x00, 0x00, 0x00),
    '"': (0x0A, 0x0A, 0x00, 0x00, 0x00, 0x00, 0x00),
    '-': (0x00, 0x00, 0x00, 0x0E, 0x00, 0x00, 0x00),
    '(': (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ')': (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    '/': (0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10),
    '%': (0x19, 0x19, 0x02, 0x04, 0x08, 0x13, 0x13),
    '&': (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    '$': (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    '#': (0x0A, 0x0A, 0x1F, 0x0A, 0x1F, 0x0A, 0x0A),
    '@': (0x0E, 0x11, 0x17, 0x15, 0x16, 0x10, 0x0E),
    '+': (0x00, 0x04, 0x04, 0x1F, 0x04, 0x04, 0x00),
    '*': (0x00, 0x04, 0x15, 0x0E, 0x15, 0x04, 0x00),
    '=': (0x00, 0x00, 0x1F, 0x00, 0x1F, 0x00, 0x00),
    '<': (0x02, 0x04, 0x08, 0x10, 0x08, 0x04, 0x02),
    '>': (0x08, 0x04, 0x02, 0x01, 0x02, 0x04, 0x08),
    '_': (0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x1F),
    '[': (0x0E, 0x08, 0x08, 0x08, 0x08, 0x08, 0x0E),
    ']': (0x0E, 0x02, 0x02, 0x02, 0x02, 0x02, 0x0E),
    '~': (0x00, 0x00, 0x0E, 0x15, 0x00, 0x00, 0x00),
    '^': (0x04, 0x0A, 0x11, 0x00, 0x00, 0x00, 0x00),
    '\\': (0x10, 0x10, 0x08, 0x04, 0x02, 0x01, 0x01),
    '|': (0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    '{': (0x06, 0x08, 0x08, 0x0E, 0x08, 0x08, 0x06),
    '}': (0x0C, 0x02, 0x02, 0x1E, 0x02, 0x02, 0x0C),
    '\u2022': (0x00, 0x00, 0x0E, 0x0E, 0x0E, 0x00, 0x00),  # bullet
}

# ---------------------------------------------------------------------------
# Canvas: RGB bytearray, origin top-left.
# ---------------------------------------------------------------------------
WHITE = (250, 248, 240)   # newsprint off-white
BLACK = (18, 18, 18)      # ink
RED = (178, 34, 34)       # masthead red
DARKRED = (139, 0, 0)
GREY = (90, 90, 90)
LIGHTGREY = (225, 222, 214)


class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                j = base + (xx - x0) * 3
                self.px[j], self.px[j + 1], self.px[j + 2] = c

    def hline(self, x, y, w, c, thick=1):
        self.rect(x, y, w, thick, c)

    def circle(self, cx, cy, r, c):
        # Filled circle via scanlines (deterministic integer math).
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.rect(cx - dx, cy + dy, 2 * dx + 1, 1, c)

    def ring(self, cx, cy, r, c, thick=2):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            inner = int(((r - thick) ** 2 - dy * dy) ** 0.5) if abs(dy) < r - thick else 0
            self.rect(cx - dx, cy + dy, dx - inner + 1, 1, c)
            self.rect(cx + inner, cy + dy, dx - inner + 1, 1, c)

    def text(self, x, y, s, scale, c):
        """Draw string s with top-left at (x, y). Returns width used."""
        cx = x
        for ch in s:
            glyph = FONT.get(ch)
            if glyph is None:
                glyph = FONT['?']
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits & (1 << (4 - col)):
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, c)
            cx += 6 * scale
        return cx - x

    def text_w(self, s, scale):
        return len(s) * 6 * scale - scale

    def text_center(self, y, s, scale, c, x0=0, x1=None):
        if x1 is None:
            x1 = self.w
        w = self.text_w(s, scale)
        self.text(x0 + (x1 - x0 - w) // 2, y, s, scale, c)


def wrap(text, max_chars):
    """Greedy word wrap to lines of at most max_chars characters."""
    words = text.split(' ')
    lines, cur = [], ''
    for wd in words:
        nxt = wd if not cur else cur + ' ' + wd
        if len(nxt) <= max_chars:
            cur = nxt
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------------------
# Minimal deterministic PNG encoder (RGB, filter 0, zlib level 9).
# ---------------------------------------------------------------------------
def _chunk(kind, data):
    out = struct.pack('>I', len(data)) + kind + data
    out += struct.pack('>I', zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(canvas):
    ihdr = struct.pack('>IIBBBBB', canvas.w, canvas.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    row_bytes = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)
        raw += canvas.px[y * row_bytes:(y + 1) * row_bytes]
    png = b'\x89PNG\r\n\x1a\n'
    png += _chunk(b'IHDR', ihdr)
    png += _chunk(b'IDAT', zlib.compress(bytes(raw), 9))
    png += _chunk(b'IEND', b'')
    return png


# ---------------------------------------------------------------------------
# Stories. Every headline below was verified against reporting dated
# Thursday 26 November 2026 (AP, BBC, The Guardian, Reuters wires, Al
# Jazeera, Sharecast/AP market wires). Headlines are kept short so each
# fits one line in its column; numbers are the lowest figure all sources
# agreed on. Sources per story are listed in README.md.
# ---------------------------------------------------------------------------
LEAD_HEAD = ["US UNVEILS SWEEPING NEW", "TARIFFS ON 14 PARTNERS"]
LEAD_DECK = ("Trump targets China, EU, Japan and Brazil over subsidised "
             "factories")

# (section title, [headlines]) — columns are balanced by the layout code.
SECTIONS = [
    ("AMERICAS", [
        "100TH MACY'S PARADE MOVED TO SATURDAY",
        "IOWA BOMB-CHEMICAL BLAST 'A SUCCESS'",
        "VANCE: HUANG NEEDS NO PARDON",
        "TRUMP ACCOUNTS TRADED NVIDIA 44 TIMES",
        "FOUR-TIME MVP RODGERS RELEASED",
        "COLOMBIA FREES HOSTAGES AFTER SIEGE",
        "KING TIDES THREATEN CALIFORNIA COAST",
        "WOLBACHIA CUTS BRAZIL VIRUSES 68%",
    ]),
    ("EUROPE & UKRAINE", [
        "RUSSIA LOST NEARLY 500,000 IN WAR",
        "UKRAINE CLAIMS FIVE RUSSIAN JETS HIT",
        "RUSSIAN STRIKES KILL FIVE, CUT POWER",
        "UKRAINE DRONE KILLS ONE IN SAMARA",
        "MERZ: RUSSIA THREATENS EUROPE",
        "34 NATIONS: END RIOT-GAS USE",
    ]),
    ("MIDDLE EAST", [
        "JUDGES URGE DROPPING NETANYAHU CHARGES",
        "KNESSET BACKS OCTOBER 7 PROBE",
        "EISENKOT CLOSER TO OUSTING NETANYAHU",
        "LIKUD APPEALS RESULTS IN 120 SEATS",
        "HOUTHIS CLAIM SAUDI REFINERY HIT",
        "HOUTHIS THREATEN SAUDI RED SEA PORTS",
        "SAUDI INTERCEPTS MISSILES OVER RIYADH",
        "COALITION STRIKES HODEIDAH PORT",
        "SEVEN KILLED IN ISRAELI GAZA STRIKES",
        "TEHRAN ACCUSES US OF AI-DRIVEN ATTACKS",
        "IRAN GUARD: READY TO REPEL ATTACK",
        "WINTER RAINS THREATEN GAZA SHELTERS",
    ]),
    ("ASIA-PACIFIC", [
        "CHINA PROBES SHANGHAI CHIEF CHEN",
        "TAIWAN STOCKS PLUNGE 1,927 POINTS",
        "NT DOLLAR WEAKENS PAST 33 PER DOLLAR",
        "US PROPOSES 15% TARIFF ON TAIWAN GOODS",
        "INDIA DENIES EXCESS CAPACITY",
        "AUSTRALIAN SENATOR JOINS ONE NATION",
        "NORTH KOREA EXPELS SWISS DIPLOMAT",
        "KIM WANTS MORE TACTICAL NUCLEAR ARMS",
        "US UNVEILS F-15EX FIGHTERS AT KADENA",
        "INDIA MARKS CONSTITUTION DAY",
        "BANGLADESH OFFERS 36% GARMENT PAY RISE",
        "INDIANS HURT IN SAUDI ATTACK GO HOME",
    ]),
    ("AFRICA", [
        "31 KILLED IN CAIRO FUEL TANKER FIRE",
        "GUNMEN KILL 30 IN NIGER STATE",
        "FIVE MEXICANS HELD OVER $227M METH LAB",
        "RSF DRONES KILL 19 IN SUDAN'S DAMAZIN",
        "LIBYAN OFFICERS DIE IN WARSHIP STRIKE",
        "BIOVAC TO BOOST VACCINE OUTPUT",
    ]),
    ("MARKETS, TECH & SCIENCE", [
        "ASIA STOCKS SLUMP IN AI SELL-OFF",
        "US STOCKS FALL AS AI FEARS INTENSIFY",
        "AI BUBBLE COULD TOP DOT-COM CRASH",
        "US TIGHTENS AI CHIP ACCESS RULES",
        "US BLACKLISTS ALIBABA SINGAPORE UNIT",
        "ASTEROID CRATER IS STADIUM-SIZED",
        "FED SEES MODEST GROWTH, PRICE PRESSURE",
    ]),
    ("SPORT & CULTURE", [
        "ANDY TAYLOR OF DURAN DURAN DIES AT 65",
        "JOLIE AND PITT SETTLE WINERY BATTLE",
        "PALESTINIAN JOURNALIST WINS RORY PECK",
    ]),
]

FOOTER_MARKETS = ("MARKETS: BRENT ABOVE $94  \u2022  GOLD +1.6%  \u2022  "
                  "DOW +0.3%  \u2022  NIKKEI -2.8%")
FOOTER_SPORT = ("THANKSGIVING NFL: BEARS AT LIONS  \u2022  EAGLES AT COWBOYS"
                "  \u2022  CHIEFS AT BILLS")

STORY_COUNT = 1 + sum(len(h) for _, h in SECTIONS)


# ---------------------------------------------------------------------------
# Layout.
# ---------------------------------------------------------------------------
def draw_page():
    c = Canvas(W, H, WHITE)
    mx = 28                      # page margin
    col_w = (W - 2 * mx - 24) // 2
    col_x = [mx, mx + col_w + 24]

    # --- masthead ------------------------------------------------------
    # Small globe at the left of the masthead: blue disc, white meridians.
    gx, gy, gr = 62, 52, 30
    c.circle(gx, gy, gr, (31, 93, 140))
    c.ring(gx, gy, gr, BLACK, 2)
    c.hline(gx - gr, gy, 2 * gr, WHITE, 2)
    c.rect(gx - 2, gy - gr, 4, 2 * gr, WHITE)
    for k in (-1, 1):
        c.rect(gx + k * 16 - 1, gy - gr + 4, 2, 2 * gr - 8, WHITE)
    c.text_center(14, "THE WORLD TODAY", 7, RED, x0=110, x1=W - mx)
    c.hline(mx, 96, W - 2 * mx, BLACK, 3)
    c.hline(mx, 102, W - 2 * mx, BLACK, 1)

    # --- date banner ---------------------------------------------------
    c.rect(mx, 110, W - 2 * mx, 38, BLACK)
    c.text(mx + 14, 118, "THURSDAY 26 NOVEMBER 2026", 3, WHITE)
    right = "WORLD NEWS  \u2022  %d STORIES" % STORY_COUNT
    c.text(W - mx - 14 - c.text_w(right, 2), 124, right, 2, WHITE)

    # --- lead story ----------------------------------------------------
    y = 162
    c.text(mx, y, "TARIFFS SHAKE WORLD TRADE", 2, RED)
    y += 22
    for line in LEAD_HEAD:
        c.text(mx, y, line, 4, BLACK)
        y += 30
    c.text(mx, y, LEAD_DECK, 2, GREY)
    y += 20
    c.hline(mx, y, W - 2 * mx, BLACK, 2)
    y += 10

    # --- story grid: two columns, sections balanced by story count ----
    # Split sections into two columns with near-equal story totals.
    left, right = [], []
    ln = rn = 0
    for sec in SECTIONS:
        if ln <= rn:
            left.append(sec)
            ln += len(sec[1])
        else:
            right.append(sec)
            rn += len(sec[1])
    grid_top = y
    for col, secs in ((0, left), (1, right)):
        x = col_x[col]
        cy = grid_top
        for title, heads in secs:
            c.rect(x, cy, col_w, 24, BLACK)
            c.text(x + 8, cy + 5, title, 2, WHITE)
            cy += 24 + 6
            for head in heads:
                lines = wrap(head, (col_w - 12) // 12)
                for ln_ in lines:
                    c.text(x + 2, cy, ln_, 2, BLACK)
                    cy += 14
                cy += 4
            cy += 8
        # column rule between the two columns
        if col == 0:
            c.rect(mx + col_w + 12, grid_top, 1, cy - grid_top, LIGHTGREY)

    # --- footer --------------------------------------------------------
    fy = 962
    c.hline(mx, fy, W - 2 * mx, BLACK, 2)
    c.text(mx, fy + 10, FOOTER_MARKETS, 2, BLACK)
    c.text(mx, fy + 30, FOOTER_SPORT, 2, BLACK)
    c.hline(mx, fy + 50, W - 2 * mx, BLACK, 1)
    return c


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    data = encode_png(draw_page())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    # Gate self-check: PNG, <= 1 MiB, <= 1024x1024.
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    assert len(data) <= 1048576, "over 1 MiB: %d bytes" % len(data)
    print("wrote %s (%d bytes, %dx%d, %d stories)"
          % (path, len(data), W, H, STORY_COUNT))


if __name__ == "__main__":
    main()

