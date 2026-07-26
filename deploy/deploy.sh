#!/bin/bash
set -e  # stop immediately if any command fails

cd /home/ec2-user/ThomasGia

DOMAIN="${CERTBOT_DOMAIN:-mindmetric.store}"
CERT_NAME="${CERTBOT_CERT_NAME:-$DOMAIN}"
CERTBOT_AUTO_SETUP="${CERTBOT_AUTO_SETUP:-false}"
CERTBOT_AUTO_RENEW="${CERTBOT_AUTO_RENEW:-true}"

echo "Fetching latest code from origin..."
git fetch origin

echo "Resetting working tree to origin/main..."
git reset --hard origin/main

echo "Activating venv and installing dependencies..."
source .venv/bin/activate
pip install -r requirements.txt

echo "Configured database target:"
python manage.py shell -c "from django.conf import settings; db = settings.DATABASES['default']; print(f\"  engine={db['ENGINE']} host={db.get('HOST') or 'local'} name={db['NAME']}\")"

echo "Validating production settings..."
python manage.py shell -c "from django.conf import settings; assert not (settings.IS_PRODUCTION and settings.DEBUG), 'DJANGO_DEBUG must be False in production'; assert not (settings.IS_PRODUCTION and settings.SITE_URL.rstrip('/') != 'https://mindmetric.store'), 'SITE_URL must be https://mindmetric.store in production'; print(f'  environment={settings.DJANGO_ENV} debug={settings.DEBUG} site_url={settings.SITE_URL}')"

echo "Running migrations..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Running Django system checks..."
python manage.py check

echo "Copying config files..."
sudo cp deploy/mindmetric.service /etc/systemd/system/mindmetric.service
sudo mkdir -p /var/www/certbot
echo "Syncing nginx site config without overwriting Certbot-managed HTTPS settings..."
if [ -f /etc/nginx/conf.d/mindmetric.conf ]; then
  sudo cp /etc/nginx/conf.d/mindmetric.conf /etc/nginx/conf.d/mindmetric.conf.bak
  sudo python3 deploy/sync_nginx_conf.py /etc/nginx/conf.d/mindmetric.conf
else
  sudo cp deploy/mindmetric.conf /etc/nginx/conf.d/mindmetric.conf
fi

echo "Checking TLS coverage for tenant subdomains..."
if command -v certbot >/dev/null 2>&1 && [[ "$CERTBOT_AUTO_RENEW" == "true" ]]; then
  if ! sudo certbot renew --quiet; then
    echo "WARNING: Certbot renewal did not complete. Validating the installed certificate."
  fi
fi

if ! sudo bash deploy/check_wildcard_certificate.sh "$DOMAIN" "$CERT_NAME"; then
  if [[ "$CERTBOT_AUTO_SETUP" == "true" ]]; then
    if [[ -z "${CERTBOT_EMAIL:-}" ]]; then
      echo "CERTBOT_EMAIL is required when CERTBOT_AUTO_SETUP=true."
      exit 1
    fi
    deploy/setup_certbot_nginx.sh "$DOMAIN" "$CERTBOT_EMAIL"
  else
    echo "Deployment stopped because HTTPS does not cover *.${DOMAIN}."
    echo "Run this once, complete the DNS TXT challenge, and deploy again:"
    echo "  ./deploy/setup_certbot_nginx.sh ${DOMAIN} your-email@example.com"
    echo "For unattended setup/renewal, configure executable"
    echo "CERTBOT_DNS_AUTH_HOOK and CERTBOT_DNS_CLEANUP_HOOK scripts."
    exit 1
  fi
fi

echo "Fixing static file permissions..."
sudo chmod -R o+rx /home/ec2-user
sudo chmod -R o+rx /home/ec2-user/ThomasGia/staticfiles

echo "Reloading services..."
sudo systemctl daemon-reload
sudo nginx -t
sudo systemctl restart mindmetric
sudo systemctl restart nginx

echo "Deploy complete."
sudo systemctl status mindmetric --no-pager
