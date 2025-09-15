# Wiki Dev

Bi-directional sync between markdown files and Frappe Wiki pages with **auto-discovery** from folder structure.

**Prerequisites**: Frappe Wiki app must be installed first.

## Features

- **Auto-discovery**: Generate config from folder structure using `[n]name` notation
- **Structure preservation**: Never creates clean folders, preserves bracketed files
- **Minimal config**: Only 7 lines needed (vs 80+ lines previously)
- **Memory-only processing**: Auto-discovery works without modifying files
- Auto sync during migration
- Edit in markdown OR wiki interface
- Organized sidebar with groups
- Smart file handling for uploads
- Sequential page ordering (1, 2, 3...)

## Setup

### 1. Install
```bash
bench get-app wiki && bench install-app wiki
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app wiki_dev
```

### 2. Create docs structure (Auto-Discovery)

**Folder Structure Rules:**
- **Root folder**: `apps/your_app/your_app/docs/{wiki_space_name}/`
- **Groups (Sidebar folders)**: Use subfolders - each subfolder becomes a sidebar group
- **Pages**: Markdown files inside group folders
- **Ordering**: Use `[n]name` notation for explicit order (e.g., `[1]getting-started/`)

```
apps/your_app/your_app/docs/docs/
├── _config.json                 # Minimal config
├── [1]getting-started/          # Group: "Getting Started" (order 1)
│   ├── [1]overview.md          # Page: "Overview" → route: docs/overview
│   └── [2]installation.md      # Page: "Installation" → route: docs/installation
├── [2]user-guide/              # Group: "User Guide" (order 2)
│   └── basics.md               # Page: "Basics" → route: docs/basics
└── misc/                       # Group: "Misc" (auto-order)
    └── faq.md                  # Page: "Faq" → route: docs/faq
```

**Ordering Rules:**
- `[n]` sets explicit order (1, 2, 3...)
- Without brackets: auto-ordered alphabetically after numbered items
- Folders become sidebar groups with `parent_label`
- Files become pages under their folder's group

### 3. Create minimal _config.json
```json
{
  "wiki_space": {
    "route": "docs"
  }
}
```

**That's it!** Groups and pages auto-discovered from existing folder structure (no files moved or renamed).

### 4. Create Wiki Dev Settings

Go to **Wiki Dev Settings** in your Frappe desk and create a new record:

**Required Fields:**
- **App Name**: `your_app`
- **Wiki Space Name**: `docs` (matches your folder name)
- **Docs Folder Path**: `apps/your_app/your_app/docs`

**Optional Configuration:**
- **File Upload Path**: `apps/your_app/public/docs/images` (for uploaded images)
- **Public Assets Path**: `/assets/your_app/docs` (public URL for images)
- **Sync Options**: Enable as needed (all enabled by default)
  - Sync On Migrate
  - Sync On Wiki Update
  - Use Parent Label Folders
  - Auto Publish Pages

### 5. Run migration
```bash
bench --site your_site migrate
```

Pages auto-discovered and accessible at:
- `/docs/overview`
- `/docs/installation`
- `/docs/basics`
- `/docs/faq`

## Auto-Discovery with Bracket Notation

Use `[n]name` to specify explicit ordering:

**Folders (Groups):**
- `[1]getting-started/` → Order 1, Title "Getting Started"
- `[2]user-guide/` → Order 2, Title "User Guide"
- `advanced/` → Auto-order, Title "Advanced"

**Files (Pages):**
- `[1]overview.md` → Order 1, Title "Overview"
- `[2]setup.md` → Order 2, Title "Setup"
- `notes.md` → Auto-order, Title "Notes"

**Benefits:**
- **96% less config** (3 lines vs 80+ lines)
- **Structure preservation** (never modifies existing bracketed files/folders)
- **Conflict-free ordering** (brackets don't affect actual file names)
- **Memory-only processing** (auto-discovery works without file creation)
- **Flexible** (mix explicit and auto ordering)
- **Clean routes** (Wiki Page routes have no brackets, but files keep brackets)

## Manual Commands

```bash
# Manual sync
bench --site your_site execute wiki_dev.api.wiki_sync.sync_all_enabled_settings
```

## Troubleshooting

**No pages syncing?**
- Check Wiki Dev Settings enabled with sync options
- Verify `_config.json` exists (minimal config is fine)
- For auto-discovery: ensure markdown files in subfolders
- For manual config: file paths should be relative to wiki space folder

**Using auto-discovery but pages not found?**
- Check folder structure has subfolders (groups) with .md files
- Use bracket notation `[n]name` for explicit ordering
- Non-bracketed items get auto-ordered alphabetically

**Pages in wrong folder?**
- Background jobs auto-fix within minutes
- Or run: `bench execute wiki_dev.api.wiki_sync.check_and_fix_misplaced_pages`

**Want to switch from full config to auto-discovery?**
- Replace your `_config.json` with minimal version (just wiki_space metadata)
- Organize files into `[n]folder/[n]file.md` structure manually
- Run sync to auto-discover existing structure (no files will be moved or created)

## License

MIT