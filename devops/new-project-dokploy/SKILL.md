---
name: new-project-dokploy
description: Yeni bir proje/uygulama/site oluşturur, Dockerize eder, GitHub'a pushlar, Dokploy API ile *.zenbil.site üzerinde deploy eder ve canlılık testini yapar.
---

# Skill: Otomatik Proje Geliştirme ve Dokploy Deploy

## Açıklama
Bu skill, kullanıcı yeni bir proje, web sitesi veya servis geliştirilmesini istediğinde tüm uçtan uca süreci otomatize eder:
1. `projects/` dizininde yeni proje klasörü oluşturma ve geliştirme.
2. Dockerfile ve docker-compose (iç port 3000 - expose) yapılandırması.
3. GitHub üzerinde repo oluşturup kodları pushlama.
4. Dokploy REST API kullanarak projeyi oluşturma, Git reponuzu bağlama, `*.zenbil.site` subdomain'i ekleme ve deploy etme.
5. Deployment sonrası canlılık (health check) doğrulama testi.

---

## Çevre Değişkenleri ve Konfigürasyon (Environment Variables)

Hermes Agent çalıştırmadan önce çevre değişkenlerini aşağıdaki konfigürasyon dosyalarından otomatik olarak yüklemelidir:

- `~/.config/hermes/dokploy.env`
- `~/.config/hermes/github.env`
- `~/.config/hermes/supabase.env`

### Ortam Değişkenlerini Yükleme (Source Command):
```bash
set -a
source "$HOME/.config/hermes/dokploy.env"
source "$HOME/.config/hermes/github.env"
source "$HOME/.config/hermes/supabase.env"
set +a
```

### Paylaşımlı Supabase Backend Entegrasyonu (Shared Supabase Backend)

Geliştirilen projelerde **veritabanı, kullanıcı kimlik doğrulaması (Auth), veri depolama (Storage) veya REST API (Backend)** ihtiyacı olduğunda, her proje için ayrı bir veritabanı kurmak yerine Dokploy üzerindeki `shared-project` projesinde çalışan ortak **Supabase** servisi kullanılmalıdır.

#### Supabase Erişim Bilgileri (`~/.config/hermes/supabase.env`):
Projelerde ihtiyaç duyulduğunda aşağıdaki ortam değişkenleri uygulama `environment` / `.env` dosyasına aktarılmalıdır:
```env
SUPABASE_URL="https://supabase.zenbil.site"
SUPABASE_ANON_KEY="..."         # İstemci / Client tarafı anonim anahtarı
SUPABASE_SERVICE_ROLE_KEY="..." # Sunucu / Server tarafı yetkili anahtarı
DATABASE_URL="postgresql://postgres:...@supabase.zenbil.site:5432/postgres" # Doğrudan PostgreSQL erişimi
```

#### Kurallar:
1. **Ortak Kullanım:** Backend/DB gereksinimi olan tüm yeni projeler aynı Supabase instance'ını kullanmalıdır.
2. **Kalıcılık (Data Persistence):** Dokploy üzerinde Supabase veritabanı verilerinin silinmemesi için kalıcı volume (`supabase_db_data`) yapılandırması kullanılır.
3. **Tablo/Şema Yönetimi:** Her proje kendi tablolarını ana veritabanında (veya projeye özel PostgreSQL şemasında) oluşturabilir veya Supabase JS Client (`@supabase/supabase-js`) ile erişebilir.

### Beklenen Değişkenler:

**`~/.config/hermes/dokploy.env` İçeriği:**
```env
DOKPLOY_URL="xxxx"          # Örn: https://panel.zenbil.site
DOKPLOY_API_KEY="xxxx"      # Dokploy API anahtarı
DOKPLOY_PROJECT_ID="xxxx"   # Servislerin ekleneceği Dokploy Proje ID'si
```

**`~/.config/hermes/github.env` İçeriği:**
```env
GITHUB_TOKEN="xxxx"         # GitHub Personal Access Token (repo oluşturma/push izni)
GITHUB_USERNAME="xxxx"      # GitHub kullanıcı adı veya organizasyon adı
```

---

## İş Akışı Adımları (Workflow Steps)

### Adım 0: Ortam Değişkenlerini Hazırlama
İşlemlere başlamadan önce konfigürasyon dosyalarını yükle:
```bash
set -a
source "$HOME/.config/hermes/dokploy.env"
source "$HOME/.config/hermes/github.env"
set +a
```

---

### Adım 1: Proje Başlatma ve Geliştirme
1. Proje dizininde `projects/` altında projeye özel bir klasör aç: `projects/<proje-adi>`
2. İstenen uygulamayı/siteyi bu klasör içinde geliştir.
3. Uygulamanın dahili portunun **3000** olduğundan emin ol (istisna: nginx ile servis edilen statik HTML siteleri varsayılan olarak **80** portunu kullanır — bu durumda `expose: "80"` ve `domain.create` portu 80 olmalıdır).
4. Kök dizine `Dockerfile` ve `docker-compose.yml` ekle.
5. **ÖNEMLİ:** Sunucuda port çakışması yaşanmaması için `ports:` bağlaması yapılmamalı, container içi port `expose:` ile açılmalıdır. Dokploy/Traefik yönlendirmeyi bu iç ağ portu üzerinden otomatik yapacaktır.

**Örnek `docker-compose.yml` Şablonu:**
```yaml
version: '3.8'
services:
  app:
    build: .
    expose:
      - "3000"
    environment:
      - NODE_ENV=production
    restart: always
```

---

### Adım 2: Git Deposu ve GitHub Push
1. Yerel depoyu başlat ve ilk commit'i at:
   ```bash
   cd projects/<proje-adi>
   git init
   git add .
   git commit -m "feat: initial project setup and docker configuration"
   ```

2. GitHub API kullanarak uzaktan repo oluştur (Dokploy Git clone erişimi için public tercih edilir):
   ```bash
   curl -X POST \
     -H "Authorization: token ${GITHUB_TOKEN}" \
     -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/user/repos \
     -d '{"name":"<proje-adi>", "private": false}'
   ```

3. Repoyu bağla ve `main` dalına pushla:
   ```bash
   git remote add origin https://${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/<proje-adi>.git
   git branch -M main
   git push -u origin main
   ```

---

### Dokploy tRPC API ve Domain Yönetimi (Önemli Not)
Dokploy panelinde 404 hataları veya domain yönlendirme problemleri yaşandığında, Arayüz (UI) yerine doğrudan tRPC API üzerinden işlem yapılabilir:
1. **Domain Oluşturma ve Compose Eşleştirme:**
   ```bash
   curl -s -X POST "${DOKPLOY_URL}/api/trpc/domain.create" \
     -H "x-api-key: ${DOKPLOY_API_KEY}" \
     -H "Content-Type: application/json" \
     -d '{
       "json": {
         "host": "servis-adi.zenbil.site",
         "port": 3000,
         "https": true,
         "composeId": "<compose-id>",
         "serviceName": "<container-servis-adi>"
       }
     }'
   ```
2. **Deployment Tetikleme:**
   ```bash
   curl -s -X POST "${DOKPLOY_URL}/api/trpc/compose.deploy" \
     -H "x-api-key: ${DOKPLOY_API_KEY}" \
     -H "Content-Type: application/json" \
     -d '{
       "json": {
         "composeId": "<compose-id>"
       }
     }'
   ```

#### 1. Dokploy'da Yeni Uygulama Servisi Oluşturma (tRPC)
```bash
# Not: application.create tRPC endpoint'i environmentId gerektirir
APP_RESPONSE=$(curl -s -X POST "${DOKPLOY_URL}/api/trpc/application.create" \
  -H "x-api-key: ${DOKPLOY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "json": {
      "name": "<proje-adi>",
      "projectId": "'"${DOKPLOY_PROJECT_ID}"'",
      "environmentId": "jP-B_-Z-TOLpxuw2VT5bz"
    }
  }')

APPLICATION_ID=$(echo "$APP_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['result']['data']['json']['applicationId'])")
```

#### 2. Git Reposunu Servise Bağlama
GitHub App entegrasyonu olmadan doğrudan Git URL ile bağlamak için `sourceType: "git"` ve `customGitUrl` kullanılmalıdır:
```bash
curl -s -X POST "${DOKPLOY_URL}/api/trpc/application.update" \
  -H "x-api-key: ${DOKPLOY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "json": {
      "applicationId": "'"${APPLICATION_ID}"'",
      "sourceType": "git",
      "customGitUrl": "https://github.com/'"${GITHUB_USERNAME}"'/<proje-adi>.git",
      "customGitBranch": "main",
      "buildType": "dockerfile",
      "dockerfile": "Dockerfile",
      "buildPath": "/"
    }
  }'
```

#### 3. Subdomain Tanımlama (`<proje-adi>.zenbil.site`)
```bash
curl -s -X POST "${DOKPLOY_URL}/api/trpc/domain.create" \
  -H "x-api-key: ${DOKPLOY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "json": {
      "applicationId": "'"${APPLICATION_ID}"'",
      "host": "<proje-adi>.zenbil.site",
      "port": 3000,
      "https": true
    }
  }'
```

#### 4. Deployment Tetikleme
```bash
curl -s -X POST "${DOKPLOY_URL}/api/trpc/application.deploy" \
  -H "x-api-key: ${DOKPLOY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "json": {
      "applicationId": "'"${APPLICATION_ID}"'"
    }
  }'
```

#### 5. Deployment Loglarını Okuma ve Hata Teşhisi (Debugging Logs)
Bir deployment başarısız olduğunda (`status: "error"`), derleme veya klonlama hatasının detayını öğrenmek için `deployment.readLogs` tRPC prosedürü kullanılır:
```bash
# Hatalı deploymentId ile log metnini okuma
curl -s -X GET "${DOKPLOY_URL}/api/trpc/deployment.readLogs?input=%7B%22json%22%3A%7B%22deploymentId%22%3A%22<DEPLOYMENT_ID>%22%7D%7D" \
  -H "x-api-key: ${DOKPLOY_API_KEY}"
```

---

### Adım 4: Canlılık ve Health Check Testi
Deployment tamamlandıktan sonra container'ın kalkması için 15-20 saniye bekle. Dokploy tRPC API ile deployment durumunu kontrol et ve URL'i doğrula:

```bash
sleep 20

# Dokploy deployment durum kontrolü
set -a
source "$HOME/.config/hermes/dokploy.env"
set +a

curl -s "${DOKPLOY_URL}/api/trpc/deployment.all?input=%7B%22json%22%3A%7B%22applicationId%22%3A%22${APPLICATION_ID}%22%7D%7D" \
  -H "x-api-key: ${DOKPLOY_API_KEY}"

# Edge/Cloudflare önbelleğini (cache) aşmak için timestamp ekleyerek test et
STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://<proje-adi>.zenbil.site?cb=$(date +%s)")

if [ "$STATUS_CODE" -eq 200 ] || [ "$STATUS_CODE" -eq 301 ] || [ "$STATUS_CODE" -eq 302 ]; then
  echo "BASARILI: https://<proje-adi>.zenbil.site adresi aktif! (HTTP Kodu: $STATUS_CODE)"
else
  echo "UYARI: Deployment tamamlandi fakat HTTP Yanit Kodu: $STATUS_CODE. Dokploy loglarini kontrol edin."
fi
```

---
---
## Önemli İpuçları ve Sık Karşılaşılan Durumlar (Pitfalls)
0. **🚨 KRİTİK: Git Init — HER ZAMAN TEMİZ DİZİNDE!:**
   `git init` komutu **ASLA** çalışma alanı kök dizininde (`/opt/data`, `~` veya `projects/`) çalıştırılmamalıdır. Bu, **binlerce gereksiz dosyayı** (node_modules, cache, veritabanları, embedded git repo'ları, session dosyaları vb.) commitleyerek devasa ve bozuk bir repo oluşturur. **BU HATA DAHA ÖNCE GERÇEKLEŞTİ ve temizlenmesi zor oldu.**
   
   **DOĞRU SIRA (adım adım, atlanamaz):**
   1. `mkdir -p projects/<proje-adi>` — temiz proje dizinini oluştur
   2. Sadece projeye ait dosyaları `cp` ile kopyala (html, css, js, Dockerfile, nginx.conf vb.)
   3. `cd projects/<proje-adi>` — proje dizinine gir
   4. `git init` — SADECE bu dizinde
   5. `git add .` — sadece proje dosyaları eklenir
   6. `git commit -m "..."` 
   
   **Kontrol:** `git status` çalıştırdığında 11.000 dosya görüyorsan YANLIŞ DİZİNDESİN. `rm -rf .git` ile temizle ve baştan başla.

0b. **GitHub Repo Oluşturma ve Push Sırası:**
   GitHub'da repo oluşturulmadan `git push` yapılamaz. Doğru sıra:
   1. Önce GitHub API ile repo oluştur: `curl -X POST https://api.github.com/user/repos -d '{"name":"<proje-adi>","private":false}'`
   2. `git remote add origin` ile bağla
   3. `git push -u origin main` ile pushla
   
   **`gh` CLI yerine doğrudan git kullan:** `gh` CLI token scope sorunları yaşayabilir (`read:org` eksik). Bu durumda curl API + git push kombinasyonu kullan. Ayrıntılar için bkz: `references/git-remote-push-workflow.md`

0c. **Dokploy environmentId Zorunluluğu:**
   `application.create` endpoint'i `environmentId` parametresini zorunlu tutar. Sadece `projectId` göndermek yetersizdir (`"Invalid input: expected string, received undefined"` hatası). Önce `project.all` endpoint'ini çağırarak hedef projenin `environmentId` değerini almalısın:
   ```bash
   curl -s -G "${DOKPLOY_URL}/api/trpc/project.all" \
     -H "x-api-key: ${DOKPLOY_API_KEY}" \
     --data-urlencode 'input={"json":null}' \
     | python3 -c "import json,sys; d=json.load(sys.stdin); [print(p['name'], p['environments'][0]['environmentId']) for p in d['result']['data']['json']]"
   ```

0d. **buildType Varsayılan Değeri (nixpacks):**
   `application.create` ile oluşturulan uygulamalar varsayılan olarak `buildType: "nixpacks"` kullanır. Dockerfile ile build için `application.update` ile `buildType: "dockerfile"` ve `dockerfile: "Dockerfile"` parametrelerini açıkça göndermelisin.

0e. **GitHub Credentials Dosyası Konumu:**
   GitHub token ve username bilgileri **sadece** `~/.config/hermes/github.env` dosyasında bulunur. Bu dosyayı `projects/` dizininde, root'ta veya başka yerlerde arama. Aynı şekilde Dokploy credentials `~/.config/hermes/dokploy.env` dosyasındadır.

1. **Kullanıcı Arayüzü Tasarımı (Sade & Basit Tercihi):**
   Kullanıcı "basit/sade bir sayfa" istediğinde karmaşık yan paneller, metrik göstergeleri veya çok sayfalı yapılar yerine son derece minimalist, şık ve doğrudan amaca odaklı (ultra-clean single-page) bir UI tasarlanmalıdır.
2. **Private GitHub Repoları ve Dokploy Git Bağlantısı:**
   Dokploy `sourceType: "git"` kullanırken private repolarda klonlama aşamasında yetkilendirme hatası (`status: "error"`, loglarda `fatal: could not read Username for 'https://github.com'`) alınabilir. Hata detayları `deployment.readLogs` tRPC API çağrısı ile kontrol edilebilir. GitHub App entegrasyonu kurulana kadar repoları public (`"private": false`) oluşturmak veya mevcut reponun görünürlüğünü GitHub API `PATCH /repos/{username}/{repo}` endpoint'i ile public hale getirmek deployment'ın sorunsuz çalışmasını sağlar.
3. **Dokploy Compose & Traefik Ağı (dokploy-network):**
   Dokploy üzerinde Compose servislerinin (`composeType: "docker-compose"`) Traefik üzerinden domain (`*.zenbil.site`) alabilmesi için `docker-compose.yml` içerisinde `dokploy-network` harici ağının (`external: true`) tanımlı olması ve ilgili servislerin bu ağa bağlı olması gereklidir. Ayrıca `container_name` override edilmemeli, varsayılan Docker Compose servis adları kullanılmalıdır.
4. **Supabase Img Tag'leri:**
   Supabase veya benzeri Compose stack'lerinde `latest` veya eski commit etiketleri yerine doğrulanmış güncel Docker Hub etiketleri (`supabase/postgres:15.14.1.156`, `supabase/gotrue:v2.193.1`, `postgrest/postgrest:v12.0.1`, `supabase/studio:2026.07.20-sha-74a0848`, `supabase/postgres-meta:v0.96.6`) kullanılmalıdır.
5. **Mevcut Projeyi Güncelleme / Redeploy:**
   Geliştirilen mevcut bir projede kod güncellemesi veya re-deploy yapıldığında, `application.deploy` öncesinde `application.update` API çağrısını (`sourceType: "git"`, `customGitUrl`, `customGitBranch: "main"`, `buildType: "dockerfile"`, `dockerfile: "Dockerfile"`, `buildPath: "/"`) tekrar çalıştırmak Git yapılandırmasının güncelliğinden emin olunmasını sağlar.
2. **Dokploy Deployment Durumu Takibi:**
   `application.deploy` çağrısı asenkron çalışır. İşlem durumunu doğrulamak için `deployment.all` prosedürü çağrılarak en son deployment kaydının `status` alanının `"done"` olduğu teyit edilmelidir.
3. **CDN / Cloudflare Önbelleği:**
   `*.zenbil.site` domain'leri Cloudflare arkasında olduğu için static HTML güncellemelerinde cURL testlerinde önbellekten eski içerik dönebilir. Doğrulama yaparken URL sonuna `?cb=$(date +%s)` gibi bir önbellek kırıcı ekleyin.
4. **Next.js Standalone SSR Deployment:**
   Next.js projelerinde Docker imaj boyutunu küçültmek ve hızlı başlatmak için `next.config.js` dosyasına `output: 'standalone'` eklenmelidir. Multi-stage Dockerfile içerisinde `.next/standalone` ve `.next/static` kopyalanarak `CMD ["node", "server.js"]` komutu ile çalıştırılır (port 3000).
5. **Dokploy Servis / Uygulama Silme (API Delete Procedures):**
   - **Application Silme:** `/api/trpc/application.delete` endpoint'ine `{"json": {"applicationId": "<id>"}}` gönderilir.
   - **Compose Silme:** `/api/trpc/compose.delete` endpoint'i **`deleteVolumes` boolean parametresini zorunlu tutar**: `{"json": {"composeId": "<id>", "deleteVolumes": true}}`. `deleteVolumes` eksikse `400 BAD_REQUEST` döner.

#### 7. 404 Hataları — API Endpoint Sınırlamaları ve Manuel Panel Müdahalesi (Pitfall)
Dokploy API'sinin tüm prosedürleri (örneğin `compose.read`, `application.all`, `domain.all`) tRPC üzerinden her zaman dışarı açık olmayabilir veya sürüm farklarından dolayı `404 NOT_FOUND` dönebilir. 
1. **API Israrından Kaçının:** Komut satırından Dokploy tRPC API ile compose veya domain okuma/yazma işlemlerinde `404 NOT_FOUND` hatası alıyorsanız, API ile zorlamak yerine kullanıcıdan beklentiye girmeden veya kullanıcıyı yönlendirerek **web paneli (`dokploy.zenbil.site`)** üzerinden manuel müdahaleyi tercih edin.
2. **Panel Önceliği:** Compose servislerinin domain ve port eşleştirmeleri (özellikle Supabase gibi harici stack'ler) panel arayüzünde çok daha kararlı çalışır.


---
## Kurallar ve Kısıtlamalar
## Kurallar ve Kısıtlamalar
1. **Env Yükleme:** İşlemlere başlanmadan önce `~/.config/hermes/dokploy.env` ve `~/.config/hermes/github.env` dosyaları mutlaka `source` edilmelidir. `DOKPLOY_PROJECT_ID` ve `DOKPLOY_API_KEY` değişkenlerinin eksiksiz tanımlı olduğu doğrulanmalıdır.
2. **Dokploy API Auth:** Dokploy API çağrılarında `x-api-key: ${DOKPLOY_API_KEY}` veya `Authorization: Bearer ${DOKPLOY_API_KEY}` başlıkları kullanılabilir.
3. **Klasör Yapısı:** Tüm uygulamalar mutlaka `projects/` dizininde kendi klasöründe oluşturulmalıdır.
4. **Port Standardı ve İzolasyon:** Container dışa açılan dahili port her zaman `3000` olmalıdır. Port çakışmalarını önlemek için `ports:` (host-binding) kullanılmamalı, sadece `expose: 3000` tanımlanmalıdır.
5. **Domain Yapısı:** Domain formatı istisna olmaksızın `<proje-adi>.zenbil.site` şeklinde olmalıdır.
6. **404 Hataları ve Debugging:** 404 hatası alırsanız; domain tanımlamasının doğruluğunu, `expose` edilen port ile domain portunun eşleştiğini, `dokploy-network` ağ bağlantısını ve servisin "Redeploy" durumunu kontrol edin.
7. **Hata Denetimi:** Herhangi bir adımda (Git push, Dokploy API vb.) başarısızlık oluşursa işlem durdurulmalı ve kullanıcıya hata detayı raporlanmalıdır.
