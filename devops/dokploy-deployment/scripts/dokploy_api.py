#!/usr/bin/env python3
"""
Dokploy TRPC API helper.

Kullanım:
    from dokploy_api import DokployClient
    client = DokployClient()
    
    # GET query
    projects = client.query("project.all")
    
    # POST mutation
    result = client.mutate("application.create", {
        "name": "my-app",
        "projectId": "xxx",
        "environmentId": "yyy"
    })
    
    # Compose deploy
    client.mutate("compose.deploy", {"composeId": "xxx"})
    
    # Compose güncelle
    client.mutate("compose.update", {
        "composeId": "xxx",
        "composeFile": "version: '3.8'\\nservices:\\n  web:\\n    image: nginx"
    })
    
    # Domain ekle
    client.mutate("domain.create", {
        "composeId": "xxx",
        "host": "app.zenbil.site",
        "port": 80,
        "https": True,
        "certificateType": "letsencrypt"
    })

Otomatik olarak ~/.config/hermes/dokploy.env dosyasından config okur.
"""
import json
import os
import sys
import urllib.request
import urllib.error


class DokployClient:
    def __init__(self, env_path=None):
        env_path = env_path or os.path.expanduser("~/.config/hermes/dokploy.env")
        config = {}
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip()
        self.url = config["DOKPLOY_URL"].rstrip("/")
        self.token = config["DOKPLOY_API_TOKEN"]

    def _request(self, method, path, data=None):
        url = f"{self.url}/api/trpc/{path}"
        headers = {
            "x-api-key": self.token,
            "Content-Type": "application/json",
        }
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode()
                result = json.loads(raw)
                if "error" in result:
                    err = result["error"]
                    msg = err.get("json", {}).get("message", raw)
                    raise RuntimeError(f"Dokploy API error: {msg}")
                return result.get("result", {}).get("data", {}).get("json")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            raise RuntimeError(f"HTTP {e.code}: {body}")

    def query(self, procedure, params=None):
        """GET request for read-only procedures (project.all, etc.)"""
        path = procedure
        if params:
            encoded = json.dumps({"json": params}, separators=(",", ":"))
            path = f"{procedure}?input={urllib.request.quote(encoded)}"
        return self._request("GET", path)

    def mutate(self, procedure, params=None):
        """POST request for mutations (create, update, delete, deploy)."""
        body = {"json": params} if params else {"json": {}}
        return self._request("POST", procedure, body)


# --- CLI modu: python dokploy_api.py <method> <procedure> [json_params] ---
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Kullanım: python dokploy_api.py <query|mutate> <procedure> [json]")
        sys.exit(1)

    method = sys.argv[1]
    procedure = sys.argv[2]
    params = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None

    client = DokployClient()
    if method == "query":
        result = client.query(procedure, params)
    elif method == "mutate":
        result = client.mutate(procedure, params)
    else:
        print(f"Bilinmeyen method: {method} (query veya mutate olmalı)")
        sys.exit(1)

    print(json.dumps(result, indent=2, ensure_ascii=False))
