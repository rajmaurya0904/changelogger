# changelogger

**Breaks a Conventional Commits header into type, scope, description and a breaking-change flag — the first step toward generating Keep a Changelog entries from git history.**

**Status: early and incomplete.** `parse_commit()` works and is tested against seven
cases. The `changelogger` command installs and `--help` prints, but **it does nothing
else**: it reads no git history, writes no CHANGELOG.md, and takes no arguments. The
skill file in `SKILL.md` is still a stub.

## The problem

Writing release notes by hand means scrolling `git log`, deciding which of forty
commits a user would care about, and re-learning where "Added" goes versus "Changed".
The commit headers already encode all of it — `feat`, `fix`, the `!` that means you
broke someone's build. Something just has to read them.

## Real output

Four commit subjects in, four classifications out:

```console
$ cat commits.txt
feat(parser): accept scoped commit headers
fix: stop crashing on an empty description
feat(cli)!: rename --out to --output
chore: bump ruff

$ python classify.py
{'type': 'feat', 'scope': 'parser', 'description': 'accept scoped commit headers', 'breaking': False}
{'type': 'fix', 'scope': None, 'description': 'stop crashing on an empty description', 'breaking': False}
{'type': 'feat', 'scope': 'cli', 'description': 'rename --out to --output', 'breaking': True}
{'type': 'chore', 'scope': None, 'description': 'bump ruff', 'breaking': False}
```

`classify.py`:

```python
from changelogger.parser import parse_commit

for line in open("commits.txt"):
    line = line.strip()
    if line:
        print(parse_commit(line))
```

And the command, which is as far as the CLI currently goes:

```console
$ changelogger --help
usage: changelogger [-h]

Generate Keep a Changelog entries from conventional commit history.

options:
  -h, --help  show this help message and exit
```

## Install

Not on PyPI. Clone it and install from the working tree:

```bash
pip install -e ".[dev]"
```

## Usage

```bash
changelogger --help          # prints usage; running it bare exits 0 and prints nothing
python -m changelogger        # same entry point via the module
```

```python
from changelogger.parser import parse_commit

parse_commit("fix(api)!: drop v1 endpoints")
# {'type': 'fix', 'scope': 'api', 'description': 'drop v1 endpoints', 'breaking': True}
```

## How it works

- Splits the message once on the first `": "`. No `": "` means the whole string is
  treated as the header and the description comes back `""`.
- A trailing `!` on the header sets `breaking` and is stripped, so both `feat!:` and
  `feat(core)!:` are caught.
- A scope is whatever sits between the first `(` and the next `)`. No parentheses
  means `scope` is `None`.
- The literal text `BREAKING CHANGE:` anywhere in the message also sets `breaking`.
- The return value is always a four-key dict — `type`, `scope`, `description`,
  `breaking` — never a raised exception for a malformed header.

## Limitations

- No changelog is generated. There is no git reader, no grouping into
  Added/Changed/Fixed sections, and no file writer.
- The CLI accepts no arguments and produces no output.
- Commit types are not validated. `banana: hello` parses as type `banana`.
- The separator must be `": "` with a space. `fix:typo` yields type `fix:typo` and an
  empty description.
- `BREAKING CHANGE:` is matched anywhere in the string, including inside a quoted
  description — a commit that merely mentions the phrase is flagged as breaking.
- Only the header is parsed; the commit body and footers are otherwise ignored.
- `SKILL.md` is a placeholder and gives Claude Code no usable instructions.

## Development

```bash
pip install -e ".[dev]"
pytest -q        # 9 tests
ruff check .
```

MIT — see [LICENSE](LICENSE).
