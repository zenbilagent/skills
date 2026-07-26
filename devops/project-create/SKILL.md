---
name: project-create
description: Yeni proje/site/uygulama oluştur → Dockerize et → GitHub'a push → Dokploy'a auto-deploy ile bağla. "Proje oluştur", "site yap", "uygulama çıkar", "web app", "landing page" gibi isteklerde kullan.
version: 1.1.0
tags: [project, site, web-app, landing-page, docker, github, dokploy, deployment, automation]
---

# Proje / Site / Uygulama Oluşturma & Deploy

Yeni bir proje, site, web uygulaması veya landing page oluştur. Dockerize et, GitHub'a push et, Dokploy'da auto-deploy ile `{app-name}.zenbil.site` domaininde yayınla.

## Tetikleyiciler (Trigger Conditions)

Bu skill şu ifadelerde OTOMATIK yüklenmeli:
- "yeni proje oluştur"
- "site yap / site oluştur"
- "uygulama yap / web app"
- "landing page"
- "X'i deploy et / yayına al"
- "{herhangi-isim}.zenbil.site" domain'inde bir şey yayınlamak

## Ön Koşullar

- `~/.config/hermes/github.env` → GITHUB_USERNAME, GITHUB_TOKEN
- `~/.config/hermes/dokploy.env` → DOKPLOY_URL, DOKPLOY_API_TOKEN
- Dokploy helper: `skill_view(name='dokploy-deployment', file_path='scripts/dokploy_api.py')`
- Proje ID: `qm5KtSdIv6Cd4BJio5cmS` (agent)
- Environment ID: `PFBUSdnYByiuOWUiuXIYk` (production)
- Base domain: `zenbil.site` → her uygulama `{app-name}.zenbil.site`

## Tam Workflow (7 Adım)

### Adım 1: Proje Dizinini Oluştur

```bash
mkdir -p /opt/data/projects/{app-name}
```

Uygulama kodunu bu dizine yaz. Minimum gerekli dosyalar:
- Uygulama kaynak kodu
- `Dockerfile`
- `docker-compose.yml`
- `.gitignore`

### Adım 2: Docker Dosyalarını Oluştur

**Dockerfile** — Her proje Dockerized olmak zorunda:
```dockerfile
# Örnek Node.js
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
EXPOSE 3000
CMD ["node", "index.js"]
```

```dockerfile
# Örnek Python (FastAPI/Flask)
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "main.py"]
```

```dockerfile
# Örnek Static HTML (nginx)
FROM nginx:alpine
COPY html/ /usr/share/nginx/html/
EXPOSE 80
```

**docker-compose.yml** — Her projede olmak zorunda:
```yaml
version: "3.8"
services:
  {app-name}:
    build: .
    restart: unless-stopped
    ports:
      - "{EXPOSE_PORT}"
    environment:
      - NODE_ENV=production
```

**.gitignore** — Temel:
```
node_modules/
__pycache__/
.env
*.pyc
.DS_Store
```

### Adım 3: Git Init & Commit

```python
import subprocess, os

# GitHub env yükle
env_vars = {}
with open(os.path.expanduser("~/.config/hermes/github.env")) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env_vars[k.strip()] = v.strip()

os.chdir(f"/opt/data/projects/{app_name}")

# Credential store kur (token URL'de görünmez)
subprocess.run(["git", "config", "--global", "credential.helper", "store"], check=True)
cred_path = os.path.expanduser("~/.git-credentials")
with open(cred_path, "w") as f:
    f.write(f"https://{env_vars['GITHUB_USERNAME']}:{env_vars['GITHUB_TOKEN']}@github.com\n")
os.chmod(cred_path, 0o600)

subprocess.run(["git", "init"], check=True)
subprocess.run(["git", "config", "user.name", env_vars["GITHUB_USERNAME"]], check=True)
subprocess.run(["git", "config", "user.email", f"{env_vars['GITHUB_USERNAME']}@users.noreply.github.com"], check=True)
subprocess.run(["git", "add", "."], check=True)
subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)
subprocess.run(["git", "branch", "-M", "main"], check=True)
```

### Adım 4: GitHub Repo Oluştur & Push

```python
import subprocess, json, os, urllib.request

# Env yükle (yukarıdaki gibi)
gh_user = env_vars["GITHUB_USERNAME"]
gh_token = env_vars["GITHUB_TOKEN"]

# GitHub API ile repo oluştur
req = urllib.request.Request(
    "https://api.github.com/user/repos",
    data=json.dumps({
        "name": app_name,
        "private": True,
        "auto_init": False
    }).encode(),
    headers={
        "Authorization": f"token {gh_token}",
        "Accept": "application/vnd.github+json"
    },
    method="POST"
)
with urllib.request.urlopen(req) as resp:
    repo_data = json.loads(resp.read())

# Remote ekle & push
subprocess.run(["git", "remote", "remove", "origin"], capture_output=True)
subprocess.run(["git", "remote", "add", "origin",
    f"https://github.com/{gh_user}/{app_name}.git"], check=True)
subprocess.run(["git", "push", "-u", "origin", "main"], check=True)
```

### Adım 5: Dokploy'ta Compose Oluştur (Docker Compose + customGitUrl — ZORUNLU)

⚠️ **KRİTİK:** Dokploy'a deploy ederken **Docker Compose yapısı kullanılmalı** (application.create değil, compose.create). Ayrıca GitHub repo push edildikten sonra **customGitUrl parametresi MUTLAKA aynı anda set edilmeli**. Eksikse Dokploy repo'yu bulamaz, build başlamaz, **deploy sessizce başarısız olur** (errorMessage boş döner).

**Zorunlu parametreler:**
- `sourceType: "git"` — git kaynağı kullanacağını belirtir
- `customGitUrl: "https://github.com/zenbilagent/{app-name}.git"` — repo'nun public URL'si (GitHub App gerektirmez)
- `customGitBranch: "main"` — hangi branch'ten clone edilecek
- `composePath: "/docker-compose.yml"` — repo'daki compose dosyasının yolu
- `composeType: "docker-compose"` — orchestration tipi (standart Docker Compose)

```python
import json, os, urllib.request

compose_payload = {
    "json": {
        "name": app_name,
        "projectId": "qm5KtSdIv6Cd4BJio5cmS",
        "environmentId": "PFBUSdnYByiuOWUiuXIYk",
        "sourceType": "git",
        "customGitUrl": f"https://github.com/{gh_user}/{app_name}.git",
        "customGitBranch": "main",
        "composePath": "/docker-compose.yml",
        "composeType": "docker-compose",
        "description": "{açıklama}"
    }
}

req = urllib.request.Request(
    "https://zenbil.site/api/trpc/compose.create",
    data=json.dumps(compose_payload).encode(),
    headers={
        "x-api-key": os.environ["DOKPLOY_API_TOKEN"],
        "Content-Type": "application/json"
    },
    method="POST"
)

with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read())
    compose_id = data["result"]["data"]["json"]["composeId"]
    print(f"Compose ID: {compose_id}")
```

**Neden compose.create (application.create değil)?**
- ✅ Docker Compose yapısı = `docker-compose.yml` repo'dan okunur
- ✅ GitHub App kurulumu gerekmez (customGitUrl public repo'ları doğrudan clone eder)
- ✅ Token/credential sorunu yok
- ✅ Daha basit ve güvenilir

### Adım 6: Domain Ekle

```bash
python3 /opt/data/skills/devops/dokploy-deployment/scripts/dokploy_api.py \
  mutate domain.create '{
    "json": {
      "composeId": "{composeId}",
      "host": "{app-name}.zenbil.site",
      "port": {EXPOSE_PORT},
      "https": false
    }
  }'
```

### Adım 7: Deploy Tetikle

```bash
python3 /opt/data/skills/devops/dokploy-deployment/scripts/dokploy_api.py \
  mutate compose.deploy '{
    "json": {"composeId": "{composeId}"}
  }'
```

30-60 saniye bekle, sonra durum kontrol:
```bash
python3 /opt/data/skills/devops/dokploy-deployment/scripts/dokploy_api.py \
  query compose.one '{"json": {"composeId": "{composeId}"}}'
```

`composeStatus: done` → ✅ başarılı.

### Canlıyı Doğrula

```bash
curl -I https://{app-name}.zenbil.site
# 200 OK → yayında!
```

## Auto-Deploy

✅ GitHub reposuna her `git push` otomatik olarak Dokploy'da build + deploy tetikler (eğer Dokploy'da GitHub webhook kuruluysa).

Manuel deploy gerektiğinde:
```bash
python3 /opt/data/skills/devops/dokploy-deployment/scripts/dokploy_api.py \
  mutate compose.deploy '{"json": {"composeId": "{composeId}"}}'
```

**Önemli:** Compose yapısı kullanıldığı için `application.deploy` değil, `compose.deploy` çağrılmalı.

## Tek Seferde Tam Script (Execute Code ile)

Tüm adımları tek `execute_code` çağrısında çalıştır:

```python
import subprocess, os, json, urllib.request

app_name = "{app-name}"
expose_port = {port}
project_dir = f"/opt/data/projects/{app_name}"
os.makedirs(project_dir, exist_ok=True)

# --- 1. Env yükle ---
def load_env(path):
    env = {}
    with open(os.path.expanduser(path)) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

gh_env = load_env("~/.config/hermes/github.env")
gh_user, gh_token = gh_env["GITHUB_USERNAME"], gh_env["GITHUB_TOKEN"]

# --- 2. Git credential store ---
subprocess.run(["git", "config", "--global", "credential.helper", "store"], check=True)
cred_path = os.path.expanduser("~/.git-credentials")
with open(cred_path, "w") as f:
    f.write(f"https://{gh_user}:{gh_token}@github.com\n")
os.chmod(cred_path, 0o600)

# --- 3. GitHub repo oluştur ---
req = urllib.request.Request(
    "https://api.github.com/user/repos",
    data=json.dumps({"name": app_name, "private": True}).encode(),
    headers={"Authorization": f"token {gh_token}", "Accept": "application/vnd.github+json"},
    method="POST"
)
with urllib.request.urlopen(req) as resp:
    print(f"GitHub repo: {json.loads(resp.read())['html_url']}")

# --- 4. Git init + push ---
os.chdir(project_dir)
subprocess.run(["git", "init"], check=True)
subprocess.run(["git", "config", "user.name", gh_user], check=True)
subprocess.run(["git", "config", "user.email", f"{gh_user}@users.noreply.github.com"], check=True)
subprocess.run(["git", "add", "."], check=True)
subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)
subprocess.run(["git", "branch", "-M", "main"], check=True)
subprocess.run(["git", "remote", "remove", "origin"], capture_output=True)
subprocess.run(["git", "remote", "add", "origin", f"https://github.com/{gh_user}/{app_name}.git"], check=True)
subprocess.run(["git", "push", "-u", "origin", "main"], check=True)
print("GitHub push: OK")

# --- 5. Dokploy application oluştur ---
# ⚠️ KRİTİK: githubAccountId ZORUNLU — GitHub hesabı seçilmezse deploy PATLAR!
# githubAccountId: "Dokploy-2026-07-26-1ndz7l" (Dokploy'da kurulu GitHub App)
from hermes_tools import terminal
result = terminal(f"""python3 /opt/data/skills/devops/dokploy-deployment/scripts/dokploy_api.py \
  mutate application.create '{{"json": {{"name": "{app_name}", "projectId": "qm5KtSdIv6Cd4BJio5cmS", "environmentId": "PFBUSdnYByiuOWUiuXIYk", "sourceType": "github", "owner": "zenbilagent", "repository": "{app_name}", "branch": "main", "buildType": "dockerfile", "githubAccountId": "Dokploy-2026-07-26-1ndz7l"}}}}'""")
app_data = json.loads(result["output"])
app_id = app_data["applicationId"] if isinstance(app_data, dict) else app_data
print(f"Dokploy application: {app_id}")

# --- 6. Domain ekle ---
result = terminal(f"""python3 /opt/data/skills/devops/dokploy-deployment/scripts/dokploy_api.py \
  mutate domain.create '{{"json": {{"applicationId": "{app_id}", "host": "{app_name}.zenbil.site", "port": {expose_port}, "https": true, "certificateType": "letsencrypt"}}}}'""")
print(f"Domain: {app_name}.zenbil.site")

# --- 7. Deploy ---
result = terminal(f"""python3 /opt/data/skills/devops/dokploy-deployment/scripts/dokploy_api.py \
  mutate application.deploy '{{"json": {{"applicationId": "{app_id}"}}}}'""")
print("Deploy tetiklendi!")
```

## Pitfalls

⚠️ **GitHub Account seçilmezse deploy PATLAR:** `application.create` çağrısında `githubAccountId: "Dokploy-2026-07-26-1ndz7l"` ZORUNLU. Bu, Dokploy UI'da Settings → GitHub'da kurulu GitHub App'in ID'si. Eksikse veya yanlışsa Dokploy repo'ya erişemez, build başlamaz, deployment başarısız olur.
⚠️ **owner da gerekli:** `owner: "zenbilagent"` GitHub repo sahibinin username'i. `githubAccountId` ise Dokploy'daki App installation ID — ikisi farklı şeyler, ikisi de gerekli.
⚠️ **GitHub repo zaten varsa:** API 422 döner → repo'yu sil veya farklı isim kullan.
⚠️ **Dokploy GitHub App kurulmamışsa:** Application oluşturulur ama build alamaz. Dokploy UI → Settings → GitHub'dan App kurulmalı.
⚠️ **buildType:** `dockerfile` = Dockerfile kullanır, `nixpacks` = otomatik algılar. Dockerfile varsa `dockerfile` seç.
⚠️ **Port:** `domain.create`'daki port, Dockerfile'daki EXPOSE ile aynı olmalı.
⚠️ **Private repo:** GitHub private repo kullanıyoruz. Dokploy'un erişebilmesi için GitHub App veya Deploy Key gerekli.
⚠️ **Shell escaping:** Token içeren komutlarda heredoc/shell kullanma → Python subprocess + list args.
⚠️ **Tool masking:** write_file/execute_code token'ları `***` yapar → env'den oku, string'e gömme.

## Kontrol Listesi

Yeni proje oluşturduktan sonra kontrol et:
- [ ] `/opt/data/projects/{app-name}/` dizini var
- [ ] Dockerfile + docker-compose.yml mevcut
- [ ] GitHub'da repo oluşturuldu ve push edildi
- [ ] Dokploy'da application oluşturuldu (GitHub source)
- [ ] Domain eklendi: `{app-name}.zenbil.site`
- [ ] Deploy başarılı: `applicationStatus: done`
- [ ] `curl https://{app-name}.zenbil.site` → 200 OK
- [ ] `git push` → auto-deploy tetikleniyor
