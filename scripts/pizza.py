#!/usr/bin/env python3
"""
Contribution Pizza: a year of GitHub contributions served as a pixel-art pizza.

  - 12 slices = 12 months of the current calendar year (Jan at the top, clockwise)
  - every topping = one day
      plain cheese (oregano speck)  0 commits
      basil leaf                    1-2
      mushroom                      3-5
      pepperoni                     6-9
      spicy pepperoni               10+
  - days that have not happened yet stay plain cheese, so the pizza fills up over the year
  - each month's slice lifts out in turn (CSS animation), steam keeps rising

Outputs pizza-light.svg and pizza-dark.svg, both on a gingham tablecloth (bright and dimmed).

Usage:
  GITHUB_TOKEN=xxx python pizza.py --user nnnnnoooooeeeee --out dist
  python pizza.py --demo --out dist         # random data, no network
Standard library only.
"""
import argparse
import datetime as dt
import json
import math
import os
import random
import urllib.request

W, H = 300, 240
CX, CY, PR = 150, 120, 88
SL = math.pi / 6
CYCLE = 36  # seconds for all 12 slices to take their turn
WIB = dt.timezone(dt.timedelta(hours=7))
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

# ------------------------------------------------------------------ data

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
  }
}
"""


def fetch(user, token, year):
    body = json.dumps({"query": QUERY, "variables": {
        "login": user,
        "from": f"{year}-01-01T00:00:00Z",
        "to": f"{year}-12-31T23:59:59Z",
    }}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "contribution-pizza"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GitHub API error: {data['errors']}")
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    counts = {d["date"]: d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]}
    return counts, cal["totalContributions"]


def demo(year, today, seed=2026):
    rnd = random.Random(seed)
    counts, burst = {}, 0
    d = dt.date(year, 1, 1)
    while d <= today:
        if d.weekday() == 0 and rnd.random() < .12:
            burst = 4
        weekend = d.weekday() >= 5
        p = .05 if rnd.random() < .04 else (.45 if weekend else .8)
        v = round(rnd.random() ** 1.6 * 12) + 1 if rnd.random() < p else 0
        if burst and v:
            v += 6
            burst -= 1
        counts[d.isoformat()] = v
        d += dt.timedelta(days=1)
    return counts, sum(counts.values())


def months_of(counts, year, today):
    out = []
    for m in range(12):
        days, d = [], dt.date(year, m + 1, 1)
        while d.month == m + 1:
            days.append(-1 if d > today else counts.get(d.isoformat(), 0))
            d += dt.timedelta(days=1)
        out.append(days)
    return out


# ------------------------------------------------------------------ pixel helpers

def jsround(v):
    return math.floor(v + .5)


def hsh(x, y):
    v = math.sin(x * 127.1 + y * 311.7) * 43758.5453
    return v - math.floor(v)


def level(c):
    return 0 if c <= 0 else 1 if c < 3 else 2 if c < 6 else 3 if c < 10 else 4


def angle_of(dx, dy):
    a = math.atan2(dx, -dy)
    return a + 2 * math.pi if a < 0 else a


class Grid:
    """Sparse pixel grid; `clip` decides which pixels may be painted."""

    def __init__(self, clip=None):
        self.px, self.clip = {}, clip

    def put(self, x, y, col):
        if self.clip is None or self.clip(x, y):
            self.px[(x, y)] = col

    def rect(self, col, x, y, w=1, h=1):
        x, y = jsround(x), jsround(y)
        for j in range(h):
            for i in range(w):
                self.put(x + i, y + j, col)

    def disc(self, x, y, r, col):
        for dy in range(-r, r + 1):
            w = jsround(math.sqrt(r * r - dy * dy + r * .6))
            self.rect(col, x - w, y + dy, w * 2 + 1, 1)

    def paths(self, **attrs):
        """Run-length encode each row into one <path> per colour."""
        by_col = {}
        rows = {}
        for (x, y), col in self.px.items():
            rows.setdefault(y, []).append((x, col))
        for y, items in rows.items():
            items.sort()
            sx, sc, prev = items[0][0], items[0][1], items[0][0]
            for x, col in items[1:] + [(None, None)]:
                if x is not None and x == prev + 1 and col == sc:
                    prev = x
                    continue
                by_col.setdefault(sc, []).append(f"M{sx} {y}h{prev - sx + 1}v1h-{prev - sx + 1}z")
                if x is not None:
                    sx, sc, prev = x, col, x
        extra = "".join(f' {k}="{v}"' for k, v in attrs.items())
        return "".join(f'<path fill="{c}"{extra} d="{"".join(d)}"/>' for c, d in by_col.items())


# ------------------------------------------------------------------ toppings

def pep(g, x, y, r, spicy=False):
    g.disc(x, y, r, "#9e2a20")
    g.disc(x, y, r - 1, "#c9402f")
    for a, b in ((-1, 0), (1, -1), (0, 1)):
        g.rect("#8a2017", x + a, y + b)
    g.rect("#ef7b6a", x - r + 2, y - r + 2)
    if spicy:
        g.rect("#ff6a1f", x + r + 1, y - r)
        g.rect("#ff6a1f", x - r - 1, y + r - 1)
        g.rect("#2f6b2a", x + r, y + r)


def mush(g, x, y):
    g.rect("#8d6e53", x - 3, y - 2, 6, 1)
    g.rect("#e6d5bb", x - 3, y - 1, 6, 2)
    g.rect("#d4bf9e", x - 2, y - 3, 4, 1)
    g.rect("#efe3cf", x - 1, y + 1, 2, 2)
    g.rect("#8d6e53", x - 1, y + 3, 2, 1)


def basil(g, x, y):
    g.rect("#2f6b2a", x - 2, y)
    g.rect("#3f8f3a", x - 1, y - 1, 3, 2)
    g.rect("#5cb85c", x, y - 2, 2, 1)
    g.rect("#2f6b2a", x, y)


def topping(g, x, y, lv):
    if lv == 4:
        pep(g, x, y, 4, True)
    elif lv == 3:
        pep(g, x, y, 3)
    elif lv == 2:
        mush(g, x, y)
    elif lv == 1:
        basil(g, x, y)
    else:
        g.rect("#7d8f2e", x, y)


def slots(k):
    """31 topping spots inside slice k, spread across 5 rings, in a scattered order."""
    rows = [(24, 3), (36, 5), (48, 6), (60, 8), (71, 9)]
    out = []
    for j, (rr, n) in enumerate(rows):
        mg = 6 / rr
        for m in range(n):
            a = k * SL + mg + (m + .5) / n * (SL - 2 * mg) + (hsh(k * 7 + j, m) - .5) * .05
            r2 = rr + (hsh(m, k + j) - .5) * 3
            out.append((CX + math.sin(a) * r2, CY - math.cos(a) * r2, hsh(k + m * 3, j * 5)))
    return sorted(out, key=lambda p: p[2])


# ------------------------------------------------------------------ slices

def build_slice(k, days):
    g = Grid()
    for y in range(CY - PR - 1, CY + PR + 1):
        for x in range(CX - PR - 1, CX + PR + 1):
            dx, dy = x - CX + .5, y - CY + .5
            r = math.hypot(dx, dy)
            if r > PR or r < 3:
                continue
            a = angle_of(dx, dy)
            if int(a // SL) != k:
                continue
            da = min(a - k * SL, (k + 1) * SL - a) * r
            if da < .9:
                continue
            h = hsh(x - CX + 90, y - CY + 90)
            light = math.cos(a + math.pi * .75)
            if r > 86:
                col = "#c3803f" if light > .2 else "#a8652e"
            elif r > 80.5:
                col = "#a5652d" if h < .12 else "#ecbd74" if r < 82 else "#e8ab5c" if light > .3 else "#d9984c"
            elif r > 77:
                col = "#f6d36b" if h < .45 else "#c8452f"
            else:
                col = "#e9a83a" if h < .02 else "#f2c14e" if h < .06 else "#f7d774"
            if da < 1.8 and r <= 80.5:
                col = "#e9b94f"
            g.px[(x, y)] = col

    a0, a1 = k * SL + .04, (k + 1) * SL - .04

    def clip(x, y):
        dx, dy = x - CX + .5, y - CY + .5
        return math.hypot(dx, dy) <= 78 and a0 <= angle_of(dx, dy) <= a1

    g.clip = clip
    spots = slots(k)
    for d, v in enumerate(days):
        if v >= 0 and d < len(spots):
            topping(g, spots[d][0], spots[d][1], level(v))
    return g


# ------------------------------------------------------------------ svg

def keyframes(name, k, prop, rest, lifted):
    s = k / 12 * 100
    pts = [(0, rest), (s, rest), (s + 1.2, lifted), (s + 6.8, lifted), (s + 8, rest), (100, rest)]
    body = "".join(f"{p:.2f}%{{{prop}:{v}}}" for p, v in pts)
    return f"@keyframes {name}{k}{{{body}}}"


def build_svg(months, total, year, user, theme, today):
    slices = [build_slice(k, months[k]) for k in range(12)]
    css = [".a{animation-duration:%ds;animation-iteration-count:infinite;animation-timing-function:ease-in-out}" % CYCLE,
           "@keyframes st{0%{transform:translateY(0);opacity:0}30%{opacity:.5}100%{transform:translateY(-110px);opacity:0}}",
           ".st{animation:st 5s linear infinite}",
           "@media (prefers-reduced-motion:reduce){.a,.st{animation:none}}"]
    out = []
    for k in range(12):
        a = (k + .5) * SL
        dx, dy = math.sin(a) * 11, -math.cos(a) * 11
        css.append(keyframes("p", k, "transform", "translate(0px,0px)", f"translate({dx:.1f}px,{dy:.1f}px)"))
        css.append(keyframes("o", k, "opacity", "0", "1"))
        css.append(keyframes("l", k, "fill", "#fff8ec", "#ffe066"))
        css.append(f".p{k}{{animation-name:p{k}}}.o{k}{{animation-name:o{k};opacity:0}}.l{k}{{animation-name:l{k}}}")

    add = out.append
    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W * 2}" height="{H * 2}" '
        f'shape-rendering="crispEdges" role="img" '
        f'aria-label="Contribution pizza {year}: {total} contributions, one slice per month, toppings show daily activity">')
    add("<style>" + "".join(css) + "</style>")

    # table
    # gingham tablecloth in both themes: bright by day, dimmed under evening light for dark mode
    base, stripe, cross, weave = (("#f6efe4", "#e98b7e", "#c0392b", "#ffffff") if theme == "light"
                                  else ("#2e2422", "#6e2a24", "#a3352a", "#000000"))
    add('<defs><pattern id="g" width="24" height="24" patternUnits="userSpaceOnUse">'
        f'<rect width="24" height="24" fill="{base}"/><rect width="12" height="24" fill="{stripe}"/>'
        f'<rect width="24" height="12" fill="{stripe}"/><rect width="12" height="12" fill="{cross}"/></pattern>'
        '<pattern id="w" width="4" height="2" patternUnits="userSpaceOnUse">'
        f'<rect width="1" height="1" fill="{weave}"/><rect x="2" y="1" width="1" height="1" fill="{weave}"/></pattern></defs>')
    add(f'<rect width="{W}" height="{H}" fill="url(#g)"/>')
    add(f'<rect width="{W}" height="{H}" fill="url(#w)" opacity="{".08" if theme == "light" else ".18"}"/>')

    # board
    shadow = ".28" if theme == "light" else ".5"
    add(f'<ellipse cx="{CX + 5}" cy="{CY + 7}" rx="99" ry="97" fill="#3c140a" opacity="{shadow}" shape-rendering="auto"/>')
    add(f'<circle cx="{CX}" cy="{CY}" r="97" fill="#8c5a2e"/><circle cx="{CX}" cy="{CY}" r="95" fill="#b9824b"/>')
    for rr in (90, 74, 58, 40, 22):
        add(f'<circle cx="{CX}" cy="{CY}" r="{rr}" fill="none" stroke="#a8743f" stroke-width="1" stroke-dasharray="7 2 3 2"/>')

    # slices: shadow, strings, slice
    for k, g in enumerate(slices):
        sil = Grid()
        sil.px = {p: "#280a00" for p in g.px}
        add(f'<g class="a o{k}" transform="translate(3 4)">{sil.paths(opacity=".35")}</g>')
    for k, g in enumerate(slices):
        add(f'<g class="a p{k}">{g.paths()}</g>')
    for k in range(12):
        a = (k + .5) * SL
        ddx, ddy = math.sin(a) * 9, -math.cos(a) * 9
        d = ""
        for b in (k * SL, (k + 1) * SL):
            for rr in (28, 46, 64):
                x1, y1 = CX + math.sin(b) * rr, CY - math.cos(b) * rr
                x2, y2 = x1 + ddx, y1 + ddy
                d += f"M{x1:.1f} {y1:.1f}Q{(x1 + x2) / 2:.1f} {(y1 + y2) / 2 + 2:.1f} {x2:.1f} {y2:.1f}"
        add(f'<path class="a o{k}" d="{d}" fill="none" stroke="#f7d774" stroke-width="1" shape-rendering="auto"/>')

    # month labels
    for k in range(12):
        a = (k + .5) * SL
        x, y = CX + math.sin(a) * 109, CY - math.cos(a) * 109
        now = k == today.month - 1 and today.year == year
        add(f'<rect class="a l{k}" x="{x - 12:.0f}" y="{y - 6:.0f}" width="24" height="11" fill="#fff8ec"/>'
            f'<rect x="{x - 12:.0f}" y="{y + 5:.0f}" width="24" height="1" fill="{"#c0392b" if now else "#d8c6ab"}"/>'
            f'<text x="{x:.1f}" y="{y + 3:.1f}" font-family="{FONT}" font-size="7.5" font-weight="700" '
            f'fill="#5a2a1a" text-anchor="middle" shape-rendering="auto">{MONTHS[k]}</text>')

    # steam
    rnd = random.Random(11)
    for i in range(12):
        x = CX - 55 + rnd.random() * 110
        y = CY + 10
        add(f'<g class="st" style="animation-delay:-{rnd.random() * 5:.2f}s"><rect x="{x:.0f}" y="{y}" width="1" height="3" fill="#fff"/>'
            f'<rect x="{x + 1:.0f}" y="{y - 3}" width="1" height="2" fill="#fff"/></g>')

    # caption
    line2 = f"{total:,} contributions"
    cw = max(len(user), len(line2)) * 4.6 + 10
    add(f'<rect x="6" y="{H - 27}" width="{cw:.0f}" height="22" fill="#fff8ec"/><rect x="6" y="{H - 5}" width="{cw:.0f}" height="1" fill="#d8c6ab"/>'
        f'<text font-family="{FONT}" font-size="7.5" font-weight="700" fill="#5a2a1a" shape-rendering="auto">'
        f'<tspan x="11" y="{H - 18}">{user}</tspan><tspan x="11" y="{H - 9}" fill="#c0392b">{line2}</tspan></text>')
    add(f'<rect x="6" y="5" width="34" height="12" fill="#c0392b"/><rect x="6" y="17" width="34" height="1" fill="#7a2018"/>'
        f'<text x="23" y="14" font-family="{FONT}" font-size="8" font-weight="700" fill="#fff8ec" text-anchor="middle" shape-rendering="auto">{year}</text>')
    add("</svg>")
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("GITHUB_USER", "nnnnnoooooeeeee"))
    ap.add_argument("--out", default="dist")
    ap.add_argument("--demo", action="store_true", help="random data, no network")
    a = ap.parse_args()

    today = dt.datetime.now(WIB).date()
    year = today.year
    if a.demo:
        counts, total = demo(year, today)
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("Set GITHUB_TOKEN (or GH_TOKEN), or use --demo")
        counts, total = fetch(a.user, token, year)

    months = months_of(counts, year, today)
    os.makedirs(a.out, exist_ok=True)
    for theme in ("light", "dark"):
        path = os.path.join(a.out, f"pizza-{theme}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(build_svg(months, total, year, a.user, theme, today))
        print(f"wrote {path} ({os.path.getsize(path) // 1024} KB)")


if __name__ == "__main__":
    main()
