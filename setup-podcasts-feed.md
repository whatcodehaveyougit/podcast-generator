# Set up the podcasts feed

How the podcast episodes get from this Mac to a phone, what was set up and why, and how to set it up again.

No secrets are in this file. The real addresses live in `podcast-digest/settings.json` (gitignored).

## How it works

```text
podcast-digest/podcast run <name>
  │  fetch, screen, write digest, voice it (Gemini, local fallback)
  ▼
podcast-digest/public/                     on this Mac
  <podcast>/feed.xml + episodes/*.mp3      one feed per podcast
  all/feed.xml                             every podcast in one feed
  │
  │  cloud_sync: rsync over Tailscale SSH (new files in, deleted episodes out)
  ▼
echo-dash (DigitalOcean droplet on the tailnet)  /srv/podcast-digest/
  served by `tailscale serve` at https://echo-dash.<tailnet>.ts.net:8445   (tailnet only)
  all/feed.xml                             ← the phone subscribes to this
  │
  ▼
iPhone: Apple Podcasts, with Tailscale connected
```

- Every `run`, `digest`, `voice`, `audio` and `publish` rewrites the feeds and copies what changed.
- New podcasts join `all/feed.xml` by themselves. The phone only ever needs that one URL.
- The Mac does not need to be awake for listening, only for making new episodes. echo-dash is always on.
- **The feeds are private.** The `ts.net` name only resolves inside the tailnet, and port 8445 listens only on echo-dash's Tailscale interface. A device that is not signed in to the tailnet cannot reach the feed, even with the URL.

## Settings

`podcast-digest/settings.json`, `audio.cloud`:

| Key | Value | What it is |
| --- | --- | --- |
| `target` | `root@echo-dash:/srv/podcast-digest/` | rsync destination. SSH is Tailscale SSH, so no keys are kept anywhere. |
| `public_base` | `https://echo-dash.<tailnet>.ts.net:8445` | the address written into the feeds |

Without `target`, feeds point at the old home feed server (`audio.host`, `audio.port`, served by `feed_server.py`) and nothing is copied. That server is no longer running: its launchd agent was removed on 12 Nov 2026.

## Set it up again

1. On echo-dash (`ssh root@echo-dash`):

   ```sh
   mkdir -p /srv/podcast-digest
   tailscale serve --bg --https=8445 /srv/podcast-digest
   tailscale serve status        # expect: https://echo-dash.<tailnet>.ts.net:8445 (tailnet only)
   ```

   `tailscale serve` survives reboots. To stop it: `tailscale serve --https=8445 off`.
2. On the Mac: `ssh root@echo-dash true` once, so the host is in `known_hosts` (launchd runs cannot answer the prompt). Then fill in `audio.cloud` as above and run `podcast-digest/podcast publish`.
3. Phone: Tailscale app connected. Apple Podcasts → **Library** → **…** → **Follow a Show by URL** → `https://echo-dash.<tailnet>.ts.net:8445/all/feed.xml`. Unfollow any older feeds, or episodes show twice. Show settings → **Download Episodes** on, so episodes play offline too.

## What we did, in order

1. **Local feed server (first version).** `podcast-digest/feed_server.py` served `public/` on home Wi-Fi with byte-range support (Apple Podcasts needs HTTP 206), run by the launchd agent `local.podcast-digest.feed`. Home Wi-Fi only, and only while the Mac was awake.
2. **Descriptive episode names** from a topic title per digest, kept in `public/<podcast>/titles.json`.
3. **One feed for everything:** `public/all/feed.xml`.
4. **Cloudflare R2.** The feeds moved to a public R2 bucket under a random folder, so they worked away from home with the Mac asleep. The ISP here (Biznet, Indonesia) blocks `*.r2.dev`, which needed Tailscale's DNS override on the phone.
5. **Tailnet only (12 Nov 2026).** The R2 feed was public to anyone holding the URL, and the episodes include client data. Moved to echo-dash behind `tailscale serve`, so only devices on the tailnet can fetch them. This also removes the r2.dev block problem and the R2 keys. Cleanup the same day: every file deleted from the R2 bucket, the bucket's public r2.dev URL disabled, the R2 keys removed from `.env`, the R2 upload code and `storage` command removed from the script, and the home feed server's launchd agent (`local.podcast-digest.feed`) stopped and removed. The R2 API token (`podcast-digest`) is to be deleted in the Cloudflare dashboard; the empty bucket can go too.

## Storage

echo-dash has about 20 GB free. A 10-minute episode is about 5 MB, so a year of daily episodes is a couple of GB. Nothing is pruned automatically: delete old mp3s from `podcast-digest/public/<podcast>/episodes/` and run `podcast publish`, which removes them from echo-dash and the feeds.

## Troubleshooting

| Problem | Check |
| --- | --- |
| "Temporarily unavailable" on the phone | Tailscale must be connected on the phone. From the Mac: `curl -r 0-99 -o /dev/null -w "%{http_code}\n" <episode URL>` must return 206. |
| New episode missing from the phone | Pull down to refresh in the app. Look for "Copied" or "Tailnet copy failed" in the run output. Run `podcast publish` to retry. |
| `Tailnet copy failed: Host key verification failed` | Run `ssh root@echo-dash true` once on the Mac and accept the host key. |
| `Tailnet copy failed: tailnet policy does not permit you to SSH` | The tailnet's SSH rules changed. The copy logs in as `root`. |
| Episodes voiced in the Mac's voices | The Gemini free tier allows 10 voice requests a day. |

## Commands

```sh
podcast-digest/podcast run <podcast>     # fetch, digest, voice, update feeds, copy to echo-dash
podcast-digest/podcast publish           # rewrite every feed and copy what changed
podcast-digest/podcast voice <podcast>   # re-voice the latest digest
```
