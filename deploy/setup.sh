#!/bin/bash
# Installs or updates the Haq server on Ubuntu 24.04. Usage: sudo bash deploy/setup.sh HOSTNAME
# Run from the repository's root. Safe to run again; it never overwrites /etc/haq/haq.env.
set -euo pipefail

HOST="${1:?usage: sudo bash deploy/setup.sh HOSTNAME}"
[[ "$HOST" =~ ^[A-Za-z0-9.-]+$ ]] || { echo "bad hostname: $HOST" >&2; exit 1; }

apt-get update -q
apt-get install -qy python3-venv ffmpeg caddy rsync

id haq >/dev/null 2>&1 || useradd --system --home /var/lib/haq --shell /usr/sbin/nologin haq
install -d -o haq -g haq -m 700 /var/lib/haq
install -d -m 755 /opt/haq
rsync -a --delete --exclude .env --exclude workspace --exclude '.venv*' --exclude __pycache__ --exclude tests server/ /opt/haq/server/
python3 -m venv /opt/haq/venv
/opt/haq/venv/bin/pip install -q -r /opt/haq/server/requirements.txt

install -d -m 700 /etc/haq
if [ ! -f /etc/haq/haq.env ]; then
    install -m 600 deploy/haq.env.example /etc/haq/haq.env
    echo "Now put the API key in /etc/haq/haq.env and run: sudo systemctl restart haq"
fi

install -m 644 deploy/haq.service deploy/haq-purge.service deploy/haq-purge.timer /etc/systemd/system/
sed "s/__HOST__/$HOST/" deploy/Caddyfile > /etc/caddy/Caddyfile

systemctl daemon-reload
systemctl enable haq haq-purge.timer caddy
systemctl start haq-purge.timer
systemctl restart caddy
