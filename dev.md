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

#### Option A: Minimal Config with Auto-Discovery (Recommended)
```json
{
  "wiki_space": {
    "route": "architecture",
    "title": "Architecture Docs",
    "description": "App architecture documentation"
  }
}
```

With folder structure using bracket notation:
```
architecture/
├── [1]core-architecture/     # Order=1, Group="Core Architecture"
│   ├── [1]overview.md        # Order=1, Title="Overview"
│   └── [2]backend.md         # Order=2, Title="Backend"
├── [2]guides/                # Order=2, Group="Guides"
│   └── setup.md              # Auto-order, Title="Setup"
└── misc/                     # Auto-order, Group="Misc"
    └── notes.md              # Auto-order, Title="Notes"
```

#### Option B: Full Manual Config (Legacy)
```json
{
  "wiki_space": {
    "route": "architecture",
    "title": "Architecture Docs",
    "description": "App architecture documentation"
  },
  "groups": [
    {
      "name": "Core Architecture",
      "order": 1,
      "pages": [
        {
          "file": "01-overview.md",
          "title": "Overview",
          "route": "architecture/overview",
          "order": 1
        }
      ]
    }
  ]
}
```

## Auto-Discovery Feature (v3.0)

### Bracket Notation Convention

Use `[n]name` to specify order explicitly, preserving the actual folder/file structure:

**Folders (Groups):**
- `[1]core-architecture/` → Order=1, Name="Core Architecture", Folder=`[1]core-architecture/`
- `[3]advanced/` → Order=3, Name="Advanced", Folder=`[3]advanced/`
- `guides/` → Auto-order, Name="Guides", Folder=`guides/`

**Files (Pages):**
- `[1]overview.md` → Order=1, Title="Overview", Route="architecture/overview", File=`[1]overview.md`
- `[2]setup.md` → Order=2, Title="Setup", Route="architecture/setup", File=`[2]setup.md`
- `notes.md` → Auto-order, Title="Notes", Route="architecture/notes", File=`notes.md`

### Auto-Discovery Logic

1. **Scan folder structure** preserving actual folder/file names
2. **Parse bracket notation** `[n]name` to extract order and clean names for titles/routes
3. **Generate clean titles** by converting dashes to spaces and title-casing
4. **Create clean routes** by removing brackets from paths
5. **Fill gaps** with alphabetical ordering for non-bracketed items
6. **Work in memory only** - never modify the actual file structure

### Structure Preservation

**Key Principle**: Auto-discovery **NEVER** creates clean folders or modifies existing files.

- ✅ **Preserves bracketed structure**: `[1]core-architecture/[1]frontend.md` stays exactly as-is
- ✅ **Generates clean routes**: Creates route `architecture/frontend` for Wiki Pages
- ✅ **Minimal config**: _config.json contains only wiki_space metadata
- ✅ **Memory-only processing**: All auto-discovery happens in memory
- ✅ **No file creation**: Sync functions skip automatic file creation in auto-discovery mode

### Benefits

- **92% Config Reduction**: From 80+ lines to 7 lines
- **Zero Manual Ordering**: Bracket notation handles sequencing
- **Structure Preservation**: Never modifies existing bracketed files/folders
- **Conflict-Free**: `[n]` never interferes with actual file names
- **Flexible**: Mix bracketed and non-bracketed items
- **Backward Compatible**: Full configs still work
- **Manual Control**: Users create bracketed files manually

### Auto-Discovery Functions

- `parse_bracket_notation()` - Extract order from `[n]name` format
- `scan_wiki_folder_structure()` - Auto-generate config from folders
- `load_wiki_config_with_autodiscovery()` - Smart config loading
- `clean_name_to_title()` - Convert file names to proper titles

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

### Completed Refactoring (v3.0)
1. ✅ **Bracket notation auto-discovery** - Use `[n]name` for ordering without config
2. ✅ **Minimal _config.json support** - Only wiki space metadata needed
3. ✅ **Automatic folder scanning** - Generate groups/pages from folder structure
4. ✅ **Smart title generation** - Convert file names to proper titles
5. ✅ **Clean route generation** - Remove brackets from final routes
6. ✅ **Sequential ordering fix** - Pages now order 1, 2, 3 instead of 23, 24, 32
7. ✅ **Structure preservation** - Never creates clean folders, preserves bracketed files
8. ✅ **Memory-only processing** - Auto-discovery works purely in memory
9. ✅ **Sync function protection** - Prevents file creation in auto-discovery mode
10. ✅ **Backward compatibility** - Full configs still work alongside auto-discovery

### Completed Refactoring (v2.0)
1. ✅ **Removed wiki_route_prefix field** - Eliminated redundancy with wiki_space_name
2. ✅ **Added after_migrate hook** - Now in hooks.py for automatic migration sync
3. ✅ **Simplified route logic** - Direct mapping between wiki_space_name and route
4. ✅ **Updated file handler** - Uses direct wiki space matching instead of prefix
5. ✅ **Streamlined configuration** - Fewer fields, clearer purpose
6. ✅ **Enhanced sync function** - Now creates missing pages automatically
7. ✅ **Fixed folder organization** - Auto-creates organized folder structure

### Benefits
- **Massive Config Reduction**: 92% less configuration needed (7 lines vs 80+ lines)
- **Zero Manual Ordering**: Bracket notation handles all page sequencing
- **Structure Preservation**: Never modifies existing bracketed files/folders
- **Simplified Setup**: Users only need to specify wiki space metadata
- **Conflict-Free Ordering**: Brackets never interfere with actual file naming
- **Memory-Only Processing**: Auto-discovery works purely in memory without file creation
- **Manual Control**: Users create and organize bracketed files themselves
- **Flexible Usage**: Mix explicit ordering with automatic ordering
- **Backward Compatible**: Existing full configs continue to work
- **Clean Route Generation**: Final Wiki Page routes don't contain bracket notation

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

### Example Setup (Auto-Discovery)
```
apps/emr_plus/emr_plus/docs/architecture/
├── _config.json                    # Minimal: just wiki space metadata
├── [1]core-architecture/           # Preserved: actual folder name
│   ├── [1]frontend.md              # Preserved: actual file name → route: architecture/frontend
│   └── [2]backend.md               # Preserved: actual file name → route: architecture/backend
├── [2]integration-components/      # Preserved: actual folder name
│   └── [1]doctype-integration.md   # Preserved: actual file name → route: architecture/doctype-integration
└── [3]implementation-guides/       # Preserved: actual folder name
    └── [1]crm-integration.md       # Preserved: actual file name → route: architecture/crm-integration
```

_config.json (7 lines):
```json
{
  "wiki_space": {
    "route": "architecture",
    "title": "EMR Plus Architecture Documentation",
    "description": "Comprehensive architecture documentation for EMR Plus"
  }
}
```

**Key**: All folders and files keep their bracketed names. Auto-discovery generates clean routes for Wiki Pages without modifying the file structure.

### Example Setup (Legacy Full Config)
```
apps/emr_plus/emr_plus/docs/architecture/
├── _config.json                    # Full config with all groups/pages
├── 01-overview.md
└── implementation/
    └── guide.md
```

Wiki Dev Settings (both approaches):
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