---
name: new-project-dokploy
description: Yeni bir proje/uygulama/site oluşturur, Next.js ve Tailwind CSS ile geliştirir, MinIO (S3) ve PostgreSQL entegre eder, Dokploy üzerinde deploy eder.
---

# Skill: Otomatik Next.js & Tailwind Proje Geliştirme, PostgreSQL (Prisma), MinIO (S3 Storage) ve Dokploy Deploy

## Açıklama
Bu skill, kullanıcı yeni bir proje, web sitesi veya servis geliştirilmesini istediğinde tüm uçtan uca süreci otomatize eder:
1. `projects/` dizininde yeni proje klasörü oluşturma, **Next.js** ve **Tailwind CSS** ile geliştirme.
2. **(Veritabanı gerekiyorsa)** Dokploy PostgreSQL veritabanı, Prisma ORM (Code-First) entegrasyonu ve otomatik migration.
3. **(Dosya/Medya saklama gerekiyorsa)** MinIO (S3 Uyumlu Object Storage) servisi ve AWS S3 SDK entegrasyonu.
4. **Merkezi Konfigürasyon:** Tüm servis bağlantı bilgileri (Database URL, MinIO credentials, vb.) parça parça kod içine serpiştirilmez; `.env` dosyası ve `docker-compose.yml` ortam değişkenleri (`environment:`) üzerinden merkezi olarak yönetilir.
5. Dockerfile, GitHub push ve Dokploy deploy adımları.

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

---

## İş Akışı Adımları (Workflow Steps)

### Adım 1: Proje Başlatma (Next.js & Tailwind CSS)
1. Proje dizininde `projects/` altında projeye özel bir klasör aç: `projects/<proje-adi>`
2. **Teknoloji Yığını:** Tüm web uygulamaları mutlaka **Next.js (App Router)** ile başlatılmalı ve **Tailwind CSS** ile tasarlanmalıdır.

---

### Adım 2: Veritabanı ve Storage Entegrasyonu (Koşullu & Merkezi Konfigürasyon)

#### A. Merkezi Konfigürasyon Prensibi:
Uygulamanın kullandığı tüm veritabanı ve S3 storage bağlantı bilgileri kod içerisine hardcode edilmez. `docker-compose.yml` içerisindeki `environment:` bloğu ve `.env` üzerinden merkezi olarak yönetilir.

#### B. Veritabanı İhtiyacı (Prisma & PostgreSQL):
1. `npm install prisma @prisma/client` kurulur.
2. `prisma/schema.prisma` içine `binaryTargets = ["native", "linux-musl-openssl-3.0.x"]` eklenir.
3. Dockerfile içerisine `pg_isready` bekleme döngüsü ve `npx prisma db push` eklenir.

#### C. MinIO S3 Object Storage İhtiyacı:
1. `npm install @aws-sdk/client-s3` kurulur.
2. `lib/s3.ts` üzerinden merkezi S3 client yapılandırılır:
   ```typescript
   import { S3Client } from '@aws-sdk/client-s3'

   export const s3Client = new S3Client({
     region: process.env.AWS_REGION || 'us-east-1',
     endpoint: process.env.S3_ENDPOINT,
     credentials: {
       accessKeyId: process.env.S3_ACCESS_KEY || '',
       secretAccessKey: process.env.S3_SECRET_KEY || ''
     },
     forcePathStyle: true
   })
   ```
   Tüm anahtar ve endpoint değerleri environment variable üzerinden okunur.

---

### Adım 3: Git Deposu, GitHub Push ve Dokploy Deploy
Kodlar commit edilir, GitHub'a pushlanır ve Dokploy üzerinden otomatik veya manuel deploy edilir.

---
## Önemli İpuçları ve Sık Karşılaşılan Durumlar (Pitfalls)
1. **Merkezi Konfigürasyon (Env):** Hiçbir veritabanı şifresi veya S3 key koda gömülmez; her zaman `docker-compose.yml` `environment` bloğu ve `.env` dosyası üzerinden okunur.
2. **Next.js & Tailwind CSS Zorunluluğu:** Tüm arayüzler Next.js + Tailwind ile tasarlanmalıdır.
3. **Prisma Alpine OpenSSL & pg_isready:** Alpine container içinde Prisma ve PostgreSQL kullanırken `openssl`, `libc6-compat` ve `pg_isready` bekleme döngüsü şarttır.
