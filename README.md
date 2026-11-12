# podcast-generator

A Claude Code command that turns the sources you follow into a short research digest and a five-minute, two-host audio episode, tuned to a question you are working on.

You give it a sources file: what you want to learn, the question you are trying to answer, and the CONTENT to follow. CONTENT can be written (blogs, documentation updates, status feeds) or podcast (audio episodes). It fetches anything new, has Claude screen each item against your goals, writes a digest, and voices it as a conversation between two hosts.

Everything runs on your Mac: on demand, or on a weekday schedule (see Scheduled podcasts).

## How it works

1. **Fetch.** Reads each RSS or Atom feed in the sources file and picks up items published since the look-back date (first run) or not yet seen (later runs). At most 10 items per run, oldest first.
2. **Read.** Written CONTENT is read as text, fetching the full page when the feed only has a summary. Podcast episodes use the publisher's transcript (captions or PDF). Whisper is supported but not installed, so episodes with no published transcript are skipped and listed in the digest.
3. **Screen.** Each item goes to `claude -p` with no tools, from an empty folder, with `USER.md` (who you are), your profile and a strict reply format: a two-sentence summary and up to six insights, each with a category, a weight from 1 to 5, how to use it, and a timestamp or section.
4. **Digest.** Pending notes become one markdown digest: Act on this, What I covered, one section per category, Worth a full listen or read, and How the system ran.
5. **Voice.** Claude writes a two-host script from the digest. Gemini TTS (`gemini-3.8-flash-tts`) voices it, with macOS voices as the fallback. Episodes over five minutes are shortened and voiced again.

A fuller file is also saved for NotebookLM, and audio dropped into the drop folder is added to the feed.

## Using it

In Claude Code, from this folder:

```
/generate-podcast sources/<name>.md
```

The first run builds the tool and tests it. Every run after that produces a new digest and episode. With no argument, it lists your sources files and offers to make a new one.

Without Claude Code:

```
podcast-digest/podcast run <name>
```

Other subcommands: `test`, `fetch`, `rescreen`, `preview`, `digest`, `voice`, `audio` and `canary`. Run the script with no arguments to see them.

## About you: USER.md

`USER.md` at the project root says who you are, your mission, who you work for and what you want to learn. Every podcast reads it: screening and the digest use it to judge what matters to you, and the episode script uses it to pick emphasis and examples. Template comments and blank fields are ignored, so you can fill it in a bit at a time. It is gitignored: copy `USER.example.md` to `USER.md` to start.

## Files about you that live elsewhere: context_files

Some context about you, such as a mission statement, may already live in another repo. List those files' absolute paths under `context_files` in `podcast-digest/settings.json` (gitignored). Every prompt reads them fresh, after `USER.md` and before the podcast's profile. `MISSION-STATEMENT.example.md` shows the shape of a mission statement.

## A podcast's own mission statement and resources list

A standing podcast (a daily news show, say) can live in a folder, `sources/<name>/`, with `podcast.md` as its sources file and two more files beside it:

- `mission-statement.md`: why this podcast exists and what it should keep you on top of. Listed under `context_files` in `podcast-digest/podcasts/<name>/config.json`, it goes into every prompt for that podcast. Template: `sources/_mission-statement.example.md`.
- `resources.md`: everyone the podcast listens to, the sources left out and why, and ones to add later. `podcast.md` says "See resources.md" under Content. Template: `sources/_resources.example.md`.

Both stay local, like every sources file.

## Scheduled podcasts

A podcast can run itself Monday to Friday at 21:00 through a launchd agent that calls `podcast run <name>`. Copy `launchd/podcast-run.example.plist`, replace `NAME` and `ROOT`, save it in `~/Library/LaunchAgents/` and load it with `launchctl bootstrap gui/$(id -u) <plist>`. Output goes to `podcast-digest/logs/run-<name>.log`.

The Mac must be awake: a run missed while asleep happens as soon as it wakes. `sudo pmset repeat wakeorpoweron MTWRF 20:55:00` wakes it first, and `caffeinate -i` in the plist keeps it awake until the run ends. A closed laptop on battery will not wake.

## Making a new podcast

1. Copy `sources/_template.md` to `sources/<short-name>.md`.
2. Fill in the goal, what you want to learn, your current question, the look-back date, what is useful, what to ignore, and the Content table. You can leave feed URLs blank: the command finds and checks them.
3. Run `/generate-podcast sources/<short-name>.md`.

Each sources file is its own podcast, with its own folder under `podcast-digest/podcasts/<name>/`.

## Setup

- **Claude Code**, logged in. The screening uses `claude -p`. If the login expires, `run` stops and tells you to log in again.
- **`ffmpeg`** and **`pdftotext`** (Homebrew).
- **A Gemini API key** from aistudio.google.com, stored in the macOS keychain, never in a file:

  ```
  security add-generic-password -s podcast-digest-gemini -a gemini -w
  ```

  On the free tier, Google may use the episode script to improve its products. Without a key, episodes use the built-in macOS voices.

## What is in the repo

| Path | What it is |
| --- | --- |
| `.claude/commands/generate-podcast.md` | The command: the full build specification and safety rules |
| `podcast-digest/podcast` | The script (Python 3, standard library only) |
| `sources/_template.md` | Template for a new sources file |
| `sources/_mission-statement.example.md` | Template for a podcast's own mission statement |
| `sources/_resources.example.md` | Template for a podcast's resources list |
| `launchd/podcast-run.example.plist` | Template for a weekday schedule |
| `MISSION-STATEMENT.example.md` | Template for a mission statement listed in `context_files` |
| `NOTES.md` | Parked ideas: the original scheduling design, and iCloud or Google Drive storage |

Git holds the framework only. Your sources files and everything a run creates are gitignored: settings, profiles, notes, transcripts, digests, scripts and mp3 episodes.

## Where the output goes

```
podcast-digest/
  settings.json                     Claude model, voices, audio settings (no secrets)
  podcasts/<name>/
    profile.md                      built from the sources file
    notes/  transcripts/  logs/
    digests/<date>.md                     the digest
    digests/<date>-with-source-notes.md   the digest plus every source note behind it
    episode-scripts/<date>.md             the two-host script that was voiced
  public/<name>/episodes/<date>.mp3
```

Episodes reach the phone through a private podcast feed on echo-dash, an always-on server in your Tailscale network, so the Mac does not need to be awake for listening. Only devices signed in to the tailnet can fetch it. Setup, and why it is built this way: [setup-podcasts-feed.md](setup-podcasts-feed.md).

## Safety

- Fetched text is treated as untrusted. Screening runs with no tools, so nothing in an episode or post can act on the machine.
- No passwords or API keys are kept in files.
- Notes stay pending until a digest is saved, so a failed run never loses them.
