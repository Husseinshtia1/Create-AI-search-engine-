# G97 Live Alpha — Single-node deployment

Target: controlled Ubuntu 24.04 DigitalOcean Droplet. This is the first deployment topology, not an Internet-scale final architecture.

## Suggested initial host

- 4 vCPU
- 8 GiB RAM
- 160 GiB local SSD
- optional attached volume mounted at `/var/lib/g97`

Choose capacity from measured scale-gate output rather than page count alone.

## Layout

```text
/opt/g97              code + virtualenv
/var/lib/g97          mutable crawl/search data
/etc/systemd/system   g97-search.service, g97-worker.service
/etc/nginx/sites-*    reverse proxy
```

## Install outline

```bash
sudo apt update
sudo apt install -y git python3 python3-venv nginx
sudo useradd --system --home /var/lib/g97 --shell /usr/sbin/nologin g97 || true
sudo mkdir -p /opt/g97 /var/lib/g97
sudo chown -R g97:g97 /var/lib/g97
sudo git clone https://github.com/Husseinshtia1/Create-AI-search-engine-.git /opt/g97
sudo python3 -m venv /opt/g97/.venv
sudo /opt/g97/.venv/bin/pip install --upgrade pip
sudo /opt/g97/.venv/bin/pip install -e /opt/g97
```

Copy the systemd units from `deploy/systemd/` to `/etc/systemd/system/`, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now g97-search g97-worker
sudo systemctl status g97-search g97-worker
```

Copy `deploy/nginx/g97.conf`, replace `search.example.com` with the selected domain, enable the site, test, and reload nginx:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

TLS should be enabled before public access using the operator's chosen ACME/certificate workflow. Do not expose port 8080 publicly; the G97 service binds to `127.0.0.1` and nginx is the public edge.

## First controlled crawl

Seed a deliberately small set first:

```bash
sudo -u g97 /opt/g97/.venv/bin/g97-live --data-dir /var/lib/g97 submit https://example.org/
sudo -u g97 /opt/g97/.venv/bin/g97-live --data-dir /var/lib/g97 sitemap https://example.org/ --max-urls 500
```

Observe:

```bash
sudo -u g97 /opt/g97/.venv/bin/g97-live --data-dir /var/lib/g97 status
sudo -u g97 /opt/g97/.venv/bin/g97-live --data-dir /var/lib/g97 scale-gate
journalctl -u g97-worker -f
```

Do not jump directly to 100K URLs. Reach 1K, collect the required crawl/search samples, evaluate the gate, diagnose any failed metric, then proceed to 10K only on a clean gate.

## Backups

At minimum back up `/var/lib/g97`. SQLite databases use WAL mode, so use a consistent snapshot method (filesystem snapshot while services are stopped, SQLite backup API/tooling, or provider-volume snapshot with a documented consistency procedure). Do not copy only the main `.sqlite3` files while ignoring active WAL files and call that a verified backup.

## Security notes

- public traffic terminates at nginx/TLS;
- the application listens on loopback only;
- crawler blocks non-public/private network targets and validates redirects;
- robots and per-host crawl delay are enforced;
- request body size is bounded;
- systemd services run as non-root `g97` with restricted filesystem write paths;
- no API/admin secret should be committed to the repository.
