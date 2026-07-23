#!/bin/bash
set -e  # stop immediately if any command fails

cd /home/ec2-user/ThomasGia

echo "Fetching latest code from origin..."
git fetch origin

echo "Resetting working tree to origin/main..."
git reset --hard origin/main

echo "Activating venv and installing dependencies..."
source .venv/bin/activate
pip install -r requirements.txt

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
