#!/bin/bash
set -e  # stop immediately if any command fails

cd /home/ec2-user/ThomasGia

DOMAIN="${CERTBOT_DOMAIN:-mindmetric.store}"
CERT_NAME="${CERTBOT_CERT_NAME:-$DOMAIN}"
DOMAIN_FILE="${CERTBOT_TENANT_DOMAIN_FILE:-deploy/tenant_domains.txt}"
CERTBOT_AUTO_SETUP="${CERTBOT_AUTO_SETUP:-true}"
CERTBOT_AUTO_RENEW="${CERTBOT_AUTO_RENEW:-true}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-support@mindmetric.store}"

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

echo "Checking TLS coverage for configured tenant domains..."
if command -v certbot >/dev/null 2>&1 && [[ "$CERTBOT_AUTO_RENEW" == "true" ]]; then
  if ! sudo certbot renew --quiet; then
    echo "WARNING: Certbot renewal did not complete. Validating the installed certificate."
  fi
fi

if ! sudo bash deploy/check_certificate_domains.sh "$DOMAIN" "$CERT_NAME" "$DOMAIN_FILE"; then
  if [[ "$CERTBOT_AUTO_SETUP" == "true" ]]; then
    if [[ -z "$CERTBOT_EMAIL" ]]; then
      echo "CERTBOT_EMAIL is required when CERTBOT_AUTO_SETUP=true."
      exit 1
    fi
    deploy/setup_certbot_nginx.sh "$DOMAIN" "$CERTBOT_EMAIL"
  else
    echo "Deployment stopped because HTTPS does not cover every configured domain."
    echo "Point all domains in $DOMAIN_FILE to this server, then run:"
    echo "  ./deploy/setup_certbot_nginx.sh ${DOMAIN} your-email@example.com"
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
