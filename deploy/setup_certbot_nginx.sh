#!/bin/bash
set -euo pipefail

DOMAIN="${1:-mindmetric.store}"
WWW_DOMAIN="${2:-www.mindmetric.store}"
EMAIL="${3:-}"

if [[ -z "$EMAIL" ]]; then
  echo "Usage: $0 <domain> <www-domain> <email>"
  echo "Example: $0 mindmetric.store www.mindmetric.store you@example.com"
  exit 1
fi

echo "Installing Certbot and nginx plugin..."
if command -v dnf >/dev/null 2>&1; then
  sudo dnf install -y certbot python3-certbot-nginx
elif command -v yum >/dev/null 2>&1; then
  sudo yum install -y certbot python3-certbot-nginx
else
  echo "Neither dnf nor yum is available on this host."
  exit 1
fi

echo "Preparing ACME challenge directory..."
sudo mkdir -p /var/www/certbot
sudo chown -R nginx:nginx /var/www/certbot || true

echo "Checking nginx config..."
sudo nginx -t
sudo systemctl reload nginx

echo "Requesting certificate for $DOMAIN and $WWW_DOMAIN..."
sudo certbot --nginx \
  -d "$DOMAIN" \
  -d "$WWW_DOMAIN" \
  --agree-tos \
  --redirect \
  --non-interactive \
  -m "$EMAIL"

echo "Verifying automatic renewal configuration..."
sudo systemctl status certbot-renew.timer --no-pager || true
sudo certbot renew --dry-run

echo "SSL setup complete."
