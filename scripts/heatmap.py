import os
from pathlib import Path
import requests


USERNAME = os.environ["PROFILE_USERNAME"]
TOKEN = os.environ["GITHUB_TOKEN"]


QUERY = """
query($username: String!) {
  user(login: $username) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            contributionCount
            date
            weekday
          }
        }
      }
    }
  }
}
"""


# ─────────────────────────────────────────────
# FETCH CONTRIBUTIONS
# ─────────────────────────────────────────────

response = requests.post(
    "https://api.github.com/graphql",
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    },
    json={
        "query": QUERY,
        "variables": {"username": USERNAME},
    },
    timeout=30,
)

response.raise_for_status()

payload = response.json()

if payload.get("errors"):
    raise RuntimeError(payload["errors"])

weeks = (
    payload["data"]["user"]
    ["contributionsCollection"]
    ["contributionCalendar"]
    ["weeks"]
)

# ONLY LAST 5 WEEKS.
# No old months. No empty yearly space.
weeks = weeks[-5:]


# ─────────────────────────────────────────────
# CONTRIBUTION LEVELS
# ─────────────────────────────────────────────

positive_counts = sorted(
    day["contributionCount"]
    for week in weeks
    for day in week["contributionDays"]
    if day["contributionCount"] > 0
)


def percentile(values, fraction):
    if not values:
        return 1

    index = round((len(values) - 1) * fraction)
    return max(1, values[index])


q1 = percentile(positive_counts, 0.25)
q2 = percentile(positive_counts, 0.50)
q3 = percentile(positive_counts, 0.75)


def contribution_color(count):
    if count == 0:
        return "#21262d"

    if count <= q1:
        return "#0e4429"

    if count <= q2:
        return "#006d32"

    if count <= q3:
        return "#26a641"

    return "#39d353"


# ─────────────────────────────────────────────
# SVG CONFIG
# ─────────────────────────────────────────────

CELL = 22
GAP = 6

LEFT = 56
TOP = 48

WIDTH = 260
HEIGHT = 260

TEXT = "#f0f6fc"
MUTED = "#8b949e"

row_map = {
    1: 0,  # Monday
    2: 1,
    3: 2,
    4: 3,
    5: 4,
    6: 5,
    0: 6,  # Sunday
}


# ─────────────────────────────────────────────
# SVG
# ─────────────────────────────────────────────

svg = [
    f'''<svg
xmlns="http://www.w3.org/2000/svg"
width="{WIDTH}"
height="{HEIGHT}"
viewBox="0 0 {WIDTH} {HEIGHT}"
>''',

    """
<style>
text {
    font-family:
        ui-monospace,
        SFMono-Regular,
        Menlo,
        Monaco,
        Consolas,
        "Liberation Mono",
        monospace;
}
</style>
""",

    # transparent background intentionally
    f'''
<text
    x="{LEFT}"
    y="18"
    fill="{TEXT}"
    font-size="13"
    font-weight="600"
>
LAST_5_WEEKS
</text>
''',
]


# ─────────────────────────────────────────────
# WEEK LABELS
# ─────────────────────────────────────────────

week_labels = ["W-4", "W-3", "W-2", "W-1", "NOW"]

for index, label in enumerate(week_labels):

    x = LEFT + index * (CELL + GAP)

    svg.append(
        f'''
<text
    x="{x + CELL / 2}"
    y="37"
    text-anchor="middle"
    fill="{MUTED}"
    font-size="8"
>
{label}
</text>
'''
    )


# ─────────────────────────────────────────────
# DAY LABELS
# ─────────────────────────────────────────────

day_labels = {
    0: "MON",
    2: "WED",
    4: "FRI",
}

for row, label in day_labels.items():

    y = TOP + row * (CELL + GAP) + 15

    svg.append(
        f'''
<text
    x="5"
    y="{y}"
    fill="{MUTED}"
    font-size="8"
>
{label}
</text>
'''
    )


# ─────────────────────────────────────────────
# CELLS
# ─────────────────────────────────────────────

total = 0

for week_index, week in enumerate(weeks):

    for day in week["contributionDays"]:

        count = day["contributionCount"]
        date = day["date"]
        weekday = day["weekday"]

        total += count

        row = row_map[weekday]

        x = LEFT + week_index * (CELL + GAP)
        y = TOP + row * (CELL + GAP)

        color = contribution_color(count)

        svg.append(
            f'''
<rect
    x="{x}"
    y="{y}"
    width="{CELL}"
    height="{CELL}"
    rx="4"
    fill="{color}"
>
<title>{date}: {count} contributions</title>
</rect>
'''
        )


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────

footer_y = TOP + 7 * (CELL + GAP) + 8

svg.append(
    f'''
<text
    x="{LEFT}"
    y="{footer_y}"
    fill="{MUTED}"
    font-size="8"
>
{total} contributions / 5 weeks
</text>
'''
)


svg.append("</svg>")


# ─────────────────────────────────────────────
# WRITE FILE
# ─────────────────────────────────────────────

Path("assets").mkdir(exist_ok=True)

Path("assets/recent-weeks.svg").write_text(
    "\n".join(svg),
    encoding="utf-8",
)

print(
    f"Generated recent-weeks.svg "
    f"with {total} contributions."
)
