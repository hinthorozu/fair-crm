# Günlük yedek (yerel + Google Drive)

Her gün proje dosyalarını, PostgreSQL veritabanlarını ve sunucu ayarlarını yedekler; yedeği önce sunucuya yazar, sonra Google Drive'a yükler.

| Dosya | Görevi |
|---|---|
| `install-backup.sh` | Bir sunucuya kurulum: rclone, Drive bağlantısı, ayar dosyası, cron, logrotate |
| `kyrox-backup.sh` | Her gece çalışan yedek betiği (`/usr/local/sbin/kyrox-backup` olarak kurulur) |

## Kurulum

```bash
sudo bash /opt/fair-crm/scripts/server/backup/install-backup.sh
```

Betik `/opt` altındaki git projelerini ve Docker'daki PostgreSQL konteynerlerini kendisi bulur. Drive bağlantısı için bir kez onay ister:

1. Tarayıcısı olan bilgisayarda rclone kurun (Windows: `winget install Rclone.Rclone`).
2. `rclone authorize "drive"` çalıştırın, açılan sayfada Google hesabıyla izin verin.
3. Çıkan `{"access_token": ...}` satırını sunucudaki soruya yapıştırın.

Kurulum sonunda bir deneme yedeği alınır ve Drive'a yüklenir.

Seçenekler: `--time 03:30`, `--remote-name gdrive`, `--drive-folder Kyrox-Yedek`, `--skip-drive` (yalnız yerel), `--no-test`.

## Neler yedeklenir

- **Projeler** (`APP_DIRS`): `.env`, `.git`, yüklenen dosyalar ve `data/` dahil. `.venv`, `node_modules` ve `dist` atlanır; bunlar deploy ile yeniden kurulur. `fair-crm/backups` (uygulamanın kendi dump'ları) atlanır, veritabanları ayrıca yedeklenir.
- **Veritabanları** (`PG_CONTAINERS`): her konteyner için roller (`__globals.sql`) ve `postgres` dışındaki her veritabanı (`pg_dump -Fc`).
- **Sunucu ayarları**: `/etc/nginx`, `/etc/letsencrypt`, `/etc/systemd/system`, `/etc/cron.d`, `/etc/fair-crm`, root crontab, paket ve Docker listeleri.

Her yedek klasöründe `MANIFEST.txt` ve `SHA256SUMS` bulunur. Drive'a yükleme `rclone check` ile doğrulanır.

Yedekler şifrelenmez. `.env` dosyaları ve SSL anahtarları içerdiğinden Drive hesabının güvenliği (iki adımlı doğrulama) önemlidir.

## Ayarlar

`/etc/kyrox-backup.env` dosyasından değiştirilir; bir sonraki çalıştırmada geçerli olur.

| Ayar | Varsayılan |
|---|---|
| `BACKUP_ROOT` | `/var/backups/kyrox` |
| `LOCAL_RETENTION_DAYS` | 3 |
| `REMOTE_RETENTION_DAYS` | 14 (eski yedekler Drive çöp kutusuna gitmeden silinir) |
| `RCLONE_REMOTE` | `gdrive:Kyrox-Yedek/<sunucu adı>`; boşsa Drive'a yüklenmez |
| `MIN_FREE_MB` | 2048; daha az boş yer varsa yedek başlamaz |

Log: `/var/log/kyrox-backup.log`. Elle çalıştırma: `sudo kyrox-backup`.

## Geri yükleme

```bash
# Drive'dan indir
rclone copy gdrive:Kyrox-Yedek/<sunucu>/<tarih> /root/restore
cd /root/restore && sha256sum -c SHA256SUMS

# Proje dosyaları
tar -C /opt -xzpf app/fair-crm.tar.gz

# Veritabanı (önce roller, sonra veritabanı)
docker exec -i kyrox-postgres-dev psql -U postgres < db/kyrox-postgres-dev__globals.sql
docker exec -i kyrox-postgres-dev pg_restore -U postgres -d postgres --create --clean --if-exists < db/kyrox-postgres-dev__fair_crm.dump
```

Ardından `.venv` ve `node_modules` için `scripts/server/deploy-all.sh` çalıştırılır.
