# Günlük yedek (sunucu + Google Drive)

Her gün proje dosyalarını, PostgreSQL veritabanlarını ve sunucu ayarlarını yedekler. Yedek önce sunucuya yazılır, sonra Google Drive'a yüklenir.

| Dosya | Görevi |
|---|---|
| `install-backup.sh` | Kurulum sihirbazı: adım adım sorar, ayarları yazar, cron ve Drive bağlantısını kurar |
| `kyrox-backup.sh` | Her gece çalışan yedek (`/usr/local/sbin/kyrox-backup` olarak kurulur) |
| `kyrox-restore.sh` | Geri yükleme sihirbazı ve `--deneme` ile canlıya dokunmayan tatbikat (aşağıda) |

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

**Adım 2: Veritabanları.** Çalışan PostgreSQL Docker konteynerlerini gösterir, ör. `[kyrox-db]`. Doğruysa Enter. Konteynerdeki bütün veritabanları yedeklenir.

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
- **PostgreSQL** (`PG_CONTAINERS`): her konteyner için roller (`__globals.sql`) ve `postgres` dışındaki her veritabanı (`pg_dump -Fc`).
- **MariaDB/MySQL** (`MYSQL_CONTAINERS`, ör. kyrox.studio WordPress veritabanı): bütün veritabanları, kullanıcılar ve yetkiler tek tutarlı dump olarak (`__all.sql.gz`). Root şifresi konteynerin kendi ortamından okunur; ayar dosyasına yazılmaz.
- **Docker volume'ları** (`VOLUMES`, ör. `kyrox-web-html`): WordPress dosyaları ve yüklenen görseller olduğu gibi arşivlenir (`volume/<ad>.tar.gz`).
- **Sunucu ayarları**: `/etc/nginx`, `/etc/letsencrypt`, `/etc/systemd/system`, `/etc/cron.d`, `/etc/fair-crm`, root crontab, paket ve Docker listeleri.

Her yedek klasöründe `MANIFEST.txt` ve `SHA256SUMS` bulunur. Drive'a yükleme `rclone check` ile doğrulanır. Drive'daki eski yedekler çöp kutusuna gitmeden silinir.

Yedekler şifrelenmez. `.env` dosyaları ve SSL anahtarları içerdiğinden Google hesabında iki adımlı doğrulama açık olmalı.

Ayarlar `/etc/kyrox-backup.env` dosyasındadır (sihirbaz yazar).

## Geri yükleme: `kyrox-restore.sh`

### Tatbikat (canlıya dokunmaz)

Yedeğin gerçekten geri yüklenebildiğini, çalışan sunucuda hiçbir şeyi değiştirmeden sınar:

```bash
ssh -t kullanici@sunucu "sudo bash /opt/kyrox/kyrox-fair-crm/scripts/server/backup/kyrox-restore.sh --deneme"
```

Sağlama toplamlarını ve arşivleri kontrol eder. PostgreSQL dökümlerini geçici bir kapsayıcıya açıp tablo sayılarını dökümle karşılaştırır, MariaDB dökümünü de geçici bir kapsayıcıya açar. Proje, volume ve ayar arşivlerindeki dosyaları sayar. Bitince geçici kapsayıcıları siler. En son `Tatbikat başarılı` yazmalı.

### Yeni sunucuya taşıma

1. Boş Ubuntu'da altyapıyı kurun:
   ```bash
   sudo apt update && sudo apt install -y git
   sudo git clone https://github.com/kyrox-studio/kyrox-fair-crm.git /opt/kyrox/kyrox-fair-crm
   sudo bash /opt/kyrox/kyrox-fair-crm/scripts/server/bootstrap-server.sh
   ```
2. Sihirbazı çalıştırın:
   ```bash
   sudo bash /opt/kyrox/kyrox-fair-crm/scripts/server/backup/kyrox-restore.sh
   ```

| Adım | Ne olur | Ne yazarsınız |
|---|---|---|
| 1. Ön kontroller | root, docker; sunucuda çalışan Kyrox servisi varsa uyarır ve onay ister (varsayılan hayır) | — |
| 2. Yedeği seç | Sunucudaki yedekleri listeler; yoksa ya da istemezseniz Drive'dan seçtirir (gerekirse Drive token'ı ister, kurulumdaki gibi) | numara (Enter = en yeni) |
| 3. Sağlamlık | `SHA256SUMS` ve bütün arşivler kontrol edilir; içerik listelenir | — |
| 4. Neler | Projeler, PostgreSQL, WordPress, sunucu ayarları ayrı ayrı sorulur; Kyrox servisleri durdurulur | Enter… |
| 5. Projeler | `/opt/kyrox/<ad>` olarak açılır (`.env` dahil). Var olan klasör silinmez, kenara alınır. Eski düzenin `fair-crm` yedeği `kyrox-fair-crm` olarak açılır | — |
| 6. PostgreSQL | `kyrox-db` gerekirse başlatılır; önce roller, sonra her veritabanı geri yüklenir. Var olan veritabanının önce kopyası alınır. Tablo sayısı dökümle karşılaştırılır | Enter, onay |
| 7. WordPress | MariaDB dökümü ve WordPress dosyaları (`kyrox-web-html`) geri yüklenir; önceki halin kopyası alınır | — |
| 8. Sunucu ayarları | nginx, SSL sertifikaları, Kyrox servis tanımları, cron, `/etc/fair-crm`, yedek ayarı ayrı ayrı sorulur. `nginx -t` geçmezse nginx yeniden yüklenmez | Enter… |
| 9. Başlat | `deploy-all.sh` (bağımlılıklar, şema güncellemesi, servisler) çalıştırılır; sağlık kontrolü yazılır | Enter |

Üzerine yazılan her şeyin (klasörler, veritabanları, volume'lar, ayar dosyaları) kopyası `/var/backups/kyrox/geri-yukleme-oncesi-<tarih>/` altında kalır.

3. Bilgisayarınızın `hosts` dosyasına yeni IP'yi yazıp siteleri deneyin. Eski sunucu bu sırada çalışmaya devam eder.
4. Natro'da A kayıtlarını yeni IP'ye çevirin. MX kayıtlarına dokunmayın.
5. Gece yedeğini yeni sunucuda kurun (`install-backup.sh`); DNS yayılınca `sudo certbot renew --dry-run`.
