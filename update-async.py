#!/usr/bin/env python3

import asyncio, contextvars, functools, json, re, shutil, sys, urllib.request
from bs4 import BeautifulSoup

PREAMBLE = r"""# Unofficial “odd-jobbed rankings”

This “rankings” is almost certainly riddled with errors, inaccuracies, and
missing information, and should be treated as such. This is just for informal
use, so please don’t take it too seriously. The levels of the characters listed
here are fetched directly from [the official MapleLegends
rankings](https://maplelegends.com/ranking/all) via [a shitty Python
script](https://codeberg.org/oddjobs/odd-jobbed_rankings/src/branch/master/update-async.py).

To make the “rankings” actually maintainable, off-island characters who have
not yet achieved level 45, islanders who have not yet achieved level 40, and
campers who have not yet achieved level 10 are not represented here.

“IGN” stands for “in-game name”. The “name” entries are mostly for discerning
when two or more characters are controlled by the same player. The names, I’ve
done on a best-effort basis, and some of them are just Discord identifiers
(which, it should be noted, can be changed at more or less any time, for any
reason).

Unknown or uncertain information is denoted by a question mark (“?”).

Legend:

- \*Not a member of <b>Suboptimal</b>.
- †Known to have leeched some non-negligible amount of EXP.
- ‡Known to have leeched a large amount of EXP.

| IGN        | name         | level | job(s)                 | guild         |
| :--------- | :----------- | ----: | :--------------------- | ------------- |
"""

SUBOPTIMAL = {"Flow", "Oddjobs", "Victoria", "Embargo"}

SPECIAL_MARKDOWN_RE = re.compile(r"_|\*|\[|\]|<|>|#")


async def to_thread(func, /, *args, **kwargs):
    """
    Polyfill because Python 3.8 (see: Ubuntu 20.04) doesn't have this function
    HAHAHAH

    https://github.com/python/cpython/blob/main/Lib/asyncio/threads.py
    """
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)


def markdown_esc(s):
    return SPECIAL_MARKDOWN_RE.sub(lambda mo: rf"\{mo.group(0)}", s)


with open("./chars.json", "r", encoding="UTF-8") as chars_json:
    chars = json.load(chars_json)["chars"]


def fetch_lvl(i):
    try:
        ign = chars[i]["ign"]
        url = f"https://maplelegends.com/levels?name={ign}"

        with urllib.request.urlopen(url) as res:
            html = res.read()

        soup = BeautifulSoup(html, "lxml")
        if (not soup.table) or (not soup.table.children):
            print(f"IGN {ign} doesn’t seem to exist", file=sys.stderr)

            return

        level = 0
        for table_child in soup.table.children:
            if table_child.name == "tr":
                for tr_child in table_child.children:
                    if tr_child.name == "td":
                        level = int(tr_child.string)
                        break

                if level > 0:
                    break
    except BaseException as e:
        print(
            f"Exception ocurred while fetching level for IGN {ign}",
            file=sys.stderr,
        )
        raise e

    if level < 1:
        print(f"Could not get level for IGN {ign}", file=sys.stderr)

    # We aren't using a mutex or really any synchronisation primitives, but
    # that's okay because the GIL will save us.  The only reason that this
    # script even runs faster than the synchronous version is because the GIL
    # is released when performing I/O...
    chars[i]["level"] = level


asyncio.run(
    asyncio.wait(
        [to_thread(fetch_lvl, i) for i in range(len(chars))],
        return_when=asyncio.ALL_COMPLETED,
    )
)

with open("./README.md.temp", "w", encoding="UTF-8") as readme:
    readme.write(PREAMBLE)

    for char in sorted(chars, key=lambda c: c["level"], reverse=True):
        leech_symbol = ""
        if "leech" in char:
            if char["leech"] == "some":
                leech_symbol = "†"
            elif char["leech"] == "lots":
                leech_symbol = "‡"

        readme.write(
            f"| {char['ign']} | {markdown_esc(char['name']) if char['name'] else '?'} | {leech_symbol}{char['level'] if char['level'] else '?'} | {markdown_esc(char['job'])} | {char['guild'] if char['guild'] else markdown_esc('[none]')}{'' if char['guild'] in SUBOPTIMAL else markdown_esc('*')} |\n"
        )

shutil.move("./README.md.temp", "./README.md")
