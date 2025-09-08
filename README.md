# Wiki Dev

**Bi-directional Wiki Synchronization for Frappe Apps**

Automatically sync markdown files in your app's `/docs` folder with Frappe Wiki Pages. Supports folder-based organization with complete bi-directional sync.

## Features

- ✅ **Auto Migration Sync**: Updates during `bench migrate`
- ✅ **Bi-directional Sync**: Markdown ↔ Wiki Pages
- ✅ **Multi-app Support**: Configure multiple apps independently
- ✅ **Auto Hook Management**: Automatically adds migration hooks
- ✅ **GUI Configuration**: Easy setup through Wiki Dev Settings
- ✅ **Smart File Handling**: Automatic file upload processing

## Quick Start

### 1. Install
```bash
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app wiki_dev
```

### 2. Configure
Create **Wiki Dev Settings** record:
- **App Name**: `your_app_name`
- **Wiki Space Name**: `docs`
- **Enabled**: ✅
- **Sync On Migrate**: ✅
- **Auto Publish Pages**: ✅

### 3. Create Structure
```
apps/your_app_name/
├── docs/
│   └── docs/
│       ├── _config.json
│       ├── basics/
│       │   ├── getting-started.md
│       │   └── user-guide.md
│       └── advanced/
│           └── configuration.md
└── public/
    └── docs/
        └── images/
```

### 4. Create _config.json
```json
{
  "wiki_space": {
    "route": "docs",
    "title": "My Documentation",
    "description": "App documentation"
  },
  "groups": [
    {
      "name": "Basics",
      "order": 1,
      "pages": [
        {
          "file": "docs/basics/getting-started.md",
          "title": "Getting Started",
          "route": "docs/getting-started",
          "order": 1
        }
      ]
    }
  ]
}
```

### 5. Run Migration
```bash
bench --site your_site migrate
```

**Done!** Your wiki pages are now accessible at `/docs/getting-started`, `/docs/user-guide`, etc.

## How It Works

### Auto Hook Management
When **Sync On Migrate** is enabled, the system automatically adds this to your app's `hooks.py`:

```python
after_migrate = [
    "wiki_dev.wiki_dev.api.wiki_sync.sync_all_enabled_settings"
]
```

### Sync Flow
- **Markdown → Wiki**: During migration, markdown files sync to Wiki Pages
- **Wiki → Markdown**: UI edits automatically update markdown files
- **File Uploads**: Images move from private to public assets automatically

## Configuration Reference

| Field | Description | Example |
|-------|-------------|---------|
| **App Name** | Target app | `emr_plus` |
| **Wiki Space Name** | Folder with `_config.json` | `docs` |
| **Docs Folder Path** | Base docs path | `apps/emr_plus/docs` |
| **Wiki Route Prefix** | URL prefix | `docs` → `/docs/page` |
| **File Upload Path** | Upload destination | `apps/emr_plus/public/docs/images` |
| **Public Assets Path** | Public URL path | `/assets/emr_plus/docs` |

## Advanced Usage

### Multiple Wiki Spaces
Create separate configurations for different documentation sections (e.g., user docs vs API docs).

### Manual Sync
```python
# Sync all enabled settings
from wiki_dev.wiki_dev.api.wiki_sync import sync_all_enabled_settings
sync_all_enabled_settings()
```

### Debug Commands
```bash
# Test sync
bench --site your_site execute wiki_dev.wiki_dev.api.debug_recent_pages.check_recent_wiki_pages

# Manual sync
bench --site your_site execute wiki_dev.wiki_dev.api.wiki_sync.sync_all_enabled_settings
```

## Troubleshooting

**Pages not syncing during migration?**
1. Check Wiki Dev Settings is enabled with `sync_on_migrate` checked
2. Verify `_config.json` exists and is valid JSON
3. Ensure markdown files exist at specified paths

**Files not uploading correctly?**
1. Check `file_upload_path` directory exists
2. Verify file permissions on upload directories

**Hook not added automatically?**
1. Check target app's `hooks.py` file exists
2. Look for errors in **Error Log** DocType

## License

MIT