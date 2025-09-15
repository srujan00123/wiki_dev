import frappe
import json
import os
from frappe import _


@frappe.whitelist()
def create_wiki_space_from_folder(settings_name, folder_name=None):
	"""Create a new Wiki Space from a documentation folder with _config.json"""
	try:
		settings = frappe.get_doc("Wiki Dev Settings", settings_name)
		if not settings.enabled:
			return {"success": False, "message": "Wiki Dev Settings is disabled"}
		
		# Use folder_name from settings if not provided
		if not folder_name:
			folder_name = settings.wiki_space_name
		
		docs_path = settings.get_full_docs_path()
		folder_path = os.path.join(docs_path, folder_name)
		config_path = os.path.join(folder_path, "_config.json")
		
		if not os.path.exists(config_path):
			return {"success": False, "message": f"Configuration file not found: {config_path}"}
		
		with open(config_path, 'r') as f:
			config = json.load(f)
		
		wiki_config = config.get("wiki_space", {})
		route = wiki_config.get("route")
		title = wiki_config.get("title")
		description = wiki_config.get("description", "")
		
		if not route or not title:
			return {"success": False, "message": "Wiki space config must have 'route' and 'title'"}
		
		# Check if wiki space already exists
		if frappe.db.exists("Wiki Space", {"route": route}):
			return {"success": False, "message": f"Wiki space with route '{route}' already exists"}
		
		# Create Wiki Space
		wiki_space = frappe.new_doc("Wiki Space")
		wiki_space.title = title
		wiki_space.route = route
		wiki_space.description = description
		wiki_space.insert()
		
		# Create pages and setup sidebar
		pages_created = create_wiki_pages_from_folder(folder_path, wiki_space.name, settings)
		setup_wiki_sidebar_from_folder(folder_path, wiki_space.name, settings)
		
		frappe.db.commit()
		
		return {
			"success": True,
			"message": f"Created wiki space '{title}' with {pages_created} pages",
			"wiki_space_name": wiki_space.name,
			"route": route
		}
		
	except Exception as e:
		frappe.db.rollback()
		return {"success": False, "error": str(e)}


def create_wiki_pages_from_folder(folder_path, wiki_space_name, settings):
	"""Create Wiki Pages from markdown files based on folder configuration or auto-discovery"""
	# Get the wiki space route from the wiki space document
	space_doc = frappe.get_doc("Wiki Space", wiki_space_name)
	wiki_space_route = space_doc.route

	# Load config with auto-discovery support
	config = load_wiki_config_with_autodiscovery(folder_path, wiki_space_route)

	if not config:
		frappe.log_error(f"Could not load config or auto-discover structure for {folder_path}", "Wiki Page Creation")
		return 0

	pages_created = 0
	
	for group in config.get("groups", []):
		for page_config in group.get("pages", []):
			# File paths in config are relative to wiki space folder
			file_path = os.path.join(folder_path, page_config["file"])
			
			if os.path.exists(file_path):
				with open(file_path, 'r') as f:
					content = f.read()
				
				# Use the full route from config (already includes wiki_space_route)
				page_route = page_config['route']
				
				# Check if page already exists
				if not frappe.db.exists("Wiki Page", {"route": page_route}):
					wiki_page = frappe.new_doc("Wiki Page")
					wiki_page.title = page_config["title"]
					wiki_page.route = page_route
					wiki_page.content = content
					wiki_page.wiki_space = wiki_space_name
					wiki_page.published = 1 if settings.auto_publish_pages else 0
					wiki_page.insert()
					pages_created += 1
	
	return pages_created


def setup_wiki_sidebar_from_folder(folder_path, wiki_space_name, settings):
	"""Setup hierarchical wiki sidebar from folder configuration or auto-discovery"""
	space_doc = frappe.get_doc("Wiki Space", wiki_space_name)

	# Get the wiki space route from the space document
	wiki_space_route = space_doc.route

	# Load config with auto-discovery support
	config = load_wiki_config_with_autodiscovery(folder_path, wiki_space_route)

	if not config:
		frappe.log_error(f"Could not load config or auto-discover structure for {folder_path}", "Wiki Sidebar Setup")
		return

	# DON'T write auto-generated configs back to _config.json
	# This preserves the minimal config approach where _config.json only contains wiki_space metadata
	# Auto-discovery should work purely in memory without modifying the config file

	# Skip resequencing for auto-discovered configs to prevent writes
	# The auto-discovery already handles proper ordering via bracket notation
	
	# Clear existing sidebar and navbar
	space_doc.wiki_sidebars = []
	space_doc.navbar_items = []
	
	# Use parent labels from settings if configured
	parent_labels = []
	
	# Create sidebar structure using parent_label for folder hierarchy
	for group in sorted(config.get("groups", []), key=lambda x: x.get("order", 999)):
		group_name = group["name"]
		
		# Use group name as parent label for folder structure
		parent_label = group_name
		
		# Add pages to sidebar with group as parent_label for folder structure
		for page_config in sorted(group.get("pages", []), key=lambda x: x.get("order", 999)):
			# Use the full route from config
			page_route = page_config['route']
			
			# Find the Wiki Page
			page_doc = frappe.db.get_value("Wiki Page", {"route": page_route}, "name")
			if page_doc:
				# Add to sidebar with group as parent_label (creates folder structure)
				space_doc.append("wiki_sidebars", {
					"parent_label": parent_label if settings.use_parent_label_folders else None,
					"wiki_page": page_doc,
					"hide_on_sidebar": 0
				})
	
	space_doc.save()
	return True


@frappe.whitelist()
def refresh_wiki_space_sidebar(settings_name, folder_name=None):
	"""Refresh wiki space sidebar structure from config"""
	try:
		settings = frappe.get_doc("Wiki Dev Settings", settings_name)
		if not settings.enabled:
			return {"success": False, "message": "Wiki Dev Settings is disabled"}

		# Use folder_name from settings if not provided
		if not folder_name:
			folder_name = settings.wiki_space_name

		docs_path = settings.get_full_docs_path()
		folder_path = os.path.join(docs_path, folder_name)
		config_path = os.path.join(folder_path, "_config.json")

		if not os.path.exists(config_path):
			return {"success": False, "message": f"Configuration file not found: {config_path}"}

		with open(config_path, 'r') as f:
			config = json.load(f)

		wiki_space_route = config["wiki_space"]["route"]

		# Find existing wiki space
		wiki_space = frappe.db.get_value("Wiki Space", {"route": wiki_space_route}, "name")
		if not wiki_space:
			return {"success": False, "message": f"Wiki space not found with route: {wiki_space_route}"}

		# Update sidebar
		setup_wiki_sidebar_from_folder(folder_path, wiki_space, settings)

		return {
			"success": True,
			"message": f"Refreshed sidebar for wiki space '{wiki_space_route}'"
		}

	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def sync_all_enabled_settings():
	"""Sync all enabled Wiki Dev Settings (for migration hook)"""
	try:
		all_settings = frappe.get_all("Wiki Dev Settings", 
			filters={"enabled": 1, "sync_on_migrate": 1},
			fields=["name"]
		)
		
		results = []
		for setting_data in all_settings:
			# Try to update existing wiki space first
			result = update_wiki_space_from_folder(setting_data.name)
			
			# If wiki space doesn't exist, create it
			if not result.get("success") and "Wiki space not found" in result.get("message", ""):
				frappe.log_error(f"Wiki space not found for {setting_data.name}, creating new one...", "Wiki Sync")
				result = create_wiki_space_from_folder(setting_data.name)
			
			results.append({
				"settings": setting_data.name,
				"result": result
			})
		
		return {
			"success": True,
			"message": f"Synced {len(results)} settings",
			"results": results
		}
		
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def update_wiki_space_from_folder(settings_name, folder_name=None):
	"""Update existing wiki space from folder configuration (bi-directional sync)"""
	try:
		settings = frappe.get_doc("Wiki Dev Settings", settings_name)
		if not settings.enabled:
			return {"success": False, "message": "Wiki Dev Settings is disabled"}
		
		# Use folder_name from settings if not provided
		if not folder_name:
			folder_name = settings.wiki_space_name
		
		docs_path = settings.get_full_docs_path()
		folder_path = os.path.join(docs_path, folder_name)

		# Use the folder name as the wiki space route for auto-discovery
		wiki_space_route = folder_name

		# Load config with auto-discovery support
		config = load_wiki_config_with_autodiscovery(folder_path, wiki_space_route)

		if not config:
			return {"success": False, "message": f"Could not load or auto-discover configuration for: {folder_path}"}

		wiki_space_route = config["wiki_space"]["route"]
		
		# Find existing wiki space
		wiki_space = frappe.db.get_value("Wiki Space", {"route": wiki_space_route}, "name")
		if not wiki_space:
			return {"success": False, "message": f"Wiki space not found with route: {wiki_space_route}"}
		
		updates = []
		
		# Update each page from markdown files
		for group in config.get("groups", []):
			for page_config in group.get("pages", []):
				# File paths in config are relative to wiki space folder
				file_path = os.path.join(folder_path, page_config["file"])
				
				if os.path.exists(file_path):
					with open(file_path, 'r') as f:
						markdown_content = f.read()
					
					# Use the full route from config
					page_route = page_config['route']
					
					# Find existing wiki page
					wiki_page_doc = frappe.db.get_value("Wiki Page", {"route": page_route}, "name")
					if wiki_page_doc:
						page = frappe.get_doc("Wiki Page", wiki_page_doc)

						# Update if content differs
						if page.content != markdown_content:
							page.content = markdown_content
							page.title = page_config["title"]  # Ensure title is up to date
							page.published = 1 if settings.auto_publish_pages else page.published
							page.save()
							updates.append(f"Updated '{page_config['title']}'")
					else:
						# Create new wiki page if it doesn't exist
						wiki_page = frappe.new_doc("Wiki Page")
						wiki_page.title = page_config["title"]
						wiki_page.route = page_route
						wiki_page.content = markdown_content
						wiki_page.wiki_space = wiki_space
						wiki_page.published = 1 if settings.auto_publish_pages else 0
						wiki_page.insert()
						updates.append(f"Created '{page_config['title']}'")
		
		# Update sidebar structure
		setup_wiki_sidebar_from_folder(folder_path, wiki_space, settings)
		
		frappe.db.commit()
		
		return {
			"success": True,
			"message": f"Updated wiki space '{folder_name}' - {len(updates)} pages updated",
			"updates": updates
		}
		
	except Exception as e:
		frappe.db.rollback()
		return {"success": False, "error": str(e)}


def sync_wiki_page_to_markdown(doc, method=None):
	"""Hook function: Automatically sync wiki page changes to markdown files"""
	try:
		# For new pages, enqueue a background job to check placement after sidebar is saved
		if method == "after_insert":
			frappe.enqueue(
				'wiki_dev.api.wiki_sync.fix_page_placement_if_needed',
				queue='short',
				timeout=60,
				enqueue_after_commit=True,  # Wait until transaction completes
				doc_name=doc.name,
				doc_route=doc.route
			)
		
		# Find settings that match this wiki page's app
		all_settings = frappe.get_all("Wiki Dev Settings", 
			filters={"enabled": 1, "sync_on_wiki_update": 1},
			fields=["name", "app_name", "docs_folder_path", "wiki_space_name"]
		)
		
		for setting_data in all_settings:
			settings = frappe.get_doc("Wiki Dev Settings", setting_data.name)
			docs_path = settings.get_full_docs_path()
			
			if not docs_path or not os.path.exists(docs_path):
				continue
			
			# Search through all folders for matching wiki page
			for item in os.listdir(docs_path):
				item_path = os.path.join(docs_path, item)
				config_path = os.path.join(item_path, "_config.json")
				
				if os.path.isdir(item_path) and os.path.exists(config_path):
					with open(config_path, 'r') as f:
						config = json.load(f)
					
					wiki_space_route = config.get("wiki_space", {}).get("route")
					
					# Check if this page belongs to this wiki space
					if wiki_space_route and doc.route.startswith(f"{wiki_space_route}/"):
						# First check if page exists in config with wrong parent and move it
						synced = sync_misplaced_page(doc, config, item_path, settings, config_path, wiki_space_route)
						
						# Then try to find existing page in config
						if not synced:
							synced = sync_existing_page(doc, config, item_path, settings, wiki_space_route)
						
						# If not found, handle as new page
						if not synced:
							synced = sync_new_page(doc, config, item_path, settings, config_path, wiki_space_route)
						
						if synced:
							return
		
	except Exception as e:
		frappe.log_error(f"Wiki to Markdown Sync Error: {str(e)}", "Wiki Sync Error")


def sync_wiki_space_sidebar_changes(doc, method=None):
	"""Hook function: Sync all pages when Wiki Space sidebar changes"""
	try:
		# When Wiki Space is updated (sidebar changes), re-sync all pages in that space
		for sidebar_item in doc.wiki_sidebars:
			if sidebar_item.wiki_page:
				try:
					page = frappe.get_doc("Wiki Page", sidebar_item.wiki_page)
					sync_wiki_page_to_markdown(page)
				except Exception as e:
					frappe.log_error(f"Error syncing page {sidebar_item.wiki_page} from sidebar update: {str(e)}", "Wiki Sidebar Sync")
					continue
					
	except Exception as e:
		frappe.log_error(f"Wiki Space Sidebar Sync Error: {str(e)}", "Wiki Sidebar Sync Error")


def check_and_fix_misplaced_pages():
	"""Scheduled task: Check for pages that are in wrong groups and fix them"""
	try:
		# Get all enabled settings
		settings_list = frappe.get_all("Wiki Dev Settings", 
			filters={"enabled": 1, "sync_on_wiki_update": 1},
			fields=["name"]
		)
		
		if not settings_list:
			return
		
		for setting_data in settings_list:
			settings = frappe.get_doc("Wiki Dev Settings", setting_data.name)
			docs_path = settings.get_full_docs_path()
			
			if not docs_path or not os.path.exists(docs_path):
				continue
			
			# Check each wiki space folder
			for item in os.listdir(docs_path):
				item_path = os.path.join(docs_path, item)
				config_path = os.path.join(item_path, "_config.json")
				
				if os.path.isdir(item_path) and os.path.exists(config_path):
					with open(config_path, 'r') as f:
						config = json.load(f)
					
					wiki_space_route = config.get("wiki_space", {}).get("route")
					if not wiki_space_route:
						continue
					
					# Find wiki space
					wiki_spaces = frappe.get_all("Wiki Space", filters={"route": wiki_space_route}, limit=1)
					if not wiki_spaces:
						continue
					
					wiki_space = frappe.get_doc("Wiki Space", wiki_spaces[0].name)
					
					# Check each page in the sidebar
					pages_fixed = 0
					for sidebar_item in wiki_space.wiki_sidebars:
						if not sidebar_item.wiki_page:
							continue
						
						try:
							page = frappe.get_doc("Wiki Page", sidebar_item.wiki_page)
							current_parent = sidebar_item.parent_label
							
							# Check if page is in wrong group in config
							page_in_wrong_group = False
							for group in config.get("groups", []):
								for page_config in group.get("pages", []):
									if page_config.get("route") == page.route and group.get("name") != current_parent:
										page_in_wrong_group = True
										break
								if page_in_wrong_group:
									break
							
							# Fix misplaced page
							if page_in_wrong_group:
								synced = sync_misplaced_page(page, config, item_path, settings, config_path, wiki_space_route)
								if synced:
									pages_fixed += 1
							
						except Exception as page_error:
							frappe.log_error(f"Error fixing page {sidebar_item.wiki_page}: {str(page_error)}", "Wiki Misplaced Page Fix")
							continue
					
					if pages_fixed > 0:
						print(f"Wiki Sync: Fixed {pages_fixed} misplaced pages in {wiki_space_route}")
						
	except Exception as e:
		frappe.log_error(f"Wiki Misplaced Page Check Error: {str(e)}", "Wiki Misplaced Page Check")


def fix_page_placement_if_needed(doc_name, doc_route):
	"""Background job: Check if a specific page needs to be moved from Miscellaneous"""
	try:
		# Get the page document
		if not frappe.db.exists("Wiki Page", doc_name):
			return
		
		page = frappe.get_doc("Wiki Page", doc_name)
		
		# Find settings that match this wiki page
		all_settings = frappe.get_all("Wiki Dev Settings", 
			filters={"enabled": 1, "sync_on_wiki_update": 1},
			fields=["name", "app_name", "docs_folder_path", "wiki_space_name"]
		)
		
		for setting_data in all_settings:
			settings = frappe.get_doc("Wiki Dev Settings", setting_data.name)
			docs_path = settings.get_full_docs_path()
			
			if not docs_path or not os.path.exists(docs_path):
				continue
			
			# Check each wiki space folder
			for item in os.listdir(docs_path):
				item_path = os.path.join(docs_path, item)
				config_path = os.path.join(item_path, "_config.json")
				
				if os.path.isdir(item_path) and os.path.exists(config_path):
					with open(config_path, 'r') as f:
						config = json.load(f)
					
					wiki_space_route = config.get("wiki_space", {}).get("route")
					
					# Check if this page belongs to this wiki space
					if wiki_space_route and page.route.startswith(f"{wiki_space_route}/"):
						# Try to fix misplacement
						synced = sync_misplaced_page(page, config, item_path, settings, config_path, wiki_space_route)
						if synced:
							print(f"Wiki Sync: Background job fixed placement for page '{page.title}'")
							return
						
						# If not misplaced, try normal sync
						synced = sync_existing_page(page, config, item_path, settings, wiki_space_route)
						if not synced:
							synced = sync_new_page(page, config, item_path, settings, config_path, wiki_space_route)
						
						if synced:
							return
						
	except Exception as e:
		frappe.log_error(f"Background page placement fix error: {str(e)}", "Wiki Background Fix")


def sync_existing_page(doc, config, item_path, settings, wiki_space_route=None):
	"""Sync existing page that's already in _config.json"""
	config_path = os.path.join(item_path, "_config.json")

	# In auto-discovery mode, don't create new files - only update existing bracketed files
	if is_auto_discovery_mode(config_path):
		# Find the actual bracketed file that corresponds to this route
		route_without_space = doc.route.replace(f"{wiki_space_route}/", "") if wiki_space_route else doc.route

		# Search for existing bracketed files that would generate this clean route
		for group in config.get("groups", []):
			for page_config in group.get("pages", []):
				if page_config['route'] == doc.route:
					# Found matching page in auto-discovery config
					bracketed_file_path = os.path.join(item_path, page_config["file"])

					# Only update if the bracketed file actually exists
					if os.path.exists(bracketed_file_path):
						with open(bracketed_file_path, 'w') as f:
							f.write(doc.content)
						print(f"Wiki Sync: Updated existing bracketed page '{doc.title}' to {bracketed_file_path}")
						return True

		return False  # Page not found in existing bracketed structure

	# Traditional mode - work with config as before
	for group in config.get("groups", []):
		for page_config in group.get("pages", []):
			expected_route = page_config['route']

			if doc.route == expected_route:
				# Check if parent label has changed
				if wiki_space_route:
					current_parent_label = get_current_parent_label(doc, wiki_space_route)
					if current_parent_label and current_parent_label != group.get("name"):
						# Parent label changed - return False to let sync_misplaced_page handle it
						return False

				# Sync this page back to markdown
				# File paths in config are relative to wiki space folder
				file_path = os.path.join(item_path, page_config["file"])

				# Ensure directory exists
				if settings.create_missing_folders:
					os.makedirs(os.path.dirname(file_path), exist_ok=True)

				# Write updated content
				with open(file_path, 'w') as f:
					f.write(doc.content)

				print(f"Wiki Sync: Updated existing page '{doc.title}' to {file_path}")
				return True

	return False


def get_current_parent_label(doc, wiki_space_route):
	"""Get the current parent label for a page from the Wiki Space sidebar"""
	try:
		wiki_spaces = frappe.get_all("Wiki Space", filters={"route": wiki_space_route}, limit=1)
		if not wiki_spaces:
			return None
		
		wiki_space = frappe.get_doc("Wiki Space", wiki_spaces[0].name)
		
		for sidebar_item in wiki_space.wiki_sidebars:
			if sidebar_item.wiki_page == doc.name:
				return sidebar_item.parent_label
		
		return None
	except:
		return None


def sync_new_page(doc, config, item_path, settings, config_path, wiki_space_route):
	"""Handle new wiki page created in UI - add to config and create markdown file"""
	try:
		# In auto-discovery mode, do NOT create new files automatically
		# Users should manually create bracketed files for auto-discovery
		if is_auto_discovery_mode(config_path):
			print(f"Wiki Sync: Auto-discovery mode - skipping automatic file creation for '{doc.title}'. Please create bracketed file manually.")
			return False

		# Traditional mode - create files as before
		# Extract page name from route (e.g., "docs/new-page" -> "new-page")
		page_name = doc.route.replace(f"{wiki_space_route}/", "")

		# Get the parent label (sidebar group) from the Wiki Space
		# Find the wiki space that matches this route
		wiki_spaces = frappe.get_all("Wiki Space", filters={"route": wiki_space_route}, limit=1)
		if not wiki_spaces:
			return False

		wiki_space = frappe.get_doc("Wiki Space", wiki_spaces[0].name)
		parent_label = None

		# Find the sidebar entry for this page
		for sidebar_item in wiki_space.wiki_sidebars:
			if sidebar_item.wiki_page == doc.name:
				parent_label = sidebar_item.parent_label
				break

		# Use "Miscellaneous" as default group if no parent label found
		if not parent_label:
			parent_label = "Miscellaneous"

		# Determine file path based on parent label
		# Convert parent label to folder-friendly name
		folder_name = parent_label.lower().replace(" ", "-").replace("_", "-")
		file_name = f"{page_name}.md"
		# For config file: relative path from wiki space folder
		relative_file_path = f"{folder_name}/{file_name}"
		# For file system: absolute path
		full_file_path = os.path.join(item_path, relative_file_path)

		# Create directory if needed
		if settings.create_missing_folders:
			os.makedirs(os.path.dirname(full_file_path), exist_ok=True)

		# Write markdown content
		with open(full_file_path, 'w') as f:
			f.write(doc.content)

		# Update _config.json to include this new page
		updated = update_config_with_new_page(config, parent_label, {
			"file": relative_file_path,
			"title": doc.title,
			"route": doc.route,
			"order": get_next_order_in_group(config, parent_label)
		})
		
		if updated:
			# Only write config if NOT in auto-discovery mode
			if not is_auto_discovery_mode(config_path):
				# Write updated config back to file
				with open(config_path, 'w') as f:
					json.dump(config, f, indent=2)
				print(f"Wiki Sync: Created new page '{doc.title}' at {full_file_path} and updated _config.json")
			else:
				print(f"Wiki Sync: Created new page '{doc.title}' at {full_file_path} (auto-discovery mode, config not updated)")
			return True
		
	except Exception as e:
		frappe.log_error(f"Error syncing new wiki page: {str(e)}", "Wiki Sync Error")
	
	return False


def sync_misplaced_page(doc, config, item_path, settings, config_path, wiki_space_route):
	"""Handle pages that exist in config but are in the wrong parent group"""
	try:
		# In auto-discovery mode, don't move files around - just update content in place
		if is_auto_discovery_mode(config_path):
			# Find the existing bracketed file and update its content
			for group in config.get("groups", []):
				for page_config in group.get("pages", []):
					if page_config.get("route") == doc.route:
						bracketed_file_path = os.path.join(item_path, page_config["file"])
						if os.path.exists(bracketed_file_path):
							with open(bracketed_file_path, 'w') as f:
								f.write(doc.content)
							print(f"Wiki Sync: Updated bracketed page content for '{doc.title}' in {bracketed_file_path}")
							return True
			return False  # Page not found in bracketed structure

		# Traditional mode - move files as before
		# Get the current parent label from sidebar
		wiki_spaces = frappe.get_all("Wiki Space", filters={"route": wiki_space_route}, limit=1)
		if not wiki_spaces:
			return False

		wiki_space = frappe.get_doc("Wiki Space", wiki_spaces[0].name)
		current_parent_label = None

		# Find the sidebar entry for this page
		for sidebar_item in wiki_space.wiki_sidebars:
			if sidebar_item.wiki_page == doc.name:
				current_parent_label = sidebar_item.parent_label
				break

		if not current_parent_label:
			return False

		# Look for this page in ANY group in the config
		page_found_in_group = None
		page_config_to_move = None

		for group in config.get("groups", []):
			for page_config in group.get("pages", []):
				if page_config.get("route") == doc.route:
					page_found_in_group = group.get("name")
					page_config_to_move = page_config.copy()
					# Remove from current group
					group["pages"].remove(page_config)
					break
			if page_found_in_group:
				break

		# If page was found in config but in wrong group, move it
		if page_found_in_group and page_found_in_group != current_parent_label:
			# Update the file path in the page config
			page_name = doc.route.replace(f"{wiki_space_route}/", "")
			folder_name = current_parent_label.lower().replace(" ", "-").replace("_", "-")
			old_file_path = page_config_to_move["file"]
			# For config file: relative path from wiki space folder
			new_file_path = f"{folder_name}/{page_name}.md"

			# Move the actual file
			old_full_path = os.path.join(item_path, "..", old_file_path)
			new_full_path = os.path.join(item_path, new_file_path)

			# Create directory if needed
			if settings.create_missing_folders:
				os.makedirs(os.path.dirname(new_full_path), exist_ok=True)

			# Move file if it exists
			if os.path.exists(old_full_path):
				import shutil
				shutil.move(old_full_path, new_full_path)
			else:
				# Create new file with current content
				with open(new_full_path, 'w') as f:
					f.write(doc.content)

			# Update the page config
			page_config_to_move["file"] = new_file_path

			# Add to correct group
			updated = update_config_with_new_page(config, current_parent_label, page_config_to_move)
			
			if updated:
				# Clean up empty groups
				config["groups"] = [g for g in config.get("groups", []) if g.get("pages")]

				# Only write config if NOT in auto-discovery mode
				if not is_auto_discovery_mode(config_path):
					# Write updated config back to file
					with open(config_path, 'w') as f:
						json.dump(config, f, indent=2)
					print(f"Wiki Sync: Moved page '{doc.title}' from '{page_found_in_group}' to '{current_parent_label}' group")
				else:
					print(f"Wiki Sync: Moved page '{doc.title}' from '{page_found_in_group}' to '{current_parent_label}' group (auto-discovery mode, config not updated)")
				return True
		
		return False
		
	except Exception as e:
		frappe.log_error(f"Error syncing misplaced page: {str(e)}", "Wiki Misplaced Page Sync")
		return False


def update_config_with_new_page(config, parent_label, page_config):
	"""Add new page to the appropriate group in _config.json"""
	try:
		groups = config.get("groups", [])
		
		# Find existing group with matching name
		target_group = None
		for group in groups:
			if group.get("name") == parent_label:
				target_group = group
				break
		
		# Create new group if not found
		if not target_group:
			target_group = {
				"name": parent_label,
				"order": len(groups) + 1,
				"pages": []
			}
			groups.append(target_group)
			config["groups"] = groups
		
		# Add page to group (avoid duplicates)
		existing_routes = [p.get("route") for p in target_group.get("pages", [])]
		if page_config["route"] not in existing_routes:
			target_group.setdefault("pages", []).append(page_config)
			# Resequence all pages in this group to maintain order from 1
			resequence_pages_in_group(config, parent_label)
			return True
		
	except Exception as e:
		frappe.log_error(f"Error updating config with new page: {str(e)}", "Wiki Config Update")
	
	return False


def get_next_order_in_group(config, parent_label):
	"""Get the next order number for pages in a specific group (sequential from 1)"""
	try:
		for group in config.get("groups", []):
			if group.get("name") == parent_label:
				pages = group.get("pages", [])
				if pages:
					# Count existing pages and return next sequential number
					return len(pages) + 1
				return 1
		return 1
	except:
		return 1


def resequence_pages_in_group(config, group_name):
	"""Resequence all pages in a group to start from 1"""
	try:
		for group in config.get("groups", []):
			if group.get("name") == group_name:
				pages = group.get("pages", [])
				if pages:
					# Sort by current order first to maintain relative positioning
					pages.sort(key=lambda x: x.get("order", 0))
					# Resequence starting from 1
					for i, page in enumerate(pages, 1):
						page["order"] = i
				return True
		return False
	except:
		return False


def resequence_all_pages_in_config(config):
	"""Resequence all pages in all groups to start from 1"""
	try:
		for group in config.get("groups", []):
			group_name = group.get("name")
			if group_name:
				resequence_pages_in_group(config, group_name)
		return True
	except:
		return False


@frappe.whitelist()
def debug_wiki_pages():
	"""Debug function to check Wiki Pages"""
	try:
		pages = frappe.get_all("Wiki Page",
			filters=[["route", "like", "architecture/%"]],
			fields=["name", "route", "title"]
		)

		result = {"success": True, "pages": []}
		for page in pages:
			result["pages"].append({
				"route": page.route,
				"title": page.title,
				"name": page.name
			})

		return result
	except Exception as e:
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def debug_wiki_sidebar():
	"""Debug function to check Wiki Space sidebar"""
	try:
		wiki_space_name = frappe.db.get_value("Wiki Space", {"route": "architecture"}, "name")
		if not wiki_space_name:
			return {"success": False, "error": "Wiki Space not found"}

		wiki_space = frappe.get_doc("Wiki Space", wiki_space_name)

		result = {"success": True, "sidebar_items": [], "wiki_space": wiki_space_name}
		for item in wiki_space.wiki_sidebars:
			result["sidebar_items"].append({
				"parent_label": item.parent_label,
				"wiki_page": item.wiki_page,
				"title": frappe.db.get_value("Wiki Page", item.wiki_page, "title") if item.wiki_page else None
			})

		return result
	except Exception as e:
		return {"success": False, "error": str(e)}


def is_auto_discovery_mode(config_path):
	"""Check if we're in auto-discovery mode (minimal config with only wiki_space)"""
	try:
		if not os.path.exists(config_path):
			return True  # No config file means auto-discovery

		with open(config_path, 'r') as f:
			config = json.load(f)

		# Auto-discovery mode if no groups are defined or groups are empty
		return "groups" not in config or not config.get("groups")
	except:
		return True  # Error reading config, assume auto-discovery


def parse_bracket_notation(name):
	"""Parse bracket notation [n]name to extract order and clean name"""
	import re

	# Match pattern [number]name
	match = re.match(r'^\[(\d+)\](.+)$', name)
	if match:
		order = int(match.group(1))
		clean_name = match.group(2)
		return order, clean_name

	# No bracket notation found
	return None, name


def clean_name_to_title(name):
	"""Convert file/folder name to human-readable title"""
	# Remove .md extension
	if name.endswith('.md'):
		name = name[:-3]

	# Convert dashes/underscores to spaces and title case
	title = name.replace('-', ' ').replace('_', ' ')
	title = ' '.join(word.capitalize() for word in title.split())

	return title


def scan_wiki_folder_structure(folder_path, wiki_space_route):
	"""Scan folder structure and auto-generate config using bracket notation"""
	try:
		import os

		if not os.path.exists(folder_path):
			return None

		groups = []

		# Get all subdirectories (groups)
		items = []
		for item in os.listdir(folder_path):
			item_path = os.path.join(folder_path, item)
			if os.path.isdir(item_path) and not item.startswith('_'):
				items.append(item)

		# Sort and process folders
		folder_orders = {}
		unordered_folders = []

		for folder in items:
			order, clean_name = parse_bracket_notation(folder)
			if order is not None:
				folder_orders[order] = (folder, clean_name)
			else:
				unordered_folders.append(folder)

		# Sort folders: ordered first, then unordered alphabetically
		sorted_folders = []
		for order in sorted(folder_orders.keys()):
			folder, clean_name = folder_orders[order]
			# Use clean name for title, but keep original folder name
			group_title = clean_name_to_title(clean_name)
			sorted_folders.append((folder, group_title, order))

		# Add unordered folders after ordered ones
		next_order = max(folder_orders.keys()) + 1 if folder_orders else 1
		for folder in sorted(unordered_folders):
			# For non-bracketed folders, use the folder name as-is for title
			group_title = clean_name_to_title(folder)
			sorted_folders.append((folder, group_title, next_order))
			next_order += 1

		# Process each group folder
		for folder_name, group_title, group_order in sorted_folders:
			folder_path_full = os.path.join(folder_path, folder_name)

			# Get all .md files in this folder
			pages = []
			page_files = []
			for item in os.listdir(folder_path_full):
				if item.endswith('.md') and not item.startswith('_'):
					page_files.append(item)

			# Sort pages similar to folders
			page_orders = {}
			unordered_pages = []

			for page_file in page_files:
				page_name = page_file[:-3]  # Remove .md
				order, clean_name = parse_bracket_notation(page_name)
				if order is not None:
					page_orders[order] = (page_file, clean_name)
				else:
					unordered_pages.append(page_file)

			# Sort pages: ordered first, then unordered alphabetically
			sorted_pages = []
			for order in sorted(page_orders.keys()):
				page_file, clean_name = page_orders[order]
				sorted_pages.append((page_file, clean_name, order))

			# Add unordered pages after ordered ones
			next_page_order = max(page_orders.keys()) + 1 if page_orders else 1
			for page_file in sorted(unordered_pages):
				page_name = page_file[:-3]  # Remove .md
				clean_name = clean_name_to_title(page_name)
				sorted_pages.append((page_file, clean_name, next_page_order))
				next_page_order += 1

			# Build pages list for this group
			for page_file, page_title, page_order in sorted_pages:
				page_name = page_file[:-3]  # Remove .md

				# Generate clean route (remove brackets) for Wiki Page matching
				_, clean_page_name = parse_bracket_notation(page_name)
				page_route = f"{wiki_space_route}/{clean_page_name}"

				# Convert name to proper title only if it was auto-generated
				if page_title == page_name:  # Was auto-generated from filename
					# For bracketed files, extract clean name for title
					page_title = clean_name_to_title(clean_page_name)
				elif '[' in page_title and ']' in page_title:  # Was extracted from bracket
					page_title = clean_name_to_title(page_title)

				# File path relative to wiki space folder - keep actual folder/file names
				relative_file_path = f"{folder_name}/{page_file}"

				pages.append({
					"file": relative_file_path,
					"title": page_title,
					"route": page_route,
					"order": page_order
				})

			# Add group to config
			if pages:  # Only add groups that have pages
				groups.append({
					"name": group_title,
					"order": group_order,
					"pages": pages
				})

		return groups

	except Exception as e:
		frappe.log_error(f"Error scanning wiki folder structure: {str(e)}", "Wiki Auto-Discovery")
		return None


def load_wiki_config_with_autodiscovery(folder_path, wiki_space_route):
	"""Load config from _config.json or auto-generate from folder structure"""
	try:
		config_path = os.path.join(folder_path, "_config.json")

		# Try to load existing _config.json
		if os.path.exists(config_path):
			with open(config_path, 'r') as f:
				config = json.load(f)

			# Check if it's a minimal config (no groups defined)
			if "groups" not in config or not config["groups"]:
				# Use auto-discovery for groups
				auto_groups = scan_wiki_folder_structure(folder_path, wiki_space_route)
				if auto_groups:
					config["groups"] = auto_groups
					print(f"Wiki Auto-Discovery: Generated {len(auto_groups)} groups from folder structure")

			return config

		else:
			# No config file - create minimal config with auto-discovery
			auto_groups = scan_wiki_folder_structure(folder_path, wiki_space_route)
			if auto_groups:
				config = {
					"wiki_space": {
						"route": wiki_space_route,
						"title": f"{wiki_space_route.title()} Documentation",
						"description": f"Auto-generated documentation for {wiki_space_route}"
					},
					"groups": auto_groups
				}
				print(f"Wiki Auto-Discovery: Created config with {len(auto_groups)} groups from folder structure")
				return config

		return None

	except Exception as e:
		frappe.log_error(f"Error loading wiki config with auto-discovery: {str(e)}", "Wiki Config Loading")
		return None


def sync_wiki_page_deletion_to_markdown(doc, method=None):
	"""Hook function: Remove markdown file when wiki page is deleted"""
	try:
		# Find settings that match this wiki page's app
		all_settings = frappe.get_all("Wiki Dev Settings", 
			filters={"enabled": 1, "sync_on_wiki_update": 1},
			fields=["name", "app_name", "docs_folder_path", "wiki_space_name"]
		)
		
		for setting_data in all_settings:
			settings = frappe.get_doc("Wiki Dev Settings", setting_data.name)
			docs_path = settings.get_full_docs_path()
			
			if not docs_path or not os.path.exists(docs_path):
				continue
			
			# Search through all folders for matching wiki page
			for item in os.listdir(docs_path):
				item_path = os.path.join(docs_path, item)
				config_path = os.path.join(item_path, "_config.json")
				
				if os.path.isdir(item_path) and os.path.exists(config_path):
					with open(config_path, 'r') as f:
						config = json.load(f)
					
					wiki_space_route = config.get("wiki_space", {}).get("route")
					
					# Check if this page belongs to this wiki space
					if wiki_space_route and doc.route.startswith(f"{wiki_space_route}/"):
						# Find and remove the page from config
						page_removed = remove_page_from_config(doc, config, item_path, config_path)
						
						if page_removed:
							print(f"Wiki Sync: Removed page '{doc.title}' from markdown and _config.json")
							return
		
	except Exception as e:
		frappe.log_error(f"Wiki Page Deletion Sync Error: {str(e)}", "Wiki Sync Error")


def remove_page_from_config(doc, config, item_path, config_path):
	"""Remove page from _config.json and delete markdown file"""
	try:
		page_found = False
		file_path = None
		
		# Find and remove the page from config
		for group in config.get("groups", []):
			pages = group.get("pages", [])
			for i, page_config in enumerate(pages):
				if page_config.get("route") == doc.route:
					# Found the page to remove
					# File paths in config are relative to wiki space folder
					file_path = os.path.join(item_path, page_config["file"])
					pages.pop(i)
					page_found = True
					break
			
			if page_found:
				break
		
		if page_found:
			# Remove empty groups
			config["groups"] = [g for g in config.get("groups", []) if g.get("pages")]

			# Only update config file if NOT in auto-discovery mode
			if not is_auto_discovery_mode(config_path):
				# Update config file
				with open(config_path, 'w') as f:
					json.dump(config, f, indent=2)
			
			# Delete markdown file if it exists
			if file_path and os.path.exists(file_path):
				os.remove(file_path)
				
				# Remove empty directory if no other files
				dir_path = os.path.dirname(file_path)
				if os.path.exists(dir_path) and not os.listdir(dir_path):
					os.rmdir(dir_path)
			
			return True
		
	except Exception as e:
		frappe.log_error(f"Error removing page from config: {str(e)}", "Wiki Config Update")
	
	return False