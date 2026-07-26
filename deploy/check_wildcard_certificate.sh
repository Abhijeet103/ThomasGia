#!/bin/bash
set -euo pipefail

DOMAIN="${1:-mindmetric.store}"
CERT_NAME="${2:-$DOMAIN}"
MIN_VALIDITY_SECONDS="${CERTBOT_MIN_VALIDITY_SECONDS:-604800}"
CERT_PATH="/etc/letsencrypt/live/${CERT_NAME}/fullchain.pem"

if [[ ! "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ || ! "$CERT_NAME" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Invalid certificate domain or name."
  exit 1
fi

if [[ ! -r "$CERT_PATH" ]]; then
  echo "Wildcard certificate not found: $CERT_PATH"
  exit 1
fi

if ! openssl x509 -in "$CERT_PATH" -noout -ext subjectAltName \
  | grep -Fq "DNS:*.${DOMAIN}"; then
  echo "Certificate '$CERT_NAME' does not cover *.${DOMAIN}."
  exit 1
fi

if ! openssl x509 -in "$CERT_PATH" -noout -checkend "$MIN_VALIDITY_SECONDS"; then
  echo "Certificate '$CERT_NAME' expires in less than ${MIN_VALIDITY_SECONDS} seconds."
  exit 1
fi

echo "Wildcard certificate is valid for *.${DOMAIN}."
