# Putting genes.pietri.dev online

genes is static files (spec §12): `genes build` writes `dist/`, and Caddy on factory serves
it. No container, no database, no port: nothing runs per request, so it costs no RAM. Do it
only when marcos says (spec §17, phase 5).

## 1. DNS (Cloudflare)

In Cloudflare, zone `pietri.dev`, DNS → Records → Add record:

| Type | Name  | Content                                     | Proxy |
|------|-------|---------------------------------------------|-------|
| A    | genes | factory's IPv4 (the same as `origen`'s A)   | Proxied (orange cloud) |

Add the AAAA too if `origen` has one. SSL/TLS mode stays as for the other sites (Full, strict).

## 2. The files on factory

Build on marcos's PC from `main` and copy over WireGuard (the PC has the keys):

```
cd ~/genes && git switch main && git pull
uv run genes build --out dist
rsync -a --delete dist/ factory:/srv/domains/pietri.dev/genes/dist/
```

(Once: `ssh -t factory 'sudo install -d -o "$USER" /srv/domains/pietri.dev/genes/dist'`.)
`--delete` is safe because a build always holds every published file: published versions are
never removed from the repository (spec §4).

## 3. Caddy

`/etc/caddy/sites/genes.pietri.dev.caddy`, with the same guard (CrowdSec) the other
`*.pietri.dev` files use, and its own access log:

```
genes.pietri.dev {
	import guard

	log {
		output file /var/log/caddy/genes.pietri.dev.log {
			roll_size 10MiB
			roll_keep 5
		}
	}

	root * /srv/domains/pietri.dev/genes/dist
	encode zstd gzip

	header {
		Content-Security-Policy "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; style-src-attr 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' data: blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
		Strict-Transport-Security "max-age=31536000"
		X-Content-Type-Options "nosniff"
		Referrer-Policy "strict-origin-when-cross-origin"
		# Pages are always checked again, so a deploy shows at once. `?` sets it only when
		# @frozen below has not, whichever order Caddy runs the two `header` lines in.
		?Cache-Control "no-cache"
		-Server
	}
	# The site's CSS, JS and art live in a folder named by their content
	# (/static/site/<version>/, genes.site_static), and frozen versions and the pinned
	# three.js never change: cache them for a year.
	@frozen path /static/site/* /v1/species/*/sheets/* /v1/species/*/looks/* /static/vendor/*
	header @frozen Cache-Control "public, max-age=31536000, immutable"
	@glb path *.glb
	header @glb Content-Type model/gltf-binary
	@md path *.md /llms.txt /llms-full.txt
	header @md Content-Type "text/markdown; charset=utf-8"

	try_files {path} {path}/index.html
	file_server
}
```

The CSP is the one `genes serve` sends (`src/genes/serve.py`); keep them equal. Install it
from marcos's PC (sudo over ssh needs `-t`):

```
scp genes.pietri.dev.caddy factory:/tmp/
ssh -t factory 'sudo install -m 644 /tmp/genes.pietri.dev.caddy /etc/caddy/sites/ && sudo systemctl reload caddy && systemctl is-active caddy'
```

## 4. Check

- <https://genes.pietri.dev/> shows the catalog; the algarrobo card opens its page.
- <https://genes.pietri.dev/species/neltuma-alba/>: the tree turns, play runs, the map draws.
- <https://genes.pietri.dev/sitemap.xml>, `/robots.txt`, `/llms.txt` answer.
- Search Console (optional): add the property `genes.pietri.dev` and submit the sitemap.

## Updating

Every merge to `main`: step 2 only (build, rsync). Caddy and DNS do not change.

The site's CSS, JS and art are published under `/static/site/<content hash>/`, so a new build
never mixes with copies cached by a browser or Cloudflare. Sites set up before this rule still
have the old Caddy file (`max-age=600` on everything): install the block from step 3 once.
