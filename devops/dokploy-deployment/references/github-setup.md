# GitHub Entegrasyonu Kurulumu

## Dosya Yapısı
`~/.config/hermes/github.env`:
```
GITHUB_USERNAME=zenbilagent
GITHUB_TOKEN=***
```

## Token Doğrulama
- Classic token `ghp_` ile başlar (40 karakter)
- Yetki: `repo` scope yeterli
- **Fine-grained token KULLANMA** — Dokploy ve bazı git işlemleriyle uyumsuz

## Dosya Kontrolü (bozuk mu?)
```bash
cat -A ~/.config/hermes/github.env
```
- Satır sonu `$` olmalı (LF), `^M$` ise CRLF → bozuk
- `GITHUB_USERNAME=zenbilagent  $` → trailing whitespace → bozuk
- Token uzunluğu 40 olmalı

## GitHub App Kurulumu (Dokploy için)
1. Dokploy UI → Settings → GitHub
2. "Install GitHub App" → GitHub'a yönlendirir
3. Repoları seç (tümü veya sadece ilgili olanlar)
4. Install & Authorize

Bu adım tamamlanmadan Dokploy'un GitHub'dan deploy etmesi mümkün değil.

## Yeni Repo Oluşturma
```python
import subprocess, json, os

# env oku
env = {}
with open(os.path.expanduser("~/.config/hermes/github.env")) as f:
    for line in f:
        if "=" in line:
            k, v = line.strip().split("=", 1)
            env[k] = v

# Repo oluştur
result = subprocess.run(
    ["curl", "-s", "-X", "POST", "https://api.github.com/user/repos",
     "-H", f"Authorization: token {env['GITHUB_TOKEN']}",
     "-H", "Accept: application/vnd.github+json",
     "-d", json.dumps({"name": "app-name", "description": "...", "private": False})],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
if "html_url" in data:
    print(f"✅ Repo: {data['html_url']}")
```

## GitHub Hesabı
- **Username:** zenbilagent (deploy'lar için ayrı hesap)
- Token: `~/.config/hermes/github.env`
