# Certbot SSL Setup On EC2

This project already includes:

- `deploy/mindmetric.conf` for nginx
- `deploy/mindmetric.service` for the Django ASGI app
- `deploy/setup_certbot_nginx.sh` to install Certbot and request the certificate

## 1. Point the domain to EC2

In GoDaddy DNS, make sure:

- `A` record for `@` points to your EC2 Elastic IP
- `A` record for `www` points to the same Elastic IP, or `CNAME` to `@`
- `A` record for `*` points to the same EC2 Elastic IP

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
chmod +x deploy/check_wildcard_certificate.sh
./deploy/setup_certbot_nginx.sh mindmetric.store your-email@example.com
```

Certbot will:

- install the nginx plugin
- request one certificate for `mindmetric.store` and `*.mindmetric.store`
- prompt for the `_acme-challenge` TXT record in GoDaddy
- preserve the certificate name as `mindmetric.store`
- install the expanded certificate into nginx and enable HTTPS redirects

## Wildcard certificate for tenant subdomains

The normal nginx/HTTP challenge cannot issue `*.mindmetric.store`, so the setup
script uses a DNS challenge. One wildcard certificate covers `www` and every
first-level tenant such as `demo.mindmetric.store`; do not issue a separate
certificate for every tenant.

Manual DNS certificates do not renew unattended. For automated deployment,
provide two executable scripts that create and remove the requested DNS TXT
record:

```bash
export CERTBOT_DNS_AUTH_HOOK=/secure/path/certbot-dns-auth
export CERTBOT_DNS_CLEANUP_HOOK=/secure/path/certbot-dns-cleanup
./deploy/setup_certbot_nginx.sh mindmetric.store your-email@example.com
```

Certbot passes values such as `CERTBOT_DOMAIN`, `CERTBOT_VALIDATION`, and
`CERTBOT_REMAINING_CHALLENGES` to these hooks. Keep DNS API credentials outside
the repository and restrict the hook file permissions.

## Deployment behavior

`deploy/deploy.sh` now:

- optionally runs `certbot renew`
- verifies that the installed certificate contains `*.mindmetric.store`
- verifies that the certificate has at least seven days remaining
- stops safely rather than deploying tenant hosts with invalid TLS

Supported environment variables:

```env
CERTBOT_DOMAIN=mindmetric.store
CERTBOT_CERT_NAME=mindmetric.store
CERTBOT_AUTO_RENEW=true
CERTBOT_AUTO_SETUP=false
CERTBOT_EMAIL=support@mindmetric.store
CERTBOT_DNS_AUTH_HOOK=/secure/path/certbot-dns-auth
CERTBOT_DNS_CLEANUP_HOOK=/secure/path/certbot-dns-cleanup
```

Keep `CERTBOT_AUTO_SETUP=false` when using the interactive GoDaddy TXT process.
Set it to `true` only when both DNS hook scripts are configured; otherwise a
non-interactive deployment can pause waiting for DNS input.

## 4. Django settings to confirm

Make sure production env includes:

```env
DEBUG=False
DJANGO_ALLOWED_HOSTS=mindmetric.store,www.mindmetric.store,.mindmetric.store,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://mindmetric.store,https://www.mindmetric.store,https://*.mindmetric.store
TENANT_BASE_DOMAIN=mindmetric.store
```

And in Django settings you should keep:

- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`

## 5. Renewal check

For a certificate issued with automated DNS hooks, run:

```bash
sudo certbot renew --dry-run
```

If manual DNS validation was used, rerun `setup_certbot_nginx.sh` before expiry
or configure the DNS hooks first. The deploy script will warn about renewal
errors and reject a certificate with less than seven days remaining.
