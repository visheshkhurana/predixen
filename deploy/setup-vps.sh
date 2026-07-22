#!/usr/bin/env bash
# One-time VPS bootstrap for FounderConsole.
# Run as root on a fresh Ubuntu 24.04 server:  bash setup-vps.sh
set -euo pipefail

echo "==> Updating system"
apt-get update && apt-get upgrade -y

echo "==> Installing basics"
apt-get install -y ca-certificates curl git ufw fail2ban unattended-upgrades

echo "==> Installing Docker (official script)"
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

echo "==> Enabling automatic security updates"
dpkg-reconfigure -f noninteractive unattended-upgrades

echo "==> Firewall: allow SSH, HTTP, HTTPS only"
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> fail2ban (protects SSH from brute force)"
systemctl enable --now fail2ban

echo "==> Adding 2G swap (helps npm/vite builds on small servers)"
if ! swapon --show | grep -q swapfile; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> Creating deploy user 'app' with docker access"
if ! id app >/dev/null 2>&1; then
  adduser --disabled-password --gecos "" app
  usermod -aG docker app
  mkdir -p /home/app/.ssh
  # copy root's authorized_keys so you can ssh in as 'app'
  if [ -f /root/.ssh/authorized_keys ]; then
    cp /root/.ssh/authorized_keys /home/app/.ssh/
    chown -R app:app /home/app/.ssh
    chmod 700 /home/app/.ssh && chmod 600 /home/app/.ssh/authorized_keys
  fi
fi

echo ""
echo "Done. Next steps (as user 'app'):"
echo "  su - app"
echo "  git clone <your-repo-url> founderconsole && cd founderconsole"
echo "  cp deploy/env.production.example .env.production   # then fill it in"
echo "  bash deploy/deploy.sh"
