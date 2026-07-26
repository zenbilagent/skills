# Cloudflare Bot Protection Bypass (2026-07-26)

## Problem

Hermes container (IP: `172.19.0.2`) Dokploy API'ye (`https://zenbil.site`) erişmeye çalıştığında Cloudflare bot protection tarafından bloke edildi. Tüm curl ve browser denemeleri timeout verdi (15-30 saniye sonra connection refused).

**Belirtiler:**
- `curl -v https://zenbil.site/api/trpc/...` → timeout after 15s
- Browser navigate → "CDP command timed out: Page.navigate"
- Aynı container'dan `curl https://ifconfig.me` çalışıyor (dış IP: `191.218.161.10`)
- `ping zenbil.site` çalışıyor (ICMP reply)
- Ama port 443 bağlantısı kurulamıyor

## Kök Neden

Cloudflare'ın bot detection sistemi, bu container'ın IP adresini (`172.19.0.2`) veya User-Agent'ını otomatik olarak bot olarak işaretledi. Dokploy API endpoint'lerine erişim engellendi.

## Çözüm

### Cloudflare Dashboard'da IP Whitelist Ekle

1. **Cloudflare Dashboard** → https://dash.cloudflare.com
2. **zenbil.site** domain'ini seç
3. Sol menüden: **Security** → **WAF** → **Tools** sekmesi
4. **IP Access Rules** bölümünde:
   - "Add an IP Access Rule" butonuna tıkla
   - **IP Address:** `172.19.0.2` (bu container'ın IP'si)
   - **Action:** `Allow`
   - **Zone:** `zenbil.site`
   - **Note:** "Hermes Agent container"
   - **Save**

### Alternatif: Custom Rules

**Rules** → **Custom Rules** → **Create rule**:
- **Rule name:** "Allow Hermes Agent"
- **When incoming requests match:**
  - Field: `IP Source Address`
  - Operator: `equals`
  - Value: `172.19.0.2`
- **Then... Choose action:** `Skip`
- **WAF Managed Rules:** ✅ (tümünü atla)
- **Save**

## Doğrulama

İzin eklendikten sonra:

```bash
source ~/.config/hermes/dokploy.env

curl -s --max-time 15 \
  -H "x-api-key: ${DOKPLOY_API_TOKEN}" \
  "https://zenbil.site/api/trpc/project.all?input=%7B%22json%22%3A%7B%7D%7D"
```

**Başarılı yanıt:**
```json
{"result":{"data":{"json":[{"projectId":"qm5KtSdIv6Cd4BJio5cmS","name":"agent",...}]}}}
```

## Önemli Notlar

- **Container IP değişebilir:** Docker container yeniden oluşturulursa IP değişebilir (`docker inspect` ile yeni IP'yi bul)
- **Wildcard izin:** `172.19.0.0/24` subnet'i için de izin verilebilir (tüm container'lar için)
- **Rate limiting:** Cloudflare rate limiting de aktif olabilir → Whitelist sonrası sorun çözülür

## Alternatif Yaklaşımlar (Çalışmadı)

- ❌ `User-Agent` değiştirme (Mozilla/5.0 spoofing) → işe yaramadı
- ❌ HTTP yerine HTTPS → zaten HTTPS kullanılıyordu
- ❌ Docker internal network (`dokploy` service name) → DNS resolution yok
- ❌ Localhost port forwarding → Dokploy container bu container'dan erişilebilir değil
- ❌ Farklı portlar (80, 8080, 8443) → hiçbiri açık değil

**Tek çözüm:** Cloudflare IP whitelist.
