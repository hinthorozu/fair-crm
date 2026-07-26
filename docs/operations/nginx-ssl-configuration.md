# FAIR CRM Nginx + SSL Operasyon Rehberi

Bu doküman FAIR CRM uygulamasının domain üzerinden Nginx reverse proxy ile yayınlanması, Let's Encrypt SSL kurulması, 80/443 erişiminin açılması, doğrulama ve rollback adımlarını kapsar.

## 1. Ön Koşullar

- FAIR CRM sunucuda çalışıyor olmalı.
- Frontend build çıktısı mevcut olmalı.
- FAIR CRM backend `127.0.0.1:8001` üzerinde erişilebilir olmalı.
- Kyrox Core `127.0.0.1:8000` üzerinde erişilebilir olmalı.
- Nginx kurulu olmalı.
- Domain DNS kaydını değiştirme yetkisi olmalı.
- Root veya sudo yetkisi olmalı.

Mevcut domain:

```text
faircrm.umaay.com
```

Mevcut sunucu IP:

```text
64.226.110.223
```

## 2. DNS

A kaydı:

```text
Type: A
Host: faircrm
Value: 64.226.110.223
```

Doğrulama:

```bash
nslookup faircrm.umaay.com
```

veya:

```bash
dig +short faircrm.umaay.com
```

Beklenen:

```text
64.226.110.223
```

DNS doğru IP'ye çözülmeden Certbot çalıştırma.

## 3. Nginx Site Yapısı

Site dosyası:

```text
/etc/nginx/sites-available/fair-crm
```

Enabled symlink:

```text
/etc/nginx/sites-enabled/fair-crm
```

Repo template:

```text
scripts/server/nginx/fair-crm.conf
```

Mevcut yönlendirme:

```text
/             -> frontend/dist
/api/         -> http://127.0.0.1:8001
/kyrox-core/  -> http://127.0.0.1:8000/
```

## 4. Domain'i Nginx'e Bağlama

Dosyayı aç:

```bash
nano /etc/nginx/sites-available/fair-crm
```

Şunu:

```nginx
server_name _;
```

şuna çevir:

```nginx
server_name faircrm.umaay.com;
```

Temel örnek:

```nginx
server {
    listen 80;
    listen [::]:80;

    server_name faircrm.umaay.com;

    root /opt/fair-crm/frontend/dist;
    index index.html;

    client_max_body_size 64m;

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    location /kyrox-core/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Deploy dizini farklıysa `root` yolunu gerçek dizine göre değiştir.

## 5. Nginx Doğrulama ve Reload

```bash
nginx -t
```

Başarılı olmadan reload yapma.

```bash
systemctl reload nginx
systemctl status nginx --no-pager
```

HTTP kontrol:

```bash
curl -I http://faircrm.umaay.com
```

## 6. Firewall

```bash
ufw status
```

Gerekirse:

```bash
ufw allow 80/tcp
ufw allow 443/tcp
```

Tekrar:

```bash
ufw status
```

SSL kurulmuş olsa bile 443 kapalıysa tarayıcı HTTPS bağlantısı başarısız olur.

## 7. Certbot Kurulumu

```bash
apt update
apt install -y certbot python3-certbot-nginx
```

Kontrol:

```bash
certbot --version
```

## 8. Let's Encrypt SSL

```bash
certbot --nginx -d faircrm.umaay.com
```

Certbot sırasında:

- geçerli yönetici e-postası gir,
- kullanım şartlarını kabul et,
- HTTP -> HTTPS redirect seçeneğini etkinleştir.

Sertifika dosyaları tipik olarak:

```text
/etc/letsencrypt/live/faircrm.umaay.com/fullchain.pem
/etc/letsencrypt/live/faircrm.umaay.com/privkey.pem
```

## 9. SSL Sonrası Kontrol

```bash
nginx -t
systemctl reload nginx
curl -I https://faircrm.umaay.com
```

Tarayıcı:

```text
https://faircrm.umaay.com
```

Frontend, login ve API çağrılarını kontrol et.

## 10. Sertifika Bilgisi

```bash
certbot certificates
```

Alternatif:

```bash
openssl s_client -connect faircrm.umaay.com:443 -servername faircrm.umaay.com </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
```

## 11. Otomatik Renewal

```bash
systemctl status certbot.timer --no-pager
systemctl list-timers | grep certbot
```

Dry-run:

```bash
certbot renew --dry-run
```

Manuel yenileme:

```bash
certbot renew
```

## 12. Reverse Proxy Kontrolleri

FAIR CRM backend:

```bash
curl -I http://127.0.0.1:8001
```

Kyrox Core:

```bash
curl -I http://127.0.0.1:8000
```

Public API:

```bash
curl -I https://faircrm.umaay.com/api/
```

Public Kyrox Core:

```bash
curl -I https://faircrm.umaay.com/kyrox-core/
```

Localhost çalışıyor ama public route çalışmıyorsa Nginx routing/config tarafını kontrol et.

## 13. Yaygın Sorunlar

### DNS yanlış IP

```bash
dig +short faircrm.umaay.com
```

Domain sunucu IP'sini göstermeli.

### `nginx -t` hata veriyor

Syntax hatasını düzelt. `nginx -t` başarılı olmadan reload/restart yapma.

### HTTPS connection reset / timeout

```bash
ufw status
ss -lntp | grep ':443'
```

443 kapalıysa:

```bash
ufw allow 443/tcp
```

### Certbot domain doğrulayamıyor

```bash
dig +short faircrm.umaay.com
curl -I http://faircrm.umaay.com
ufw status
```

DNS doğru olmalı, port 80 internetten erişilebilir olmalı, Nginx domaini karşılamalıdır.

### API 502

```bash
curl -I http://127.0.0.1:8001
ss -lntp | grep ':8001'
```

### Kyrox Core 502

```bash
curl -I http://127.0.0.1:8000
ss -lntp | grep ':8000'
```

## 14. Rollback

Değişiklikten önce yedek:

```bash
cp /etc/nginx/sites-available/fair-crm \
   /etc/nginx/sites-available/fair-crm.backup
```

Geri dön:

```bash
cp /etc/nginx/sites-available/fair-crm.backup \
   /etc/nginx/sites-available/fair-crm
nginx -t
systemctl reload nginx
```

SSL satırlarını kontrol etmek için:

```bash
grep -n "ssl_certificate\|server_name\|listen" /etc/nginx/sites-available/fair-crm
```

Sertifikaları silmeden önce problemi DNS, firewall ve Nginx config seviyesinde doğrula.

## 15. Hızlı Checklist

```bash
dig +short faircrm.umaay.com
nginx -t
systemctl is-active nginx
ufw status
curl -I http://faircrm.umaay.com
curl -I https://faircrm.umaay.com
certbot certificates
certbot renew --dry-run
```

Beklenen:

- DNS doğru IP'ye çözülür.
- Nginx config geçerlidir.
- Nginx aktiftir.
- 80 ve 443 açıktır.
- HTTP çalışır ve HTTPS'e yönlenir.
- HTTPS cevap verir.
- Sertifika geçerlidir.
- Renewal dry-run başarılıdır.

## 16. FAIR CRM'e Özel Not

Repo içindeki mevcut Nginx template domain bağımsızdır ve:

```nginx
server_name _;
```

kullanır.

Domain + SSL kurulumu şu an deploy scriptlerinin dışında operasyonel olarak yapılmaktadır. İleride otomasyona alınırken mevcut reverse proxy yapısı korunarak domain, firewall ve Certbot adımları deploy/setup scriptine eklenmelidir.
