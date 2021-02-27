#!/usr/bin/env python3

import json, re, sys, urllib.request
from bs4 import BeautifulSoup

PREAMBLE = r"""# Unofficial “odd-jobbed rankings”

This “rankings” is almost certainly riddled with errors, inaccuracies, and
missing information, and should be treated as such. This is just for informal
use, so please don’t take it too seriously.

Because the impetus of this “rankings” was the formation of groups for
bossing/PQing, only off-island characters are represented here. In addition, to
make the “rankings” actually maintainable, characters who have not yet achieved
level 45 are not represented here either. Supposedly, only active players
(“player” should be distinguished from “player character”) are represented
here.

“IGN” stands for “in-game name”. The “name” entries are mostly for discerning
when two or more characters are controlled by the same player. The names, I’ve
done on a best-effort basis, and some of them are just Discord identifiers
(which, it should be noted, can be changed at more or less any time, for any
reason).

Unknown or uncertain information is denoted by a question mark (“?”).

\*Not a member of <b>Suboptimal</b>.

| IGN        | name         | level | job(s)                 | guild         |
| :--------- | :----------- | ----: | :--------------------- | ------------- |
"""

SUBOPTIMAL = {"Flow", "Oddjobs", "Southperry"}

SPECIAL_MARKDOWN_RE = re.compile(r"_|\*|\[|\]|<|>|#")


def markdown_esc(s):
    return SPECIAL_MARKDOWN_RE.sub(lambda mo: fr"\{mo.group(0)}", s)


with open("./chars.json", "r", encoding="UTF-8") as chars_json:
    chars = json.load(chars_json)["chars"]

for i in range(len(chars)):
    ign = chars[i]["ign"]
    url = f"https://maplelegends.com/levels?name={ign}"

    with urllib.request.urlopen(url) as res:
        html = res.read()

    soup = BeautifulSoup(html, "lxml")
    level = 0
    for table_child in soup.table.children:
        if table_child.name == "tr":
            found_level = False

            for tr_child in table_child.children:
                if tr_child.name == "td":
                    level = int(tr_child.string)
                    found_level = True
                    break

            if found_level:
                break

    if level == 0:
        print(f"Could not get level for IGN {ign}", file=sys.stderr)

    chars[i]["level"] = level

with open("./README.md", "w", encoding="UTF-8") as readme:
    readme.write(PREAMBLE)

    for char in sorted(chars, key=lambda c: c["level"], reverse=True):
        readme.write(
            f"| {char['ign']} | {markdown_esc(char['name']) if char['name'] else '?'} | {char['level'] if char['level'] else '?'} | {markdown_esc(char['job'])} | {char['guild']}{'' if char['guild'] in SUBOPTIMAL else markdown_esc('*')} |\n"
        )
