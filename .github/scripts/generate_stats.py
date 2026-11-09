#!/usr/bin/env python3
"""Generate animated GitHub stats cards (SVG) for the profile README.

Uses only the Python standard library. Reads public data from the GitHub
GraphQL API and writes three SVG files into assets/stats/.
"""

import datetime
import html
import json
import os
import urllib.request

USER = os.environ.get("GH_USER", "abuhuraira5130")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT_DIR = os.environ.get("OUT_DIR", "assets/stats")

CY, MINT, GOLD, PINK, BLUE, ORANGE = "#00E5FF", "#2DFFB3", "#FFC400", "#FF3D9A", "#6EA8FF", "#FF8A3D"
LANG_COLORS = [CY, MINT, GOLD, PINK, BLUE, ORANGE]
FONT = "'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100) {
      totalCount
      nodes {
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def esc(value):
    return html.escape(str(value), quote=True)


def fetch_data():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": "bearer " + TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "profile-stats-generator",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    user = payload["data"]["user"]

    collection = user["contributionsCollection"]
    calendar = collection["contributionCalendar"]
    weeks = [
        [(d["date"], d["contributionCount"]) for d in week["contributionDays"]]
        for week in calendar["weeks"]
    ]

    languages = {}
    for repo in user["repositories"]["nodes"]:
        for edge in repo["languages"]["edges"]:
            name = edge["node"]["name"]
            languages[name] = languages.get(name, 0) + edge["size"]

    return {
        "contributions": calendar["totalContributions"],
        "commits": collection["totalCommitContributions"],
        "repos": user["repositories"]["totalCount"],
        "weeks": weeks,
        "languages": sorted(languages.items(), key=lambda item: item[1], reverse=True),
    }


def streaks(weeks):
    days = [day for week in weeks for day in week]
    days.sort(key=lambda d: d[0])
    longest = run = 0
    for _, count in days:
        run = run + 1 if count > 0 else 0
        longest = max(longest, run)
    counts = [count for _, count in days]
    if counts and counts[-1] == 0:
        counts = counts[:-1]  # today may not have a contribution yet
    current = 0
    for count in reversed(counts):
        if count > 0:
            current += 1
        else:
            break
    return current, longest


def shell(width, height, label, right, body):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    right_text = right or ("UPDATED " + now)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(label)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#05060B"/>
      <stop offset="1" stop-color="#0B0D18"/>
    </linearGradient>
    <filter id="blur" x="-40%" y="-80%" width="180%" height="260%">
      <feGaussianBlur stdDeviation="50"/>
    </filter>
    <filter id="glowS" x="-100%" y="-100%" width="300%" height="300%">
      <feGaussianBlur stdDeviation="3" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <clipPath id="card"><rect width="{width}" height="{height}" rx="22"/></clipPath>
  </defs>
  <style>
    text {{ font-family: {FONT}; }}
    .lb {{ font-size: 14px; font-weight: 700; letter-spacing: 4px; }}
    .rt {{ font-size: 13px; font-weight: 600; letter-spacing: 2px; fill: #8A93A8; }}
  </style>
  <g clip-path="url(#card)">
    <rect width="{width}" height="{height}" fill="url(#bg)"/>
    <g filter="url(#blur)">
      <ellipse cx="{width * 0.15:.0f}" cy="{height * 0.3:.0f}" rx="{width * 0.2:.0f}" ry="{height * 0.4:.0f}" fill="{CY}" opacity="0.16">
        <animate attributeName="cx" values="{width * 0.12:.0f};{width * 0.24:.0f};{width * 0.12:.0f}" dur="16s" repeatCount="indefinite"/>
      </ellipse>
      <ellipse cx="{width * 0.88:.0f}" cy="{height * 0.4:.0f}" rx="{width * 0.2:.0f}" ry="{height * 0.4:.0f}" fill="{PINK}" opacity="0.14">
        <animate attributeName="cx" values="{width * 0.9:.0f};{width * 0.76:.0f};{width * 0.9:.0f}" dur="19s" repeatCount="indefinite"/>
      </ellipse>
    </g>
    <text class="lb" x="40" y="44" fill="{CY}">{esc(label)}</text>
    <text class="rt" x="{width - 40}" y="44" text-anchor="end">{esc(right_text)}</text>
{body}
  </g>
  <rect x="2" y="2" width="{width - 4}" height="{height - 4}" rx="22" fill="none" stroke="#FFFFFF" stroke-opacity="0.10" stroke-width="2"/>
  <rect x="2" y="2" width="{width - 4}" height="{height - 4}" rx="22" fill="none" stroke="{CY}" stroke-width="3" pathLength="1000" stroke-dasharray="100 900" stroke-linecap="round" filter="url(#glowS)">
    <animate attributeName="stroke-dashoffset" from="0" to="-1000" dur="8s" repeatCount="indefinite"/>
  </rect>
</svg>
"""


def tile(x, y, w, h, color, value, label, sub, begin):
    cx = x + w / 2
    return f"""    <g>
      <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="#0E1120" fill-opacity="0.85" stroke="{color}" stroke-opacity="0.5" stroke-width="1.5">
        <animate attributeName="stroke-opacity" values="0.3;0.8;0.3" dur="4s" begin="{begin}s" repeatCount="indefinite"/>
      </rect>
      <rect x="{x + 24}" y="{y}" width="{w - 48}" height="3" rx="1.5" fill="{color}"/>
      <text x="{cx}" y="{y + 58}" text-anchor="middle" font-size="48" font-weight="800" fill="#FFFFFF">{esc(value)}</text>
      <text x="{cx}" y="{y + 90}" text-anchor="middle" font-size="16" font-weight="700" fill="#E8EEFF">{esc(label)}</text>
      <text x="{cx}" y="{y + 112}" text-anchor="middle" font-size="13" font-weight="500" fill="#8A93A8">{esc(sub)}</text>
    </g>"""


def render_overview(data):
    current, longest = streaks(data["weeks"])
    items = [
        (CY, f"{data['contributions']:,}", "Contributions", "last 12 months"),
        (MINT, f"{data['commits']:,}", "Commits", "last 12 months"),
        (GOLD, str(current), "Current streak", "days in a row"),
        (PINK, str(longest), "Longest streak", "days, last 12 months"),
        (BLUE, str(data["repos"]), "Public repos", "original projects"),
    ]
    tile_w, gap, top, tile_h = 208, 20, 70, 126
    start_x = (1200 - (len(items) * tile_w + (len(items) - 1) * gap)) / 2
    body = "\n".join(
        tile(start_x + i * (tile_w + gap), top, tile_w, tile_h, color, value, label, sub, i * 0.5)
        for i, (color, value, label, sub) in enumerate(items)
    )
    return shell(1200, 226, "GITHUB OVERVIEW", None, body)


def render_languages(data):
    total = sum(size for _, size in data["languages"]) or 1
    entries = [(name, size / total * 100) for name, size in data["languages"][:6]]
    rest = 100 - sum(pct for _, pct in entries)
    if len(data["languages"]) > 6 and rest > 0.05:
        entries = entries[:5] + [("Other", rest + entries[5][1])]
    colors = LANG_COLORS[:len(entries)]
    if entries and entries[-1][0] == "Other":
        colors[-1] = "#6B7280"

    bar_x, bar_w, bar_y = 40, 1120, 80
    segments, cursor = [], bar_x
    for (name, pct), color in zip(entries, colors):
        width = bar_w * pct / 100
        segments.append(f'      <rect x="{cursor:.1f}" y="{bar_y}" width="{width + 0.5:.1f}" height="24" fill="{color}"/>')
        cursor += width

    legend = []
    for i, ((name, pct), color) in enumerate(zip(entries, colors)):
        x0 = 40 + (i % 3) * 373
        y = 158 + (i // 3) * 46
        legend.append(f"""    <circle cx="{x0 + 9}" cy="{y - 7}" r="7" fill="{color}"/>
    <text x="{x0 + 26}" y="{y}" font-size="20" font-weight="700" fill="#F4F7FF">{esc(name)}</text>
    <text x="{x0 + 330}" y="{y}" text-anchor="end" font-size="20" font-weight="800" fill="{color}">{pct:.1f}%</text>""")

    body = f"""    <clipPath id="barclip"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="24" rx="12"/></clipPath>
    <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="24" rx="12" fill="#10131F"/>
    <g clip-path="url(#barclip)">
{chr(10).join(segments)}
      <rect x="-200" y="{bar_y}" width="140" height="24" fill="#FFFFFF" fill-opacity="0.22" transform="skewX(-20)">
        <animate attributeName="x" from="-200" to="1300" dur="5s" repeatCount="indefinite"/>
      </rect>
    </g>
{chr(10).join(legend)}"""
    return shell(1200, 240 if len(entries) > 3 else 194, "TOP LANGUAGES", None, body)


def smooth_path(points, y_min, y_max):
    path = f"M{points[0][0]:.1f} {points[0][1]:.1f}"
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1, p2 = points[i], points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, min(max(p1[1] + (p2[1] - p0[1]) / 6, y_min), y_max))
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, min(max(p2[1] - (p3[1] - p1[1]) / 6, y_min), y_max))
        path += f" C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
    return path


def render_activity(data):
    weeks = data["weeks"][-52:]
    totals = [sum(count for _, count in week) for week in weeks]
    peak = max(totals) if totals and max(totals) > 0 else 1
    left, right, top, base = 90, 1160, 100, 250
    step = (right - left) / max(len(totals) - 1, 1)
    points = [(left + i * step, base - (value / peak) * (base - top)) for i, value in enumerate(totals)]
    line = smooth_path(points, top, base)
    area = f"{line} L{points[-1][0]:.1f} {base} L{points[0][0]:.1f} {base} Z"

    grid = []
    for ratio in (0, 0.5, 1):
        y = base - ratio * (base - top)
        grid.append(f'    <line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#FFFFFF" stroke-opacity="0.08"/>')
        grid.append(f'    <text x="{left - 14}" y="{y + 5:.1f}" text-anchor="end" font-size="13" fill="#8A93A8">{peak * ratio:.0f}</text>')

    months, last_month, last_x = [], None, -100
    for i, week in enumerate(weeks):
        month = datetime.date.fromisoformat(week[0][0]).strftime("%b")
        if month != last_month:
            last_month = month
            if points[i][0] - last_x >= 55:  # skip labels that would overlap
                months.append(f'    <text x="{points[i][0]:.1f}" y="{base + 30}" font-size="13" font-weight="600" fill="#8A93A8">{month}</text>')
                last_x = points[i][0]

    peak_index = totals.index(max(totals)) if totals else 0
    px, py = points[peak_index]
    tag_x = min(max(px, left + 40), right - 40)

    body = f"""    <defs>
      <linearGradient id="lineG" gradientUnits="userSpaceOnUse" x1="{left}" y1="0" x2="{right}" y2="0">
        <stop offset="0" stop-color="{CY}"/>
        <stop offset="0.4" stop-color="{MINT}"/>
        <stop offset="0.75" stop-color="{GOLD}"/>
        <stop offset="1" stop-color="{PINK}"/>
      </linearGradient>
      <linearGradient id="areaG" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="{CY}" stop-opacity="0.32"/>
        <stop offset="1" stop-color="{CY}" stop-opacity="0"/>
      </linearGradient>
    </defs>
{chr(10).join(grid)}
{chr(10).join(months)}
    <path d="{area}" fill="url(#areaG)"/>
    <path id="trace" d="{line}" fill="none" stroke="url(#lineG)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" filter="url(#glowS)"/>
    <circle r="6" fill="#FFFFFF" filter="url(#glowS)">
      <animateMotion dur="9s" repeatCount="indefinite" path="{line}"/>
    </circle>
    <circle cx="{points[-1][0]:.1f}" cy="{points[-1][1]:.1f}" r="5" fill="none" stroke="{PINK}" stroke-width="2">
      <animate attributeName="r" values="5;14;14" keyTimes="0;0.7;1" dur="2.4s" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="0.9;0;0" keyTimes="0;0.7;1" dur="2.4s" repeatCount="indefinite"/>
    </circle>
    <circle cx="{points[-1][0]:.1f}" cy="{points[-1][1]:.1f}" r="5" fill="{PINK}"/>
    <circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="{GOLD}"/>
    <text x="{tag_x:.1f}" y="{max(py - 14, 74):.1f}" text-anchor="middle" font-size="14" font-weight="700" fill="{GOLD}">Peak week: {peak}</text>"""
    right_text = f"{data['contributions']:,} CONTRIBUTIONS IN THE LAST 12 MONTHS"
    return shell(1200, 310, "CONTRIBUTION ACTIVITY", right_text, body)


def build(data, out_dir=OUT_DIR):
    os.makedirs(out_dir, exist_ok=True)
    files = {
        "overview.svg": render_overview(data),
        "languages.svg": render_languages(data),
        "activity.svg": render_activity(data),
    }
    for name, content in files.items():
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as handle:
            handle.write(content)
        print("wrote", os.path.join(out_dir, name))


if __name__ == "__main__":
    build(fetch_data())
