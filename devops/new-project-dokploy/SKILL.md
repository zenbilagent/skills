---
name: new-project-dokploy
description: Yeni bir proje/uygulama/site oluşturur, Next.js ve Tailwind CSS ile geliştirir, Dockerize eder, GitHub'a pushlar, Dokploy API ile PostgreSQL ve *.zenbil.site üzerinde deploy eder.
---

# Skill: Otomatik Next.js & Tailwind Proje Geliştirme, PostgreSQL (Prisma) ve Dokploy Deploy

## Açıklama
Bu skill, kullanıcı yeni bir proje, web sitesi veya servis geliştirilmesini istediğinde tüm uçtan uca süreci otomatize eder:
1. `projects/` dizininde yeni proje klasörü oluşturma, **Next.js** ve **Tailwind CSS** ile geliştirme.
2. **(Gerekliyse)** Prisma ORM (Code-First) ve PostgreSQL veritabanı entegrasyonu.
3. Dockerfile ve docker-compose (iç port 3000 - expose) yapılandırması.
4. GitHub üzerinde repo oluşturup kodları pushlama.
5. Dokploy REST/tRPC API kullanarak projeyi oluşturma, Git reponuzu bağlama, `*.zenbil.site` subdomain'i ekleme ve deploy etme.
6. Deployment sonrası canlılık (health check) doğrulama testi.

---

## Çevre Değişkenleri ve Konfigürasyon (Environment Variables)

Hermes Agent çalıştırmadan önce çevre değişkenlerini aşağıdaki konfigürasyon dosyalarından otomatik olarak yüklemelidir:

- `~/.config/hermes/dokploy.env`
- `~/.config/hermes/github.env`

### Ortam Değişkenlerini Yükleme (Source Command):
```bash
set -a
source "$HOME/.config/hermes/dokploy.env"
source "$HOME/.config/hermes/github.env"
set +a
```

### Beklenen Değişkenler:

**`~/.config/hermes/dokploy.env` İçeriği:**
```env
DOKPLOY_URL="xxxx"          # Örn: https://zenbil.site
DOKPLOY_API_KEY=***      # Dokploy API anahtarı
DOKPLOY_PROJECT_ID="xxxx"   # Servislerin ekleneceği Dokploy Proje ID'si
```

**`~/.config/hermes/github.env` İçeriği:**
```env
GITHUB_TOKEN=***         # GitHub Personal Access Token (repo oluşturma/push izni)
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

### Adım 1: Proje Başlatma (Next.js & Tailwind CSS) ve Opsiyonel Veritabanı
1. Proje dizininde `projects/` altında projeye özel bir klasör aç: `projects/<proje-adi>`
2. **Teknoloji Yığını:** Tüm web uygulamaları mutlaka **Next.js (App Router)** ile başlatılmalı ve **Tailwind CSS** ile tasarlanmalıdır.
3. **Veritabanı İhtiyacı Kriteri:** 
   - Uygulama **veri saklama, kullanıcı kaydı, CRUD işlemleri veya veritabanı** gerektiriyorsa (örn: aidat takibi, e-ticaret, todo, blog vb.) Prisma ve PostgreSQL entegrasyonu yapılır.
   - Statik araçlar, hesap makineleri, sunumsuz görsel araçlar vb. için **veritabanı kurulmaz**.
4. **Veritabanı Gerekiyorsa (Prisma & PostgreSQL):**
   - Prisma ve PostgreSQL (`@prisma/client`, `prisma`) kurulur.
   - `prisma/schema.prisma` dosyasında `binaryTargets = ["native", "linux-musl-openssl-3.0.x"]` tanımlanır.
   - Dokploy API ile özel bir PostgreSQL veritabanı (`postgres.create` ve `postgres.deploy`) oluşturulur.
   - Dockerfile ve Docker Compose içerisinde Alpine OpenSSL paketleri ve `pg_isready` bekleme döngüsü entegre edilir.

---

### Adım 2: Git Deposu ve GitHub Push
1. Yerel depoyu başlat ve ilk commit'i at:
   ```bash
   cd projects/<proje-adi>
   git init
   git add .
   git commit -m "feat: initial Next.js and Tailwind project setup"
   ```

2. GitHub API kullanarak uzaktan repo oluştur:
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

### Adım 3: Dokploy Servisi Oluşturma ve Deploy (Compose veya Application)
Dokploy üzerinden projeyi bağla, `*.zenbil.site` domain'ini tanımla ve deploy et.

---
## Önemli İpuçları ve Sık Karşılaşılan Durumlar (Pitfalls)
0. **🚨 KRİTİK: Git Init — HER ZAMAN TEMİZ DİZİNDE!:**
   `git init` komutu **ASLA** çalışma alanı kök dizininde (`/opt/data`, `~` veya `projects/` kurulu olmamalıdır). 

1. **Next.js & Tailwind CSS Zorunluluğu:**
   Tüm yeni web uygulamaları ve arayüzler istisnasız **Next.js** ve **Tailwind CSS** kullanılarak geliştirilmelidir.
2. **Koşullu Veritabanı Kurulumu:**
   Prisma ve PostgreSQL her projeye körü körüne kurulmamalıdır; yalnızca uygulamanın kalıcı veri saklama ihtiyacı varsa eklenmelidir.
3. **Prisma Alpine OpenSSL Hatası (`libssl.so.1.1`):**
   Alpine imajlarında Prisma query engine `openssl` ve `libc6-compat` paketlerine ihtiyaç duyar. Hem builder hem runner aşamasında `apk add --no-cache openssl libc6-compat` kurulmalıdır.
4. **Database Race Condition (`pg_isready`):**
   Veritabanı gerektiren projelerde container başladığında `until pg_isready ...; do sleep 2; done` döngüsü kullanılmalıdır.
