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
DOMAIN_FILE="${CERTBOT_TENANT_DOMAIN_FILE:-deploy/tenant_domains.txt}"

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

if [[ ! -r "$DOMAIN_FILE" ]]; then
  echo "Tenant domain file not found: $DOMAIN_FILE"
  exit 1
fi

TENANT_DOMAINS=()
while IFS= read -r tenant_domain; do
  TENANT_DOMAINS+=("$tenant_domain")
done < <(
  sed 's/#.*//' "$DOMAIN_FILE" \
    | tr '[:upper:]' '[:lower:]' \
    | awk 'NF {print $1}' \
    | sort -u
)
CERTIFICATE_DOMAINS=("$DOMAIN" "www.$DOMAIN" "${TENANT_DOMAINS[@]}")

if (( ${#CERTIFICATE_DOMAINS[@]} > 100 )); then
  echo "A certificate can contain at most 100 domain names."
  exit 1
fi

for tenant_domain in "${TENANT_DOMAINS[@]}"; do
  if [[ ! "$tenant_domain" =~ ^[a-z0-9][a-z0-9-]*\.${DOMAIN//./\\.}$ ]]; then
    echo "Invalid tenant domain in $DOMAIN_FILE: $tenant_domain"
    exit 1
  fi
done

CERTBOT_ARGS=(
  run
  --authenticator webroot
  --webroot-path /var/www/certbot
  --installer nginx
  --cert-name "$CERT_NAME"
  --force-renewal
  --agree-tos
  -m "$EMAIL"
  --redirect
  --non-interactive
)

for certificate_domain in "${CERTIFICATE_DOMAINS[@]}"; do
  CERTBOT_ARGS+=(-d "$certificate_domain")
done

echo "Requesting one certificate for ${#CERTIFICATE_DOMAINS[@]} configured domains..."
sudo certbot "${CERTBOT_ARGS[@]}"

echo "Checking configured domain coverage..."
sudo bash deploy/check_certificate_domains.sh "$DOMAIN" "$CERT_NAME" "$DOMAIN_FILE"

echo "Testing and reloading nginx..."
sudo nginx -t
sudo systemctl reload nginx

echo "Enabling automatic certificate renewal..."
sudo systemctl enable --now certbot-renew.timer 2>/dev/null || true
sudo systemctl status certbot-renew.timer --no-pager || true

echo "Tenant domain SSL setup complete."
