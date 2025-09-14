# Wiki Dev

Bi-directional sync between markdown files and Frappe Wiki pages.

**Prerequisites**: Frappe Wiki app must be installed first.

## Features

- Auto sync during migration
- Edit in markdown OR wiki interface
- Organized sidebar with groups
- Smart file handling for uploads

## Setup

### 1. Install
```bash
bench get-app wiki && bench install-app wiki
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app wiki_dev
```

### 2. Create docs structure
```
apps/your_app/your_app/docs/docs/
├── _config.json
├── getting-started.md
└── user-guide.md
```

### 3. Create _config.json
```json
{
  "wiki_space": {
    "route": "docs",
    "title": "Documentation"
  },
  "groups": [{
    "name": "Guide",
    "pages": [{
      "file": "getting-started.md",
      "title": "Getting Started",
      "route": "docs/getting-started"
    }]
  }]
}
```

### 4. Create Wiki Dev Settings
- **App Name**: `your_app`
- **Wiki Space Name**: `docs`
- **Docs Folder Path**: `apps/your_app/your_app/docs`
- Enable sync options
```

### 5. Run migration
```bash
bench --site your_site migrate
```

Pages accessible at `/docs/getting-started`

## Manual Commands

```bash
# Manual sync
bench --site your_site execute wiki_dev.wiki_dev.api.wiki_sync.sync_all_enabled_settings
```

## Troubleshooting

**No pages syncing?**
- Check Wiki Dev Settings enabled with sync options
- Verify `_config.json` exists and markdown files exist
- File paths in config should be relative to wiki space folder

**Pages in wrong folder?**
- Background jobs auto-fix within minutes
- Or run: `bench execute wiki_dev.wiki_dev.api.wiki_sync.check_and_fix_misplaced_pages`

## License

MIT