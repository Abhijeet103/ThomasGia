# Certbot SSL Setup On EC2

The deployment uses one certificate containing the apex domain, `www`, and
every tenant hostname listed in `deploy/tenant_domains.txt`. It does not require
a wildcard certificate or DNS TXT challenge.

## Add A Tenant Domain

Add one first-level hostname per line:

```text
demo.mindmetric.store
academy.mindmetric.store
```

Blank lines and lines beginning with `#` are ignored. Do not add
`mindmetric.store` or `www.mindmetric.store`; they are included automatically.

Before deploying, make sure every listed hostname resolves to the EC2 Elastic
IP. A wildcard DNS `A` record pointing `*.mindmetric.store` to EC2 can handle
this routing without adding a separate DNS record for each tenant.

## Initial Server Setup

```bash
cd /home/ec2-user/ThomasGia
chmod +x deploy/setup_certbot_nginx.sh
chmod +x deploy/check_certificate_domains.sh
./deploy/setup_certbot_nginx.sh mindmetric.store support@mindmetric.store
```

Certbot validates each exact hostname through nginx's HTTP challenge location,
installs the certificate, redirects HTTP to HTTPS, and enables its renewal
timer.

## Deployment Behavior

`deploy/deploy.sh`:

- reads tenant hostnames from `deploy/tenant_domains.txt`;
- renews the current certificate when appropriate;
- checks that every configured hostname is covered;
- automatically replaces or expands the certificate when a hostname is
  missing;
- rejects invalid hostnames and certificates with less than seven days left.

Supported environment variables:

```env
CERTBOT_DOMAIN=mindmetric.store
CERTBOT_CERT_NAME=mindmetric.store
CERTBOT_AUTO_RENEW=true
CERTBOT_AUTO_SETUP=true
CERTBOT_EMAIL=support@mindmetric.store
CERTBOT_TENANT_DOMAIN_FILE=deploy/tenant_domains.txt
```

The certificate authority allows at most 100 names on one certificate,
including the apex and `www`, leaving room for 98 tenant hostnames.

## Django Settings

```env
DEBUG=False
DJANGO_ALLOWED_HOSTS=mindmetric.store,www.mindmetric.store,.mindmetric.store,127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=https://mindmetric.store,https://www.mindmetric.store,https://*.mindmetric.store
TENANT_BASE_DOMAIN=mindmetric.store
```

Keep:

- `SECURE_SSL_REDIRECT = True`
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`

## Renewal Check

```bash
sudo certbot renew --dry-run
sudo bash deploy/check_certificate_domains.sh \
  mindmetric.store mindmetric.store deploy/tenant_domains.txt
```
