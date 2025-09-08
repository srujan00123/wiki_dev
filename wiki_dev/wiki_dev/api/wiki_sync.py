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
	"""Create Wiki Pages from markdown files based on folder configuration"""
	config_path = os.path.join(folder_path, "_config.json")
	
	with open(config_path, 'r') as f:
		config = json.load(f)
	
	wiki_space_route = config["wiki_space"]["route"]
	pages_created = 0
	
	for group in config.get("groups", []):
		for page_config in group.get("pages", []):
			file_path = os.path.join(folder_path, "..", page_config["file"])
			
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
	"""Setup hierarchical wiki sidebar from folder configuration"""
	config_path = os.path.join(folder_path, "_config.json")
	
	with open(config_path, 'r') as f:
		config = json.load(f)
	
	space_doc = frappe.get_doc("Wiki Space", wiki_space_name)
	wiki_space_route = config["wiki_space"]["route"]
	
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
		
		updates = []
		
		# Update each page from markdown files
		for group in config.get("groups", []):
			for page_config in group.get("pages", []):
				file_path = os.path.join(folder_path, "..", page_config["file"])
				
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
		# Add small delay to ensure sidebar changes are saved first
		import time
		if method == "after_insert":
			time.sleep(0.5)  # Brief delay for sidebar to be saved
		
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


def sync_existing_page(doc, config, item_path, settings, wiki_space_route=None):
	"""Sync existing page that's already in _config.json"""
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
				file_path = os.path.join(item_path, "..", page_config["file"])
				
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
		relative_file_path = f"docs/{folder_name}/{file_name}"
		full_file_path = os.path.join(item_path, "..", relative_file_path)
		
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
			# Write updated config back to file
			with open(config_path, 'w') as f:
				json.dump(config, f, indent=2)
			
			print(f"Wiki Sync: Created new page '{doc.title}' at {full_file_path} and updated _config.json")
			return True
		
	except Exception as e:
		frappe.log_error(f"Error syncing new wiki page: {str(e)}", "Wiki Sync Error")
	
	return False


def sync_misplaced_page(doc, config, item_path, settings, config_path, wiki_space_route):
	"""Handle pages that exist in config but are in the wrong parent group"""
	try:
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
			new_file_path = f"docs/{folder_name}/{page_name}.md"
			
			# Move the actual file
			old_full_path = os.path.join(item_path, "..", old_file_path)
			new_full_path = os.path.join(item_path, "..", new_file_path)
			
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
				
				# Write updated config back to file
				with open(config_path, 'w') as f:
					json.dump(config, f, indent=2)
				
				print(f"Wiki Sync: Moved page '{doc.title}' from '{page_found_in_group}' to '{current_parent_label}' group")
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
			return True
		
	except Exception as e:
		frappe.log_error(f"Error updating config with new page: {str(e)}", "Wiki Config Update")
	
	return False


def get_next_order_in_group(config, parent_label):
	"""Get the next order number for pages in a specific group"""
	try:
		for group in config.get("groups", []):
			if group.get("name") == parent_label:
				pages = group.get("pages", [])
				if pages:
					max_order = max(p.get("order", 0) for p in pages)
					return max_order + 1
				return 1
		return 1
	except:
		return 1


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
					file_path = os.path.join(item_path, "..", page_config["file"])
					pages.pop(i)
					page_found = True
					break
			
			if page_found:
				break
		
		if page_found:
			# Remove empty groups
			config["groups"] = [g for g in config.get("groups", []) if g.get("pages")]
			
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