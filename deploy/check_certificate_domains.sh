#!/bin/bash
set -euo pipefail

DOMAIN="${1:-mindmetric.store}"
CERT_NAME="${2:-$DOMAIN}"
DOMAIN_FILE="${3:-deploy/tenant_domains.txt}"
MIN_VALIDITY_SECONDS="${CERTBOT_MIN_VALIDITY_SECONDS:-604800}"
CERT_PATH="${CERTBOT_CERT_PATH:-/etc/letsencrypt/live/${CERT_NAME}/fullchain.pem}"

if [[ ! "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ || ! "$CERT_NAME" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Invalid certificate domain or name."
  exit 1
fi

if [[ ! -r "$DOMAIN_FILE" ]]; then
  echo "Tenant domain file not found: $DOMAIN_FILE"
  exit 1
fi

if [[ ! -r "$CERT_PATH" ]]; then
  echo "Certificate not found: $CERT_PATH"
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
EXPECTED_DOMAINS=("$DOMAIN" "www.$DOMAIN" "${TENANT_DOMAINS[@]}")

if (( ${#EXPECTED_DOMAINS[@]} > 100 )); then
  echo "A certificate can contain at most 100 domain names."
  exit 1
fi

for tenant_domain in "${TENANT_DOMAINS[@]}"; do
  if [[ ! "$tenant_domain" =~ ^[a-z0-9][a-z0-9-]*\.${DOMAIN//./\\.}$ ]]; then
    echo "Invalid tenant domain in $DOMAIN_FILE: $tenant_domain"
    echo "Use a first-level hostname such as demo.$DOMAIN."
    exit 1
  fi
done

CERTIFICATE_DOMAINS="$(
  openssl x509 -in "$CERT_PATH" -noout -ext subjectAltName \
    | tr ',' '\n' \
    | sed -n 's/^[[:space:]]*DNS://p'
)"

for expected_domain in "${EXPECTED_DOMAINS[@]}"; do
  if ! grep -Fxq "$expected_domain" <<< "$CERTIFICATE_DOMAINS"; then
    echo "Certificate '$CERT_NAME' does not cover $expected_domain."
    exit 1
  fi
done

if ! openssl x509 -in "$CERT_PATH" -noout -checkend "$MIN_VALIDITY_SECONDS"; then
  echo "Certificate '$CERT_NAME' expires in less than ${MIN_VALIDITY_SECONDS} seconds."
  exit 1
fi

echo "Certificate is valid for all ${#EXPECTED_DOMAINS[@]} configured domains."
