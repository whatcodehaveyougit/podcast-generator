# Notes for later

Things from Andrew's original prompt that are out of scope for now but will be useful when we come back to them. `/generate-podcast` does not act on this file.

## Where the files live: iCloud and Google Drive

Andrew's original prompt kept everything in `~/podcast-digest/` and said:

> Keep everything in one folder, `~/podcast-digest/`, on local disk. If Desktop or Documents is synced to iCloud, do not put it there. Confirm with a test write before going further.

Why it matters: synced folders (iCloud Desktop and Documents, Google Drive, Dropbox) can offload files to the cloud, lock them mid-sync or create conflicting copies. A tool that writes transcripts, notes and a lock file overnight, or serves mp3s to a phone, can break on that.

Andrew's prompt only named iCloud. It said nothing about Google Drive.

For now everything lives in `podcast-digest/` inside this project, which is gitignored and not in a synced folder. If we later want digests or episodes in iCloud or Google Drive (for example to reach them on the phone without the local feed server), copy finished digests and mp3s there as a final step, and keep the working folder local.

## Scheduling (launchd)

A simple weekday schedule now exists (`launchd/podcast-run.example.plist`, see the README). What follows is the original, fuller design, not built.

Andrew's original design ran unattended every night. When we add scheduling, it called the same script:

- Use a launchd agent. The script's `loop` command is a long-running process: it checks every 10 minutes (`sleep 600`), transcribes between 01:00 and 06:00, runs the login check once a day after 06:00, and delivers on digest days. `KeepAlive` in the plist restarts that loop only if it exits. Guard against two copies with a lock file. `ProgramArguments` is the absolute path to the same script.
- Set `PATH` inside the script and in the plist's `EnvironmentVariables`, because launchd's `PATH` does not include `~/.local/bin` or `/opt/homebrew/bin`.
- The daily check: does `claude -p` still answer? The login expires now and then. Flag it in the next digest and tell me to run `claude`, then `/login`.
- Check the machine will not sleep overnight on mains power (`pmset -g`).
- Digest days and time were a setup question (default Monday and Thursday at 08:00).
