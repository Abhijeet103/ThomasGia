#!/bin/bash
set -euo pipefail

DOMAIN="${1:-mindmetric.store}"
if [[ $# -ge 3 ]]; then
  # Preserve the old <domain> <www-domain> <email> invocation.
  EMAIL="$3"
else
  EMAIL="${2:-}"
fi
CERT_NAME="${CERTBOT_CERT_NAME:-$DOMAIN}"
AUTH_HOOK="${CERTBOT_DNS_AUTH_HOOK:-}"
CLEANUP_HOOK="${CERTBOT_DNS_CLEANUP_HOOK:-}"

if [[ -z "$EMAIL" ]]; then
  echo "Usage: $0 <domain> <email>"
  echo "Example: $0 mindmetric.store you@example.com"
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

CERTBOT_ARGS=(
  run
  --authenticator manual
  --installer nginx
  --preferred-challenges dns
  --cert-name "$CERT_NAME"
  --expand
  -d "$DOMAIN"
  -d "*.$DOMAIN"
  --agree-tos
  -m "$EMAIL"
  --redirect
)

if [[ -n "$AUTH_HOOK" || -n "$CLEANUP_HOOK" ]]; then
  if [[ ! -x "$AUTH_HOOK" || ! -x "$CLEANUP_HOOK" ]]; then
    echo "CERTBOT_DNS_AUTH_HOOK and CERTBOT_DNS_CLEANUP_HOOK must both be executable."
    exit 1
  fi

  CERTBOT_ARGS+=(
    --manual-auth-hook "$AUTH_HOOK"
    --manual-cleanup-hook "$CLEANUP_HOOK"
    --non-interactive
  )
else
  echo "No DNS hooks configured. Certbot will prompt for the _acme-challenge TXT record."
fi

echo "Requesting one certificate for $DOMAIN and *.$DOMAIN..."
sudo certbot "${CERTBOT_ARGS[@]}"

echo "Checking wildcard coverage..."
sudo bash deploy/check_wildcard_certificate.sh "$DOMAIN" "$CERT_NAME"

echo "Testing and reloading nginx..."
sudo nginx -t
sudo systemctl reload nginx

if [[ -n "$AUTH_HOOK" && -n "$CLEANUP_HOOK" ]]; then
  echo "DNS hooks are configured; checking the Certbot renewal timer..."
  sudo systemctl enable --now certbot-renew.timer 2>/dev/null || true
  sudo systemctl status certbot-renew.timer --no-pager || true
else
  echo "Manual DNS validation was used. Renewal will require the TXT challenge again."
  echo "Configure CERTBOT_DNS_AUTH_HOOK and CERTBOT_DNS_CLEANUP_HOOK for unattended renewal."
fi

echo "Wildcard SSL setup complete."
