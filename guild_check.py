#!/usr/bin/env python3

import json, re, sys, urllib.request
from bs4 import BeautifulSoup


with open("./chars.json", "r", encoding="UTF-8") as chars_json:
    chars = json.load(chars_json)["chars"]

for i in range(len(chars)):
    ign = chars[i]["ign"]
    page = 1
    url = f"https://maplelegends.com/ranking/all?search={ign}"
    results = 0

    while True:
        with urllib.request.urlopen(url) as res:
            html = res.read()

        soup = BeautifulSoup(html, "lxml")
        guild_a_next = False
        guild_name = None
        for table_a in soup.table.find_all("a"):
            if guild_a_next:
                if "guild_name_link" not in table_a["class"]:
                    print(
                        "Expected `class` attribute to contain `guild_name_link`",
                        file=sys.stderr,
                    )
                guild_name = table_a["href"][len("/ranking/guildmembers?search=") :]

                break

            if table_a.string == ign and table_a["href"] == f"/levels?name={ign}":
                guild_a_next = True

        if guild_name is not None:
            break

        for table_sibling in soup.table.next_siblings:
            if table_sibling.name == "p":
                for c in table_sibling.children:
                    if c.name == "b":
                        results = int(c.string)

                        break
                break

        pages = (results - 1) // 5 + 1
        if pages > page:
            page += 1
            url = f"https://maplelegends.com/ranking/all?page={page}&search={ign}"
        else:
            break

    if guild_name is None:
        print(f"Could not get guild name for IGN {ign}")
    elif len(guild_name) < 1:
        if chars[i]["guild"] is not None:
            print(
                f"Guild name mismatch for IGN {ign}: chars.json says {chars[i]['guild']}, ML rankings say that they are guildless"
            )
    elif chars[i]["guild"] != guild_name:
        print(
            f"Guild name mismatch for IGN {ign}: chars.json says {chars[i]['guild'] if chars[i]['guild'] is not None else 'that they are guildless'}, ML rankings say {guild_name}"
        )
