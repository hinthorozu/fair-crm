# Günlük yedek (sunucu + Google Drive)

Her gün proje dosyalarını, PostgreSQL veritabanlarını ve sunucu ayarlarını yedekler. Yedek önce sunucuya yazılır, sonra Google Drive'a yüklenir.

| Dosya | Görevi |
|---|---|
| `install-backup.sh` | Kurulum sihirbazı: adım adım sorar, ayarları yazar, cron ve Drive bağlantısını kurar |
| `kyrox-backup.sh` | Her gece çalışan yedek (`/usr/local/sbin/kyrox-backup` olarak kurulur) |

## Kurulum: adım adım

Sunucuya bağlanın ve sihirbazı çalıştırın:

```bash
sudo bash /opt/kyrox/kyrox-fair-crm/scripts/server/backup/install-backup.sh
```

Bilgisayarınızdan tek komutla bağlanıp başlatmak için (`-t` şart, yoksa sihirbaz soru soramaz):

```bash
ssh -t kullanici@sunucu "sudo bash /opt/kyrox/kyrox-fair-crm/scripts/server/backup/install-backup.sh"
```

Her soruda köşeli parantezdeki değer varsayılandır. Kabul etmek için yalnızca Enter'a basın.

**Adım 1: Proje klasörleri.** Sihirbaz `/opt/kyrox` (ve eski düzen için `/opt`) altındaki git projelerini bulup gösterir, ör. `[/opt/kyrox/kyrox-fair-crm /opt/kyrox/kyrox-fair-stand /opt/kyrox/kyrox-core]`. Doğruysa Enter. Eksik ya da fazla varsa klasörleri boşlukla ayırarak yazın.

**Adım 2: Veritabanları.** Çalışan PostgreSQL Docker konteynerlerini gösterir, ör. `[kyrox-postgres-dev]`. Doğruysa Enter. Konteynerdeki bütün veritabanları yedeklenir.

**Adım 3: Saat.** Yedeğin her gün alınacağı saat, ör. `[03:30]`. Enter ya da `04:00` gibi bir saat.

**Adım 4: Sunucuda kaç gün.** `[3]`. Sunucuda en son kaç günün yedeği tutulsun.

**Adım 5: Google Drive.**
- `Yedekler Google Drive'a da yüklensin mi? [E/h]`: Enter (evet). Yalnız sunucuda tutmak için `h`.
- `Drive'daki klasör adı [Kyrox-Yedek]`: Enter.
- `Drive'da kaç gün [14]`: Enter.

**Adım 6: Özet.** Seçtikleriniz listelenir. `Bu ayarlarla kurulsun mu? [E/h]`: Enter.

**Google hesabı izni (yalnız ilk kurulumda).** Sihirbaz bir token ister. Bu kısım **sunucuda değil, kendi bilgisayarınızda** yapılır:

1. Bilgisayarınızda PowerShell açın, rclone'u kurun (bir kez yeterli):
   ```bash
   winget install Rclone.Rclone
   ```
   PowerShell'i kapatıp yeniden açın.
2. Şunu çalıştırın:
   ```bash
   rclone authorize "drive"
   ```
3. Tarayıcı açılır. Yedeklerin gideceği Google hesabıyla giriş yapıp izin verin. "Success" yazısını görünce PowerShell'e dönün.
4. PowerShell'de `{"access_token":` ile başlayıp `}` ile biten uzun satırın **tamamını** kopyalayın.
5. Sunucudaki `Token:` sorusuna yapıştırıp Enter'a basın.

Token yanlışsa sihirbaz tekrar ister. Vazgeçmek için boş bırakıp Enter'a basın; yedek yalnız sunucuda tutulur, Drive'ı sonra sihirbazı tekrar çalıştırarak bağlayabilirsiniz.

**Adım 7: Kurulum.** Sihirbaz ayarları yazar, yedeği zamanlar ve sorar: `Şimdi bir deneme yedeği alınsın mı? [E/h]`. Enter. Birkaç dakika sonra `Deneme yedeği başarılı.` yazısını görürsünüz; Drive'da `Kyrox-Yedek/<sunucu adı>/<tarih>` klasörü oluşur.

Bundan sonra yedek her gün kendiliğinden alınır; bir şey yapmanız gerekmez.

## Sonradan

| Ne | Nasıl |
|---|---|
| Ayarları değiştirmek | Sihirbazı tekrar çalıştırın; önceki cevaplar varsayılan olarak gelir |
| Drive'ı başka hesaba bağlamak | Sihirbazı tekrar çalıştırın, "Başka bir Google hesabına bağlamak ister misiniz?" sorusuna `e` |
| Elle yedek almak | `sudo kyrox-backup` |
| Son yedeğin sonucunu görmek | `tail -30 /var/log/kyrox-backup.log` |
| Soru sormadan kurmak | `sudo bash .../install-backup.sh --yes` (Drive bağlantısı yoksa yalnız sunucuda tutar) |

Google hesabının şifresi değişirse ya da rclone'un erişimi kaldırılırsa Drive yüklemesi durur; logda hata görünür. Sihirbazı tekrar çalıştırıp yeni token yapıştırın.

## Neler yedeklenir

- **Projeler**: `.env`, `.git`, yüklenen dosyalar ve `data/` dahil. `.venv`, `node_modules` ve `dist` atlanır; bunlar deploy ile yeniden kurulur. `kyrox-fair-crm/backups` (uygulamanın kendi dump'ları) atlanır, veritabanları ayrıca yedeklenir.
- **Veritabanları**: her konteyner için roller (`__globals.sql`) ve `postgres` dışındaki her veritabanı (`pg_dump -Fc`).
- **Sunucu ayarları**: `/etc/nginx`, `/etc/letsencrypt`, `/etc/systemd/system`, `/etc/cron.d`, `/etc/fair-crm`, root crontab, paket ve Docker listeleri.

Her yedek klasöründe `MANIFEST.txt` ve `SHA256SUMS` bulunur. Drive'a yükleme `rclone check` ile doğrulanır. Drive'daki eski yedekler çöp kutusuna gitmeden silinir.

Yedekler şifrelenmez. `.env` dosyaları ve SSL anahtarları içerdiğinden Google hesabında iki adımlı doğrulama açık olmalı.

Ayarlar `/etc/kyrox-backup.env` dosyasındadır (sihirbaz yazar).

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
