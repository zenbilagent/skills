---
name: new-project-dokploy
description: Yeni bir proje/uygulama/site oluşturur, Next.js ve Tailwind CSS ile geliştirir, MinIO (S3) ve PostgreSQL entegre eder, Dokploy üzerinde deploy eder.
---

# Skill: Otomatik Next.js & Tailwind Proje Geliştirme, PostgreSQL (Prisma), MinIO (S3 Storage) ve Dokploy Deploy

## Açıklama
Bu skill, kullanıcı yeni bir proje, web sitesi veya servis geliştirilmesini istediğinde tüm uçtan uca süreci otomatize eder:
1. `projects/` dizininde yeni proje klasörü oluşturma, **Next.js** ve **Tailwind CSS** ile geliştirme.
2. **(Veritabanı gerekiyorsa)** Dokploy PostgreSQL veritabanı, Prisma ORM (Code-First) entegrasyonu ve otomatik migration.
3. **(Dosya/Medya saklama gerekiyorsa)** Dokploy üzerinden **MinIO (S3 Uyumlu Object Storage)** servisi kurma ve S3 API ile dosya/resim/PDF yönetimi.
4. Dockerfile ve docker-compose yapılandırması.
5. GitHub üzerinde repo oluşturup kodları pushlama ve Dokploy üzerinden deploy etme.

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

### Adım 1: Proje Başlatma (Next.js & Tailwind CSS)
1. Proje dizininde `projects/` altında projeye özel bir klasör aç: `projects/<proje-adi>`
2. **Teknoloji Yığını:** Tüm web uygulamaları mutlaka **Next.js (App Router)** ile başlatılmalı ve **Tailwind CSS** ile tasarlanmalıdır.

---

### Adım 2: Veritabanı, Prisma ve S3 Storage Entegrasyonu (Koşullu)

#### A. Veritabanı İhtiyacı (Prisma & PostgreSQL):
*Uygulama kalıcı veri saklama veya CRUD gerektiriyorsa:*
1. `npm install prisma @prisma/client` kurulur.
2. `prisma/schema.prisma` içine `binaryTargets = ["native", "linux-musl-openssl-3.0.x"]` eklenir.
3. Dokploy API (`postgres.create`) ile izole PostgreSQL veritabanı (`apartman_db` vb.) oluşturulur.
4. Dockerfile içerisine `pg_isready` bekleme döngüsü ve `npx prisma db push` eklenir.

#### B. Dosya/Medya Depolama İhtiyacı (MinIO S3 Object Storage):
*Uygulama dosya, resim, PDF vb. yükleme ve saklama (Upload/Storage) gerektiriyorsa:*
1. **Dokploy Üzerinde MinIO Servisi Kurma (Docker Compose veya Compose tRPC API):**
   Dokploy'da MinIO servisi için `minio` adında bir Docker Compose servisi (`dpage/minio` veya `minio/minio`) ayağa kaldırılır.
   **Örnek MinIO Compose:**
   ```yaml
   version: '3.8'
   services:
     minio:
       image: minio/minio:latest
       container_name: shared-minio
       restart: always
       command: server /data --console-address ":9001"
       environment:
         MINIO_ROOT_USER: minio_admin
         MINIO_ROOT_PASSWORD: minio_secure_password_123
       expose:
         - "9000"
         - "9001"
       volumes:
         - minio_data:/data
       networks:
         - dokploy-network
   ```
2. **S3 API Entegrasyonu (AWS SDK S3 Client):**
   Uygulama içinde `@aws-sdk/client-s3` kütüphanesi kurularak standart **S3 API** üzerinden dosya yükleme/indirme işlemleri yapılır:
   ```bash
   npm install @aws-sdk/client-s3
   ```
   **Bağlantı Ayarları (`lib/s3.ts`):**
   ```typescript
   import { S3Client } from '@aws-sdk/client-s3'

   export const s3Client = new S3Client({
     region: 'us-east-1',
     endpoint: process.env.MINIO_ENDPOINT || 'http://minio:9000', // İç ağ veya harici URL
     credentials: {
       accessKeyId: process.env.MINIO_ACCESS_KEY || 'minio_admin',
       secretAccessKey: process.env.MINIO_SECRET_KEY || 'minio_secure_password_123'
     },
     forcePathStyle: true // MinIO için zorunludur
   })
   ```

---

### Adım 3: Git Deposu ve GitHub Push
1. Yerel depoyu başlat ve ilk commit'i at:
   ```bash
   cd projects/<proje-adi>
   git init
   git add .
   git commit -m "feat: initial Next.js project setup with prisma and minio s3"
   ```

2. GitHub API ile repo oluştur ve pushla:
   ```bash
   curl -X POST \
     -H "Authorization: token ${GITHUB_TOKEN}" \
     -H "Accept: application/vnd.github.v3+json" \
     https://api.github.com/user/repos \
     -d '{"name":"<proje-adi>", "private": false}'

   git remote add origin https://${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/<proje-adi>.git
   git branch -M main
   git push -u origin main
   ```

---

### Adım 4: Dokploy Servisi Oluşturma ve Deploy
Dokploy üzerinden projeyi bağla, `*.zenbil.site` domain'ini tanımla ve deploy et.

---
## Önemli İpuçları ve Sık Karşılaşılan Durumlar (Pitfalls)
0. **🚨 KRİTİK: Git Init — HER ZAMAN TEMİZ DIZINDE!**
1. **Next.js & Tailwind CSS Zorunluluğu:** Tüm yeni web arayüzleri **Next.js** ve **Tailwind CSS** ile geliştirilmelidir.
2. **MinIO `forcePathStyle: true` Ayarı:** S3 Client yapılandırılırken MinIO ile uyumlu çalışması için `forcePathStyle: true` parametresi **mutlaka** verilmelidir.
3. **Prisma Alpine OpenSSL & pg_isready:** Veritabanı gerektiren projelerde Alpine OpenSSL paketleri ve başlangıç bekleme döngüsü unutulmamalıdır.
