use anyhow::{anyhow, bail, Result};
use futures::future::try_join_all;
use serde::Deserialize;
use std::{cmp::Ordering, io::Write, sync::Arc};
use tokio::sync::Mutex;

static PREAMBLE: &str = r##"# Unofficial “odd-jobbed rankings”

This “rankings” is almost certainly riddled with errors, inaccuracies, and
missing information, and should be treated as such. This is just for informal
use, so please don’t take it too seriously. The levels of the characters listed
here are fetched directly from [the official MapleLegends web API
endpoint](https://maplelegends.com/api/) via [a Rust
script](https://codeberg.org/oddjobs/odd-jobbed_rankings/src/branch/master/src/main.rs).

To make the “rankings” actually maintainable, off-island characters who have
not yet achieved level 45, islanders who have not yet achieved level 40, and
campers who have not yet achieved level 10 are not represented here.

“IGN” stands for “in-game name”. The “name” entries are mostly for discerning
when two or more characters are controlled by the same player. The names, I’ve
done on a best-effort basis, and some of them are just Discord™ identifiers
(which, it should be noted, can be changed at more or less any time, for any
reason).

Unknown or uncertain information is denoted by a question mark (“?”).

Legend:

- \*Not a member of <b>Suboptimal</b>.
- †Known to have leeched some non-negligible amount of EXP.
- ‡Known to have leeched a large amount of EXP.

| IGN        | name         | level | job(s)                 | guild         |
| :--------- | :----------- | ----: | :--------------------- | ------------- |
"##;

#[derive(Deserialize)]
struct CharsJson {
    chars: Vec<Char>,
}

#[derive(Deserialize)]
struct Char {
    // In chars.json:
    ign: String,
    name: Option<String>,
    job: String,
    leech: Option<String>,

    // Fetched:
    level: Option<u8>,
    exp_percent: Option<f32>,
    guild: Option<String>,
}

#[derive(Deserialize)]
struct LegendsApiResponse {
    guild: String,
    //name: String,
    level: u8,
    //job: String,
    exp: String,
    //quests: u16,
    //cards: u16,
    //donor: bool,
    //fame: i32,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Intentionally blocking here.
    let chars_json: CharsJson =
        serde_json::from_reader(::std::fs::File::open("chars.json")?)?;
    let char_count = chars_json.chars.len();
    let chars = Arc::new(Mutex::new(chars_json.chars));

    // The actual async part.
    let client = reqwest::Client::new();
    try_join_all((0..char_count).map(|i| {
        tokio::spawn(fetch_info(client.clone(), Arc::clone(&chars), i))
    }))
    .await?;

    // More intentional blocking.
    let mut output_file = ::std::fs::File::create("README.md.temp")?;
    output_file.write_all(PREAMBLE.as_bytes())?;
    let mut cs = chars.lock().await;
    cs.sort_unstable_by(|c1, c2| match (c1.level, c2.level) {
        (Some(l1), Some(l2)) => {
            l2.cmp(&l1).then(match (c1.exp_percent, c2.exp_percent) {
                (Some(ep1), Some(ep2)) => ep2.total_cmp(&ep1),
                _ => Ordering::Equal,
            })
        }
        _ => Ordering::Equal,
    });
    for c in cs.iter() {
        let name_buf;
        let name = if let Some(name) = &c.name {
            name_buf = markdown_esc(name);

            &name_buf
        } else {
            "?"
        };
        let leech_symbol = match c.leech.as_ref().map(|s| s.as_ref()) {
            Some("some") => "†",
            Some("lots") => "‡",
            None | Some("none") => "",
            _ => bail!("Unexpected value of \"leech\""),
        };

        writeln!(
            &mut output_file,
            "| {} | {name} | {leech_symbol}{} | {} | {}{} |",
            c.ign,
            c.level.ok_or_else(|| anyhow!(
                "No level available for IGN {}",
                c.ign,
            ))?,
            markdown_esc(&c.job),
            if let Some(guild) = &c.guild {
                guild
            } else {
                r"\[none\]"
            },
            match c.guild.as_ref().map(|s| s.as_ref()) {
                Some("Oddjobs") | Some("Flow") | Some("Victoria")
                | Some("Ossyrians") | Some("Pariah") => "",
                _ => r"\*",
            },
        )?;
    }

    output_file.flush()?;
    ::std::fs::rename("README.md.temp", "README.md")?;

    Ok(())
}

async fn fetch_info(
    client: reqwest::Client,
    chars: Arc<Mutex<Vec<Char>>>,
    char_ix: usize,
) -> Result<()> {
    let url = format!(
        "https://maplelegends.com/api/character?name={}",
        chars.lock().await[char_ix].ign,
    );
    let resp = client
        .get(url)
        .send()
        .await?
        .json::<LegendsApiResponse>()
        .await?;

    let mut cs = chars.lock().await;
    let c = &mut cs[char_ix];
    c.level.replace(resp.level);
    c.exp_percent
        .replace(resp.exp[..resp.exp.len() - 1].parse().unwrap_or_default());
    c.guild = if resp.guild.is_empty() {
        None
    } else {
        Some(resp.guild)
    };

    Ok(())
}

fn markdown_esc(s: &str) -> String {
    let mut escaped = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '_' | '*' | '(' | ')' | '[' | ']' | '<' | '>' | '#' => {
                escaped.push('\\')
            }
            _ => (),
        }
        escaped.push(c);
    }

    escaped
}
