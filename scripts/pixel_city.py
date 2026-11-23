#!/usr/bin/env python3
"""
Pixel City — GitHub contribution skyline.

Each week of the last year becomes one pixel-art building:
  - building height  = contributions that week
  - lit windows      = how active that week was (more contributions, more lights)
  - empty weeks      = an empty lot with a little tree
  - the tallest week = an antenna with a blinking red light

Outputs two SVGs: city-night.svg (dark mode) and city-day.svg (light mode).

Usage:
  GITHUB_TOKEN=xxx python pixel_city.py --user nnnnnoooooeeeee --out dist
  python pixel_city.py --demo --out dist          # random data, no network
No third-party dependencies (standard library only).
"""
import argparse
import json
import math
import os
import random
import urllib.request

# ---------------------------------------------------------------- data

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
  }
}
"""


def fetch_weeks(user, token):
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "pixel-city",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GitHub API error: {data['errors']}")
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[d["contributionCount"] for d in w["contributionDays"]] for w in cal["weeks"]]
    first_day = cal["weeks"][0]["contributionDays"][0]["date"]
    return weeks, cal["totalContributions"], first_day


def demo_weeks(seed=7):
    rnd = random.Random(seed)
    weeks = []
    for _ in range(53):
        if rnd.random() < 0.15:
            weeks.append([0] * 7)
        else:
            weeks.append([int(rnd.random() ** 2 * 14) if rnd.random() < 0.7 else 0 for _ in range(7)])
    return weeks, sum(map(sum, weeks)), "demo"


# ---------------------------------------------------------------- drawing

THEMES = {
    "night": {
        "sky": "#1b1d3a", "sky2": "#23264a", "ground": "#2a2d55", "road": "#16182f",
        "line": "#4a4e88", "buildings": ["#3b3f72", "#45498a", "#34386a", "#4e5296"],
        "roof": "#272a52", "lit": "#ffd75e", "lit2": "#ffb84d", "dark": "#1f2245",
        "tree": "#2f6b4f", "trunk": "#5a3d2b", "text": "#c9cbf2",
        "car": ["#ff6b6b", "#4dd4ac", "#ffd75e"], "light": "#fff6c2",
    },
    "day": {
        "sky": "#8fd3f4", "sky2": "#a9def7", "ground": "#6aa84f", "road": "#5b6470",
        "line": "#e8e8e8", "buildings": ["#9aa5b1", "#b8c2cc", "#7b8794", "#c9b79c"],
        "roof": "#5f6b78", "lit": "#e8f4ff", "lit2": "#cfe8ff", "dark": "#5c6b7a",
        "tree": "#3f8f3a", "trunk": "#7a5233", "text": "#1d3557",
        "car": ["#e63946", "#2a9d8f", "#f4a261"], "light": "#ffffff",
    },
}

COL_W = 5          # building width in pixel units
GAP = 1            # gap between buildings
MAX_H = 58         # tallest building height in pixel units
SKY_H = 96         # sky area height (top to ground)
PAD = 6            # left/right padding
SCALE = 3          # 1 pixel unit = SCALE screen px


def rect_path(cells):
    """Combine many 1x1 (or wxh) cells into a single compact <path d>."""
    return "".join(f"M{x} {y}h{w}v{h}h-{w}z" for x, y, w, h in cells)


def build_svg(weeks, total, mode, user, seed_key):
    t = THEMES[mode]
    rnd = random.Random(f"{seed_key}-{mode}")
    n = len(weeks)
    W = PAD * 2 + n * COL_W + (n - 1) * GAP
    ground_y = SKY_H
    H = SKY_H + 14
    totals = [sum(w) for w in weeks]
    peak = max(totals) or 1
    peak_i = totals.index(peak) if max(totals) > 0 else -1

    out = []
    add = out.append
    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W * SCALE}" height="{H * SCALE}" shape-rendering="crispEdges" '
        f'role="img" aria-label="{user} contribution city: {total} contributions in the last year">'
    )
    add("<style>"
        "@keyframes tw{0%,100%{opacity:1}50%{opacity:.15}}"
        "@keyframes blink{0%,60%{opacity:1}61%,100%{opacity:0}}"
        f"@keyframes drive{{from{{transform:translateX(-12px)}}to{{transform:translateX({W + 12}px)}}}}"
        f"@keyframes driveb{{from{{transform:translateX({W + 12}px)}}to{{transform:translateX(-12px)}}}}"
        f"@keyframes drift{{from{{transform:translateX(-40px)}}to{{transform:translateX({W + 40}px)}}}}"
        ".tw{animation:tw 3s steps(2) infinite}"
        ".bl{animation:blink 1.4s steps(1) infinite}"
        "</style>")

    # sky with a simple banded "dither" look
    add(f'<rect width="{W}" height="{H}" fill="{t["sky"]}"/>')
    add(f'<rect y="{SKY_H - 30}" width="{W}" height="30" fill="{t["sky2"]}"/>')

    if mode == "night":
        stars, twinkle = [], []
        for _ in range(70):
            c = (rnd.randrange(W), rnd.randrange(SKY_H - 25), 1, 1)
            (twinkle if rnd.random() < 0.25 else stars).append(c)
        add(f'<path d="{rect_path(stars)}" fill="#ffffff" opacity=".8"/>')
        for i, c in enumerate(twinkle):
            add(f'<rect x="{c[0]}" y="{c[1]}" width="1" height="1" fill="#ffffff" class="tw" '
                f'style="animation-delay:{(i * 0.37) % 3:.2f}s"/>')
        mx = W - 30
        add(f'<path d="{rect_path([(mx+2,6,6,1),(mx+1,7,8,1),(mx,8,10,6),(mx+1,14,8,1),(mx+2,15,6,1)])}" fill="#f4e9b8"/>')
        add(f'<path d="{rect_path([(mx+5,7,6,1),(mx+6,8,6,6),(mx+5,14,6,1)])}" fill="{t["sky"]}"/>')
    else:
        sx = W - 30
        add(f'<path d="{rect_path([(sx+2,6,6,1),(sx+1,7,8,1),(sx,8,10,6),(sx+1,14,8,1),(sx+2,15,6,1)])}" fill="#ffe066"/>')
        for i in range(3):
            cy = 10 + i * 9
            dur = 70 + i * 25
            add(f'<g style="animation:drift {dur}s linear infinite;animation-delay:-{i * 23}s" fill="#ffffff">'
                f'<path d="{rect_path([(4,cy,14,3),(7,cy-2,7,2),(2,cy+1,18,2)])}"/></g>')

    # buildings
    lit_cells, lit2_cells, dark_cells, twinkle_win = [], [], [], []
    for i, days in enumerate(weeks):
        c = totals[i]
        bx = PAD + i * (COL_W + GAP)
        if c == 0:
            # empty lot: a small tree
            add(f'<rect x="{bx+2}" y="{ground_y-3}" width="1" height="3" fill="{t["trunk"]}"/>')
            add(f'<path d="{rect_path([(bx+1,ground_y-6,3,3),(bx+2,ground_y-7,1,1)])}" fill="{t["tree"]}"/>')
            continue
        h = 6 + round(math.sqrt(c / peak) * (MAX_H - 6))
        by = ground_y - h
        color = t["buildings"][rnd.randrange(len(t["buildings"]))]
        add(f'<rect x="{bx}" y="{by}" width="{COL_W}" height="{h}" fill="{color}"/>')
        add(f'<rect x="{bx}" y="{by}" width="{COL_W}" height="1" fill="{t["roof"]}"/>')
        # light ratio: active days + intensity
        active = sum(1 for d in days if d > 0) / 7
        ratio = min(1.0, 0.15 + 0.5 * active + 0.5 * math.sqrt(c / peak))
        for wy in range(by + 3, ground_y - 2, 3):
            for wx in (bx + 1, bx + 3):
                cell = (wx, wy, 1, 2)
                r = rnd.random()
                if r < ratio:
                    if rnd.random() < 0.04:
                        twinkle_win.append(cell)
                    elif rnd.random() < 0.3:
                        lit2_cells.append(cell)
                    else:
                        lit_cells.append(cell)
                else:
                    dark_cells.append(cell)
        if i == peak_i:
            add(f'<rect x="{bx+2}" y="{by-5}" width="1" height="5" fill="{t["roof"]}"/>')
            add(f'<rect x="{bx+2}" y="{by-6}" width="1" height="1" fill="#ff3b3b" class="bl"/>')

    add(f'<path d="{rect_path(dark_cells)}" fill="{t["dark"]}"/>')
    add(f'<path d="{rect_path(lit_cells)}" fill="{t["lit"]}"/>')
    add(f'<path d="{rect_path(lit2_cells)}" fill="{t["lit2"]}"/>')
    for k, c in enumerate(twinkle_win):
        add(f'<rect x="{c[0]}" y="{c[1]}" width="1" height="2" fill="{t["lit"]}" class="tw" '
            f'style="animation-delay:{(k * 0.9) % 3:.1f}s"/>')

    # ground + road with dashed lane
    add(f'<rect y="{ground_y}" width="{W}" height="2" fill="{t["ground"]}"/>')
    add(f'<rect y="{ground_y+2}" width="{W}" height="7" fill="{t["road"]}"/>')
    dashes = [(x, ground_y + 5, 3, 1) for x in range(2, W, 7)]
    add(f'<path d="{rect_path(dashes)}" fill="{t["line"]}"/>')
    add(f'<rect y="{ground_y+9}" width="{W}" height="{H-ground_y-9}" fill="{t["ground"]}"/>')

    # cars
    for k in range(3):
        lane_y = ground_y + 3 if k % 2 == 0 else ground_y + 6
        anim = "drive" if k % 2 == 0 else "driveb"
        dur = 14 + k * 5
        col = t["car"][k % len(t["car"])]
        head = 5 if anim == "drive" else 0
        add(f'<g style="animation:{anim} {dur}s linear infinite;animation-delay:-{k * 6}s">'
            f'<rect x="0" y="{lane_y}" width="6" height="2" fill="{col}"/>'
            f'<rect x="1" y="{lane_y-1}" width="3" height="1" fill="{col}"/>'
            f'<rect x="{head}" y="{lane_y}" width="1" height="1" fill="{t["light"]}"/></g>')

    # label
    label = f"{user} · {total:,} contributions in the last year"
    add(f'<text x="{PAD}" y="9" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" '
        f'font-size="5" fill="{t["text"]}" shape-rendering="auto">{label}</text>')

    add("</svg>")
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default=os.environ.get("GITHUB_USER", "nnnnnoooooeeeee"))
    ap.add_argument("--out", default="dist")
    ap.add_argument("--demo", action="store_true", help="use random data, no network")
    a = ap.parse_args()

    if a.demo:
        weeks, total, key = demo_weeks()
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            raise SystemExit("Set GITHUB_TOKEN (or GH_TOKEN), or use --demo")
        weeks, total, key = fetch_weeks(a.user, token)

    os.makedirs(a.out, exist_ok=True)
    for mode in ("night", "day"):
        path = os.path.join(a.out, f"city-{mode}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(build_svg(weeks, total, mode, a.user, key))
        print(f"wrote {path} ({os.path.getsize(path) // 1024} KB)")


if __name__ == "__main__":
    main()
