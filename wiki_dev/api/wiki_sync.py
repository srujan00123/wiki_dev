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
	if settings.use_parent_label_folders and settings.default_parent_labels:
		parent_labels = [label.strip() for label in settings.default_parent_labels.split(',')]
	else:
		parent_labels = []
	
	# Create sidebar structure using parent_label for folder hierarchy
	for group in sorted(config.get("groups", []), key=lambda x: x.get("order", 999)):
		group_name = group["name"]
		
		# Use configured parent label or group name
		parent_label = parent_labels[0] if parent_labels else group_name
		
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


@frappe.whitelist()
def sync_wiki_to_markdown(settings_name, folder_name=None):
	"""Sync Wiki Pages back to markdown files (bi-directional sync)"""
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
		updates = []
		
		# Update markdown files from wiki pages
		for group in config.get("groups", []):
			for page_config in group.get("pages", []):
				# Use the full route from config
				page_route = page_config['route']
				
				# Find wiki page
				wiki_page_doc = frappe.db.get_value("Wiki Page", {"route": page_route}, "name")
				if wiki_page_doc:
					page = frappe.get_doc("Wiki Page", wiki_page_doc)
					
					file_path = os.path.join(folder_path, "..", page_config["file"])
					
					# Read current markdown file
					current_content = ""
					if os.path.exists(file_path):
						with open(file_path, 'r') as f:
							current_content = f.read()
					
					# Update if content differs
					if current_content != page.content:
						# Ensure directory exists
						if settings.create_missing_folders:
							os.makedirs(os.path.dirname(file_path), exist_ok=True)
						
						# Write updated content
						with open(file_path, 'w') as f:
							f.write(page.content)
						updates.append(f"Synced '{page_config['title']}' to markdown")
		
		return {
			"success": True,
			"message": f"Synced {len(updates)} pages to markdown files",
			"updates": updates
		}
		
	except Exception as e:
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
			
			if not os.path.exists(docs_path):
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
						# Find the corresponding page config
						for group in config.get("groups", []):
							for page_config in group.get("pages", []):
								# Use the full route from config
								expected_route = page_config['route']
								
								if doc.route == expected_route:
									# Sync this page back to markdown
									file_path = os.path.join(item_path, "..", page_config["file"])
									
									# Ensure directory exists
									if settings.create_missing_folders:
										os.makedirs(os.path.dirname(file_path), exist_ok=True)
									
									# Write updated content
									with open(file_path, 'w') as f:
										f.write(doc.content)
									
									frappe.log("Wiki Sync", f"Synced wiki page '{doc.title}' to {file_path}")
									return
		
	except Exception as e:
		frappe.log_error(f"Wiki to Markdown Sync Error: {str(e)}", "Wiki Sync Error")


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