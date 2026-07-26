# Git Remote + Push Workflow (No `gh` CLI)

**When to use:** When `gh` CLI has token scope issues (`read:org` missing) or you want a simpler, more reliable approach.

## Workflow

```bash
# 1. Source GitHub credentials
source ~/.config/hermes/github.env

# 2. Add remote with token embedded in URL
git remote add origin "https://${GITHUB_USERNAME}:${GITHUB_TOKEN}@github.com/${GITHUB_USERNAME}/<repo-name>.git"

# 3. Set branch name
git branch -M main

# 4. Push
git push -u origin main
```

## Why This Works Better Than `gh` CLI

- **No token scope requirements**: `gh` CLI needs `read:org` scope for many operations, but direct git push only needs `repo` scope
- **Simpler**: One command instead of multiple `gh` commands
- **More reliable**: Bypasses `gh` CLI authentication complexity
- **Works with existing tokens**: Your `~/.config/hermes/github.env` token likely has `repo` scope but not `read:org`

## GitHub Repo Creation (Still Use API)

You still need to create the repo first via GitHub API:

```bash
curl -X POST \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/user/repos \
  -d '{"name":"<repo-name>","private":false,"description":"<description>"}'
```

Then use git commands above.

## Common Mistakes

❌ **Wrong**: Trying to use `gh auth login --with-token` when token lacks `read:org`
✅ **Right**: Skip `gh` entirely, use `git remote add` with token URL

❌ **Wrong**: Running `git init` in `/opt/data` (commits thousands of unwanted files)
✅ **Right**: Create project directory first, `cd` into it, then `git init`
