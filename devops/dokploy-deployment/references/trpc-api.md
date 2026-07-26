# Dokploy TRPC API Endpoint Referansı

## Genel Bilgiler

- **Base URL:** `https://dokploy.zenbil.site/api/trpc/{procedure}`
- **Auth:** `x-api-key: {token}` header
- **Query (GET):** `GET /api/trpc/{procedure}?input={"json":{...}}` — read-only
- **Mutation (POST):** `POST /api/trpc/{procedure}` body: `{"json": {...}}`
- **Input wrapper:** Tüm inputlar `{"json": {...}}` içine sarılmalı

## Doğrulanmış Endpoint'ler

### Query (GET)
| Procedure | Açıklama |
|-----------|----------|
| `project.all` | Tüm projeleri listele |
| `compose.one` | Compose detayları (input: composeId) |

### Mutation (POST)
| Procedure | Açıklama | Zorunlu Alanlar |
|-----------|----------|-----------------|
| `application.create` | Uygulama oluştur | name, projectId, environmentId |
| `application.deploy` | Deploy tetikle | applicationId |
| `application.delete` | Uygulama sil | applicationId |
| `compose.create` | Compose oluştur | name, projectId, environmentId, composeFile, sourceType |
| `compose.update` | Compose güncelle | composeId, composeFile |
| `compose.deploy` | Compose deploy | composeId |
| `compose.readLogs` | Compose logları | composeId |
| `domain.create` | Domain ekle | composeId (veya applicationId), host, port, https, certificateType |

## Mevcut Proje Bilgileri (2026-07-25)

```
Proje: "agent" 
  projectId: qm5KtSdIv6Cd4BJio5cmS
  organizationId: qnmJWg2la9NwsbINskyeN
  
  Environment: "production"
    environmentId: PFBUSdnYByiuOWUiuXIYk
    isDefault: true
    
    Servisler:
    - hermes (compose): composeId=UST-w2AVzAfwk6uknvU5u → HERMES AGENT'IN KENDİSİ
    - weather-app (compose): composeId=TVqYRuQFGgmUhVvryDhVY → Hava durumu (deploy deneniyor)
```

## application.create Input Şeması (doğrulanmış)

```json
{
  "json": {
    "name": "my-app",
    "projectId": "qm5KtSdIv6Cd4BJio5cmS",
    "environmentId": "PFBUSdnYByiuOWUiuXIYk",
    "sourceType": "github",
    "owner": "username",
    "repository": "repo",
    "branch": "main",
    "buildType": "nixpacks"
  }
}
```

Kaynak tipleri: `github`, `gitlab`, `docker`, `raw` (compose için)

## compose.create Input Şeması (doğrulanmış)

```json
{
  "json": {
    "name": "my-service",
    "projectId": "qm5KtSdIv6Cd4BJio5cmS",
    "environmentId": "PFBUSdnYByiuOWUiuXIYk",
    "composeFile": "version: '3.8'\nservices:\n  web:\n    image: nginx:alpine\n    ports:\n      - '80:80'",
    "sourceType": "raw",
    "description": "Optional description"
  }
}
```

## domain.create Input Şeması (doğrulanmış)

```json
{
  "json": {
    "composeId": "xxx",
    "host": "app.zenbil.site",
    "port": 80,
    "https": true,
    "certificateType": "letsencrypt"
  }
}
```

## Keşfedilmemiş Endpoint'ler (denenmesi gereken)

Bunlar Dokploy UI'ında var olmalı ama henüz doğrulanmadı:
- `application.readAppLogs`
- `application.update`
- `docker.getContainers`
- `settings.all`
- `user.byId`
- `admin.all`
