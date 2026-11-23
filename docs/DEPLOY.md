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

(Once: `ssh factory sudo install -d -o $USER /srv/domains/pietri.dev/genes/dist`.)
`--delete` is safe because a build always holds every published file: published versions are
never removed from the repository (spec §4).

## 3. Caddy

`/etc/caddy/sites/genes.caddy`, with the same guard (CrowdSec) and log lines the other
`*.pietri.dev` files use (copy them from `origen.caddy`):

```
genes.pietri.dev {
	# (guard and log lines as in origen.caddy)
	root * /srv/domains/pietri.dev/genes/dist
	encode zstd gzip
	header {
		Content-Security-Policy "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self'; style-src-attr 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' data: blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
		X-Content-Type-Options nosniff
		Referrer-Policy strict-origin-when-cross-origin
		Cache-Control "public, max-age=600"
	}
	# Frozen versions and the pinned three.js never change: cache them for a year.
	@frozen path /v1/species/*/sheets/* /v1/species/*/looks/* /static/vendor/*
	header @frozen Cache-Control "public, max-age=31536000, immutable"
	@glb path *.glb
	header @glb Content-Type model/gltf-binary
	@md path *.md /llms.txt /llms-full.txt
	header @md Content-Type "text/markdown; charset=utf-8"
	try_files {path} {path}/index.html
	file_server
}
```

The CSP is the one `genes serve` sends (`src/genes/serve.py`); keep them equal.

```
sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy
```

## 4. Check

- <https://genes.pietri.dev/> shows the catalog; the algarrobo card opens its page.
- <https://genes.pietri.dev/species/neltuma-alba/>: the tree turns, play runs, the map draws.
- <https://genes.pietri.dev/sitemap.xml>, `/robots.txt`, `/llms.txt` answer.
- Search Console (optional): add the property `genes.pietri.dev` and submit the sitemap.

## Updating

Every merge to `main` that changes a species: steps 2 only (build, rsync). Caddy and DNS do
not change.
