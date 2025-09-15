import frappe
import json
import os
from frappe import _




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
		
		# Find existing wiki space or create new one
		wiki_space = frappe.db.get_value("Wiki Space", {"route": wiki_space_route}, "name")
		if not wiki_space:
			# Create new Wiki Space
			wiki_space_doc = frappe.new_doc("Wiki Space")
			wiki_space_doc.route = wiki_space_route
			wiki_space_doc.insert()
			wiki_space = wiki_space_doc.name
		
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
			"message": f"Synced wiki space '{folder_name}' - {len(updates)} pages updated",
			"updates": updates
		}
		
	except Exception as e:
		frappe.db.rollback()
		return {"success": False, "error": str(e)}


def sync_wiki_page_to_markdown(doc, method=None):
	"""Hook function: Automatically sync wiki page changes to markdown files"""
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
				
				if os.path.isdir(item_path):
					# Load config with auto-discovery support
					config = load_wiki_config_with_autodiscovery(item_path, item)
					if not config:
						continue

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




def sync_existing_page(doc, config, item_path, settings, wiki_space_route=None):
	"""Sync existing page that's already in _config.json"""
	config_path = os.path.join(item_path, "_config.json")

	# In auto-discovery mode, don't create new files - only update existing bracketed files
	if is_auto_discovery_mode(config_path):
		# Find the actual bracketed file that corresponds to this route

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




def sync_new_page(doc, config, item_path, settings, config_path, wiki_space_route):
	"""Handle new wiki page created in UI - create markdown file in auto-discovery mode"""
	try:
		# In auto-discovery mode, do NOT create new files automatically
		# Users should manually create bracketed files for auto-discovery
		if is_auto_discovery_mode(config_path):
			print(f"Wiki Sync: Auto-discovery mode - skipping automatic file creation for '{doc.title}'. Please create bracketed file manually.")
			return False

		# For legacy full config mode, we could create files, but auto-discovery is preferred
		print(f"Wiki Sync: Please use auto-discovery mode with bracketed files for new page '{doc.title}'")
		return False

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

		# Legacy mode - not recommended, prefer auto-discovery
		return False

	except Exception as e:
		frappe.log_error(f"Error syncing misplaced page: {str(e)}", "Wiki Misplaced Page Sync")
		return False






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
			fields=["name"]
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

				if os.path.isdir(item_path):
					# Load config to get wiki space route
					config = load_wiki_config_with_autodiscovery(item_path, item)
					if not config:
						continue

					wiki_space_route = config.get("wiki_space", {}).get("route")

					# Check if this page belongs to this wiki space
					if wiki_space_route and doc.route.startswith(f"{wiki_space_route}/"):
						# Find and delete the markdown file
						for group in config.get("groups", []):
							for page_config in group.get("pages", []):
								if page_config.get("route") == doc.route:
									file_path = os.path.join(item_path, page_config["file"])
									if os.path.exists(file_path):
										os.remove(file_path)
										print(f"Wiki Sync: Removed markdown file for deleted page '{doc.title}'")
									return

	except Exception as e:
		frappe.log_error(f"Wiki Page Deletion Sync Error: {str(e)}", "Wiki Sync Error")