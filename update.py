#!/usr/bin/env python3

import json, re, sys, urllib.request
from bs4 import BeautifulSoup

PREAMBLE = r"""# Unofficial “odd-jobbed rankings”

This “rankings” is almost certainly riddled with errors, inaccuracies, and
missing information, and should be treated as such. This is just for informal
use, so please don’t take it too seriously. The levels of the characters listed
here are fetched directly from [the official MapleLegends
rankings](https://maplelegends.com/ranking/all) via [a shitty Python
script](https://codeberg.org/oddjobs/odd-jobbed_rankings/src/branch/master/update.py).

To make the “rankings” actually maintainable, off-island characters who have
not yet achieved level 45, islanders who have not yet achieved level 40, and
campers who have not yet achieved level 10 are not represented here.

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

SUBOPTIMAL = {"Flow", "Oddjobs", "Southperry", "Victoria"}

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
            for tr_child in table_child.children:
                if tr_child.name == "td":
                    level = int(tr_child.string)
                    break

            if level > 0:
                break

    if level < 1:
        print(f"Could not get level for IGN {ign}", file=sys.stderr)

    chars[i]["level"] = level

with open("./README.md", "w", encoding="UTF-8") as readme:
    readme.write(PREAMBLE)

    for char in sorted(chars, key=lambda c: c["level"], reverse=True):
        readme.write(
            f"| {char['ign']} | {markdown_esc(char['name']) if char['name'] else '?'} | {char['level'] if char['level'] else '?'} | {markdown_esc(char['job'])} | {char['guild'] if char['guild'] else markdown_esc('[none]')}{'' if char['guild'] in SUBOPTIMAL else markdown_esc('*')} |\n"
        )
