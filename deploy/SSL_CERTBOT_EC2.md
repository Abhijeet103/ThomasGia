# Certbot SSL Setup On EC2

This project already includes:

- `deploy/mindmetric.conf` for nginx
- `deploy/mindmetric.service` for the Django ASGI app
- `deploy/setup_certbot_nginx.sh` to install Certbot and request the certificate

## 1. Point the domain to EC2

In GoDaddy DNS, make sure:

- `A` record for `@` points to your EC2 Elastic IP
- `A` record for `www` points to the same Elastic IP, or `CNAME` to `@`

Wait for DNS to resolve before requesting the certificate.

## 2. Deploy the nginx config

From the EC2 server:

```bash
cd /home/ec2-user/ThomasGia
sudo cp deploy/mindmetric.conf /etc/nginx/conf.d/mindmetric.conf
sudo mkdir -p /var/www/certbot
sudo nginx -t
sudo systemctl restart nginx
```

## 3. Request the SSL certificate

```bash
cd /home/ec2-user/ThomasGia
chmod +x deploy/setup_certbot_nginx.sh
./deploy/setup_certbot_nginx.sh mindmetric.store www.mindmetric.store your-email@example.com
```

Certbot will:

- install the nginx plugin
- issue the certificate
- update nginx for HTTPS
- add HTTP to HTTPS redirect

## 4. Django settings to confirm

Make sure production env includes:

```env
DEBUG=False
DJANGO_ALLOWED_HOSTS=mindmetric.store,www.mindmetric.store,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://mindmetric.store,https://www.mindmetric.store
```

And in Django settings you should keep:

- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`

## 5. Renewal check

Run:

```bash
sudo certbot renew --dry-run
```

If that passes, renewal is ready.
