# Set up the podcasts feed

How the podcast episodes get from this Mac to a phone, what was set up and why, and how to set it up again or move it to a custom domain.

No secrets are in this file. The real bucket URL, endpoint and keys live in `.env` (gitignored) and `podcast-digest/settings.json` (gitignored).

## How it works

```text
podcast-digest/podcast run <name>
  │  fetch, screen, write digest, voice it (Gemini, local fallback)
  ▼
podcast-digest/public/                     on this Mac
  <podcast>/feed.xml + episodes/*.mp3      one feed per podcast
  all/feed.xml                             every podcast in one feed
  │
  │  cloud_sync: upload new files, remove deleted ones, keep under 8 GB
  ▼
Cloudflare R2 bucket  podcast-digest
  <random-prefix>/all/feed.xml             ← the phone subscribes to this
  <random-prefix>/<podcast>/episodes/*.mp3
  │
  ▼
iPhone: Apple Podcasts (with Tailscale on, see "Tailscale on the phone" below)
```

- Every `run`, `digest`, `voice`, `audio` and `publish` rewrites the feeds and uploads what changed.
- New podcasts join `all/feed.xml` by themselves. The phone only ever needs that one URL.
- The Mac does not need to be awake for listening, only for making new episodes.
- The feed URL is public but unguessable: everything sits under a random 32-character folder (`audio.cloud.prefix` in `settings.json`). Anyone with the URL can listen, so do not share it.

## What we did, in order

1. **Local feed server (first version).** Apple's `/usr/bin/python3 -m http.server` served `podcast-digest/public/` on the home network (`http://<mac-ip>:8642/...`), run by the launchd agent `local.podcast-digest.feed`. It only worked on home Wi-Fi.
2. **Fixed playback.** Apple Podcasts needs byte-range requests (HTTP 206). `http.server` ignores them, so episodes did not play. Replaced it with `podcast-digest/feed_server.py`: supports ranges, no folder listings, serves only `public/`. The launchd agent now runs that. The old agent is backed up in `podcast-digest/logs/feed.plist.bak`.
3. **Descriptive episode names.** Each digest gets a topic title (one `claude -p` call, no tools). It names the digest, the NotebookLM file, the episode script and the mp3 (`2026-11-06-core-and-spam-updates-...`), and shows in the app as "Search Updates, 6 Nov 2026: ...". Titles are stored in `public/<podcast>/titles.json`.
4. **One feed for everything.** Added `public/all/feed.xml`, rebuilt whenever any podcast's feed changes.
5. **Feed off the home network.** Google Drive was ruled out: its share links are viewer pages, large files hit a virus-scan page, and podcast apps need direct file links with range support. Tailscale (private VPN) was the other option for serving episodes but needs the Mac awake. Chose **Cloudflare R2** (free up to 10 GB, free downloads, S3 API, range support).
6. **Upload code.** The script signs S3 requests itself (AWS Signature V4, Python standard library only) and uploads changed files, episodes before feeds. A failed upload never loses anything: the local feed is already written and the next run retries.
7. **Free-tier guard.** Bucket kept under 10 GB (see "Storage limits").
8. **Network block.** The ISP on this connection (Biznet, Indonesia) blocks `*.r2.dev` by answering DNS lookups with its own address. The bucket itself works. First fixed on the phone with Cloudflare's 1.1.1.1 app. The sturdier fix is a custom domain (Option B below).
9. **Tailscale replaced 1.1.1.1.** The phone now uses Tailscale as its VPN. The tailnet's DNS settings send every lookup to Cloudflare's resolvers, so r2.dev works without the 1.1.1.1 app. The Mac can join the same tailnet, which also makes the home feed server reachable when away (see "Tailscale on the phone").

## Option A: set it up with r2.dev (what we use now)

### 1. Cloudflare bucket

1. Sign up at dash.cloudflare.com (free). Open **R2 Object Storage**. R2 asks for a payment card even on the free tier.
2. **Create bucket**, name `podcast-digest`.
3. Bucket **Settings** → **Public Development URL** (r2.dev) → **Allow**. Copy the URL (`https://pub-<id>.r2.dev`).

### 2. API token

1. Open https://dash.cloudflare.com/?to=/:account/r2/api-tokens (or R2 **Overview** → right side, **Account Details** → **API Tokens** → **Manage**).
2. **Create Account API token** (or User API token):
   - Permissions: **Object Read & Write** (not Admin).
   - Specify bucket(s): **Apply to specific buckets only** → `podcast-digest`.
   - Leave IP filtering empty. **Create**.
3. The next page shows, once:
   - **Access Key ID** → `R2_ACCESS_KEY_ID`
   - **Secret Access Key** → `R2_SECRET_ACCESS_KEY` (shown only once; if lost, delete the token and make a new one)
   - **S3 endpoint**, the Default one → `R2_ENDPOINT` (`https://<account-id>.r2.cloudflarestorage.com`; the account ID is also in the dashboard address bar)
   - Ignore the "Token value": that is for Cloudflare's own API, not S3.

### 3. Local settings

1. Copy `.env.example` to `.env` in the project root and fill in:

   ```sh
   R2_PUBLIC_BASE=https://pub-<id>.r2.dev
   R2_BUCKET=podcast-digest
   R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
   R2_ACCESS_KEY_ID=...
   R2_SECRET_ACCESS_KEY=...
   ```

   `.env` is gitignored. The keys can instead go in the macOS keychain (safer than a plain-text file), and then the two key lines are left out:

   ```sh
   security add-generic-password -s podcast-digest-r2 -a access_key_id -w
   security add-generic-password -s podcast-digest-r2 -a secret_access_key -w
   ```

   Values in `.env` override the keychain.
2. The random folder name is `audio.cloud.prefix` in `podcast-digest/settings.json`. Make a new one with `python3 -c "import secrets; print(secrets.token_hex(16))"`, or set `R2_PREFIX` in `.env`.
3. The feeds switch from the home address to the bucket only once `R2_PUBLIC_BASE`, `R2_ENDPOINT` and the prefix are all set.

### 4. First upload and checks

```sh
podcast-digest/podcast publish    # writes every feed and uploads everything; prints the feed URLs
podcast-digest/podcast storage    # how full the bucket is
```

Check from a network that can reach r2.dev (or with the real address, see "Network block"):

```sh
curl -s -o /dev/null -w "%{http_code}\n" <R2_PUBLIC_BASE>/<prefix>/all/feed.xml          # expect 200
curl -s -o /dev/null -r 0-99 -w "%{http_code}\n" <an enclosure url from the feed>          # expect 206
```

### 5. Phone

1. Install **Tailscale**, sign in to the tailnet and switch it on. Check the tailnet's DNS settings first (see "Tailscale on the phone"): without them, r2.dev stays blocked.
2. Apple Podcasts → **Library** → **…** → **Follow a Show by URL** → paste `<R2_PUBLIC_BASE>/<prefix>/all/feed.xml`.
3. Unfollow any older per-podcast or home-Wi-Fi feeds, or episodes show twice.
4. Show settings → **Download Episodes** on.

## Option B: custom domain (for later)

A subdomain such as `podcasts.7hillsonline.com` instead of `pub-<id>.r2.dev`. Why:

- Not caught by blocks on `*.r2.dev`, so the phone no longer depends on Tailscale's DNS settings to reach the feed.
- r2.dev is rate-limited and Cloudflare says it is not for production. A custom domain is not, and it gets Cloudflare's cache.
- The URL stays the same even if the bucket changes.

Steps:

1. **The domain's DNS must be on Cloudflare, in the same account as the bucket.** If it is not: Cloudflare → **Add a domain** → follow the steps, then change the nameservers at your registrar to the two Cloudflare ones it gives you. Wait until Cloudflare shows the domain as **Active** (minutes to a day). (`7hillsonline.com` already uses Cloudflare nameservers; check it is in the same account.)
2. R2 → bucket `podcast-digest` → **Settings** → **Custom Domains** → **Add** → enter `podcasts.<your-domain>` → **Continue** → **Connect domain**. Cloudflare creates the DNS record and certificate. Wait until the status is **Active**.
3. In `.env`, change:

   ```sh
   R2_PUBLIC_BASE=https://podcasts.<your-domain>
   ```

4. Rewrite and upload every feed with the new address:

   ```sh
   podcast-digest/podcast publish
   ```

   Episode files do not need re-uploading; only the feeds change. Episode IDs (guids) are based on the file names, not the address, so apps do not show duplicates.
5. Check: `curl -s -o /dev/null -w "%{http_code}\n" https://podcasts.<your-domain>/<prefix>/all/feed.xml` → 200.
6. Phone: follow the new URL `https://podcasts.<your-domain>/<prefix>/all/feed.xml`, unfollow the old r2.dev one. Tailscale can stay on; the feed no longer needs it.
7. Optional: bucket **Settings** → **Public Development URL** → **Disallow**, so the old r2.dev URL stops working.

Keep the random prefix even on your own domain: it is what keeps the feed unguessable.

## Tailscale on the phone

The phone uses Tailscale as its VPN (it replaced Cloudflare's 1.1.1.1 app). Tailscale does not get around the r2.dev block by itself: unless the tailnet overrides DNS, the phone still asks the ISP's DNS servers and gets the wrong address. Set the tailnet's DNS once:

1. Tailscale admin console → **DNS** → **Nameservers** → **Global nameservers** → **Add nameserver** → **Cloudflare** (1.1.1.1). Add **Google** too if you want a second one.
2. Switch on **Override DNS servers** (in older consoles, **Override local DNS**). Without it, devices keep using the network's own DNS for public names.
3. Phone: Tailscale app → settings → **Use Tailscale DNS** on. Keep the VPN connected (the app's **VPN On Demand** setting keeps it connected).
4. Check: Apple Podcasts refreshes the feed on mobile data and on the blocked Wi-Fi.

### Auth key (optional)

Devices normally join the tailnet by signing in through the Tailscale app, and that is the simplest way to add this Mac too (the Mac app or `tailscale up`). An auth key (`tskey-auth-...`, from admin console → **Settings** → **Keys** → **Generate auth key**) is only needed to join a machine without signing in, for example a headless or scripted setup. Nothing in `podcast-digest/podcast` reads it.

If you keep one for this project, put it in the keychain, not a file:

```sh
security add-generic-password -s podcast-digest-tailscale -a authkey -w
tailscale up --authkey "$(security find-generic-password -s podcast-digest-tailscale -a authkey -w)"
```

Or set `TS_AUTHKEY` in `.env` (gitignored). Auth keys expire (90 days at most) unless you make a reusable key; a device that has joined stays joined after its key expires.

### The home feed server over Tailscale (optional)

With the Mac on the tailnet too, the phone can reach the local feed server (`feed_server.py`) when away from home, through the Mac's tailnet name or `100.x` address. This needs the Mac awake, and the server binds only to `audio.host` in `settings.json` (the home IP), so it would have to bind to the Mac's Tailscale address as well. Not set up: the R2 feed covers this without the Mac awake.

## Storage limits (stay on the free tier)

R2's free tier is 10 GB of storage. Cloudflare does not stop uploads at 10 GB, it bills for the extra, so the script enforces its own limits on every sync:

- It reads the real bucket size from R2 (the whole bucket, not just this tool's files). If it cannot, it uploads nothing.
- **Above 8 GB:** the oldest episodes, across all podcasts, are taken off the feeds and deleted from the bucket until the total is under 8 GB. The newest episode always stays. The mp3s move to `podcast-digest/retired-audio/<podcast>/` on the Mac; text digests are never touched.
- **Hard stop at 9 GB:** any upload that would take the bucket past 9 GB is refused and logged as `STORAGE LIMIT`.
- `podcast-digest/podcast storage` shows the current size.
- The limits are `CLOUD_PRUNE_BYTES` and `CLOUD_HARD_BYTES` in `podcast-digest/podcast`.

A 45-minute episode is about 20 MB, so 8 GB holds several hundred episodes. Downloads are free on R2, and a run makes only a handful of requests, far inside the free monthly allowance.

## Network block (r2.dev)

Symptom: the feed URL times out from this Mac or the phone, but `podcast publish` uploads fine.

Check:

```sh
dig +short pub-<id>.r2.dev A     # a non-Cloudflare address (not 104.x or 172.x) means the ISP is redirecting it
```

Confirm the bucket itself is fine by fetching through Cloudflare's real address:

```sh
IP=$(curl -s -H "accept: application/dns-json" "https://cloudflare-dns.com/dns-query?name=pub-<id>.r2.dev&type=A" \
     | python3 -c "import json,sys; print([a['data'] for a in json.load(sys.stdin)['Answer'] if a['type']==1][0])")
curl -s --resolve pub-<id>.r2.dev:443:$IP -o /dev/null -w "%{http_code}\n" https://pub-<id>.r2.dev/<prefix>/all/feed.xml
```

Fix: Tailscale on the phone with the tailnet's DNS override on (see "Tailscale on the phone"), or a custom domain (Option B).

On the phone, if the feed fails with Tailscale on: check the Tailscale app shows **Connected**, and that **Use Tailscale DNS** is on in its settings.

## Troubleshooting

| Problem | Check |
| --- | --- |
| Episodes do not play | `curl -r 0-99` on an episode URL must return 206. On the home server, check `launchctl list \| grep podcast-digest` and `podcast-digest/logs/feed-server.log`. |
| New episode missing from the phone | Pull down to refresh in the app. Look for "Uploaded" or "Cloud upload failed" in the run output. Run `podcast publish` to retry. |
| `Cloud upload skipped: could not read the bucket size` | Keys or endpoint wrong in `.env`, or the token was deleted. |
| `STORAGE LIMIT` in the log | The bucket is near 9 GB. Run `podcast storage`; check for files in the bucket not made by this tool. |
| Episodes voiced in the Mac's voices | The Gemini free tier allows 10 voice requests a day, and a 45-minute episode uses most of them. |
| Feed stops working at home only | The Mac's home IP changed (the local server binds to `audio.host` in `settings.json`). Set a DHCP reservation in the router. |

## Commands

```sh
podcast-digest/podcast run <podcast>     # fetch, digest, voice, update feeds, upload
podcast-digest/podcast publish           # rewrite every feed and upload what changed
podcast-digest/podcast storage           # bucket size and limits
podcast-digest/podcast voice <podcast>   # re-voice the latest digest
```
