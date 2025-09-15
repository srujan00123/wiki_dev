# Wiki Dev - Developer Documentation

## Overview
Wiki Dev is a bi-directional sync system for Frappe Wiki that enables developers to maintain documentation as markdown files in their app folders and automatically sync them with Wiki Pages in the Frappe interface.

## System Architecture

### Core Components

1. **Wiki Dev Settings DocType** - Configuration for each app's wiki sync
2. **Sync Engine** - Handles bi-directional sync between markdown and wiki pages
3. **File Handler** - Manages uploaded images and assets
4. **Hooks System** - Automatic sync triggers for various events

## Directory Structure Logic

### User Setup Pattern
```
frappe_bench/
└── apps/
    └── {app_name}/           # e.g., emr_plus
        └── {app_name}/       # e.g., emr_plus
            └── docs/         # docs_folder_path in Wiki Dev Settings
                └── {wiki_space_name}/  # e.g., architecture
                    ├── _config.json
                    ├── page1.md
                    ├── page2.md
                    └── subfolder/
                        └── page3.md
```

### Real Example
```
frappe_bench/
└── apps/
    └── emr_plus/
        └── emr_plus/
            └── docs/                    # docs_folder_path = "apps/emr_plus/emr_plus/docs"
                └── architecture/        # wiki_space_name = "architecture"
                    ├── _config.json
                    ├── 01-overview.md
                    ├── 02-backend-architecture.md
                    └── miscellaneous/
                        └── test-page.md
```

## Configuration Flow

### 1. Wiki Dev Settings Fields
- **app_name**: Name of the Frappe app (e.g., "emr_plus")
- **docs_folder_path**: Path to docs folder ("apps/emr_plus/emr_plus/docs")
- **wiki_space_name**: Folder name for wiki space ("architecture") - also used as route
- **use_parent_label_folders**: Enable sidebar grouping (default: true)
- **sync_on_migrate**: Auto-sync during migrations (default: true)
- **sync_on_wiki_update**: Bi-directional sync (default: true)
- **file_upload_path**: Path for uploaded files ("apps/emr_plus/public/docs/images")
- **public_assets_path**: Public URL path ("/assets/emr_plus/docs")

### 2. Config File Structure (_config.json)
```json
{
  "wiki_space": {
    "route": "architecture",         // Uses wiki_space_name directly
    "title": "Architecture Docs",
    "description": "App architecture documentation"
  },
  "groups": [
    {
      "name": "Core Architecture",
      "order": 1,
      "pages": [
        {
          "file": "01-overview.md",           // Relative to wiki space folder
          "title": "Overview",
          "route": "architecture/overview",   // Full route
          "order": 1
        }
      ]
    }
  ]
}
```

## Sync Logic Flow

### 1. Migration Hook
```
after_migrate → sync_all_enabled_settings() → update_wiki_space_from_folder()
```

### 2. Wiki Page Events
```
Wiki Page Created/Updated → sync_wiki_page_to_markdown()
Wiki Page Deleted → sync_wiki_page_deletion_to_markdown()
```

### 3. Wiki Space Events
```
Wiki Space Updated → sync_wiki_space_sidebar_changes()
```

### 4. File Processing
```
Wiki Page with /private/files/ → auto_process_wiki_page_files() → Move to public docs folder
```

## Key Functions

### Core Sync Functions
- `sync_all_enabled_settings()` - Entry point for migration sync
- `update_wiki_space_from_folder()` - Sync existing wiki space from markdown
- `create_wiki_space_from_folder()` - Create new wiki space from markdown
- `setup_wiki_sidebar_from_folder()` - Configure sidebar with proper grouping

### Page Management
- `sync_wiki_page_to_markdown()` - Wiki to markdown sync
- `sync_new_page()` - Create new wiki page from markdown
- `sync_existing_page()` - Update existing wiki page
- `remove_page_from_config()` - Clean up deleted pages

### Sidebar Management
- Uses `Wiki Group Item` child table with `parent_label` for grouping
- Groups pages by `group["name"]` from _config.json
- Pages with same `parent_label` appear in same sidebar folder

## Refactoring History

### Completed Refactoring (v2.0)
1. ✅ **Removed wiki_route_prefix field** - Eliminated redundancy with wiki_space_name
2. ✅ **Added after_migrate hook** - Now in hooks.py for automatic migration sync
3. ✅ **Simplified route logic** - Direct mapping between wiki_space_name and route
4. ✅ **Updated file handler** - Uses direct wiki space matching instead of prefix
5. ✅ **Streamlined configuration** - Fewer fields, clearer purpose
6. ✅ **Enhanced sync function** - Now creates missing pages automatically
7. ✅ **Fixed folder organization** - Auto-creates organized folder structure

### Benefits
- **Simplified Setup**: Users only need to specify wiki_space_name once
- **Clearer Logic**: Direct 1:1 mapping between folder name and route
- **Automatic Migration**: Built-in sync during bench migrate
- **Reduced Confusion**: No more duplicate/conflicting route configurations
- **Auto-Organization**: System creates proper folder structure from _config.json groups
- **Complete Sync**: Creates missing pages, doesn't just update existing ones

## Testing
- Migration sync: `bench --site {site} migrate`
- Manual sync: `bench --site {site} execute wiki_dev.api.wiki_sync.sync_all_enabled_settings`
- Sidebar refresh: `bench --site {site} execute wiki_dev.api.wiki_sync.refresh_wiki_space_sidebar --kwargs '{"settings_name": "WDS-00002"}'`

## File Paths
- All file paths in _config.json are relative to wiki space folder
- Full file paths: `{docs_folder_path}/{wiki_space_name}/{file_path_from_config}`
- Wiki routes: `{wiki_space_name}/{page_path}` (direct mapping, no prefix needed)

## Setup Instructions

### For App Developers
1. Create docs folder structure:
   ```
   frappe_bench/apps/{your_app}/{your_app}/docs/{wiki_space_name}/
   ```

2. Add _config.json with wiki space configuration

3. Create Wiki Dev Settings record:
   - Set `app_name` to your app name
   - Set `wiki_space_name` to your docs subfolder name
   - Set `docs_folder_path` to "apps/{your_app}/{your_app}/docs"
   - Enable sync options as needed

4. Run migration to auto-sync: `bench --site {site} migrate`

### Example Setup
```
apps/emr_plus/emr_plus/docs/architecture/
├── _config.json
├── 01-overview.md
└── implementation/
    └── guide.md
```

Wiki Dev Settings:
- app_name: "emr_plus"
- wiki_space_name: "architecture"
- docs_folder_path: "apps/emr_plus/emr_plus/docs"

Result: Wiki accessible at `/architecture` with automatic sync.

## Troubleshooting

### No Pages in Wiki Space
**Problem**: Wiki space exists but contains no pages.

**Cause**: The `update_wiki_space_from_folder()` function originally only updated existing pages, never created new ones.

**Solution**: Enhanced the function to create missing wiki pages:
```python
# Now checks if wiki page exists, creates if missing
wiki_page_doc = frappe.db.get_value("Wiki Page", {"route": page_route}, "name")
if wiki_page_doc:
    # Update existing page
else:
    # Create new wiki page
    wiki_page = frappe.new_doc("Wiki Page")
    # ... set properties and insert
```

**Manual Fix**: Run sync manually:
```bash
bench --site {site} execute wiki_dev.api.wiki_sync.update_wiki_space_from_folder --kwargs '{"settings_name": "WDS-XXXXX"}'
```

### Duplicate Migration Hooks
**Problem**: Wiki sync hook appears in multiple app hooks.py files.

**Solution**: Remove from individual apps, keep only in wiki_dev/hooks.py:
```python
# Keep only in wiki_dev/hooks.py
after_migrate = [
    "wiki_dev.api.wiki_sync.sync_all_enabled_settings"
]

# Remove from other apps like emr_plus/hooks.py
after_migrate = [
    "emr_plus.install.after_migrate"  # Keep only app-specific hooks
]
```

### Missing Wiki Route Prefix
**Problem**: References to removed `wiki_route_prefix` field.

**Solution**: Use `wiki_space_name` directly as route everywhere:
- Wiki Space route = wiki_space_name
- File handler matches wiki_space_name exactly
- No additional prefix logic needed