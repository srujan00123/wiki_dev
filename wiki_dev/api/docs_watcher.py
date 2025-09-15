import frappe
import os
import json
from pathlib import Path

@frappe.whitelist()
def sync_docs_folder_to_wiki(settings_name):
	"""Sync docs folder changes to wiki - detect deleted files and remove wiki pages"""
	try:
		settings = frappe.get_doc("Wiki Dev Settings", settings_name)
		if not settings.enabled or not settings.sync_on_wiki_update:
			return {"success": False, "message": "Sync disabled in settings"}
		
		docs_path = settings.get_full_docs_path()
		if not docs_path or not os.path.exists(docs_path):
			return {"success": False, "message": f"Docs path not found: {docs_path}"}
		
		# Get all config files in docs folder
		results = []
		for item in os.listdir(docs_path):
			item_path = os.path.join(docs_path, item)
			config_path = os.path.join(item_path, "_config.json")
			
			if os.path.isdir(item_path) and os.path.exists(config_path):
				result = sync_single_docs_folder(item_path, config_path, settings)
				results.append({
					"folder": item,
					"result": result
				})
		
		return {
			"success": True,
			"message": f"Synced {len(results)} doc folders",
			"results": results
		}
		
	except Exception as e:
		frappe.log_error(f"Docs folder sync error: {str(e)}", "Docs Sync Error")
		return {"success": False, "error": str(e)}


def sync_single_docs_folder(item_path, config_path, settings):
	"""Sync a single docs folder - remove wiki pages for missing markdown files"""
	try:
		with open(config_path, 'r') as f:
			config = json.load(f)
		
		wiki_space_route = config.get("wiki_space", {}).get("route")
		if not wiki_space_route:
			return {"success": False, "message": "No wiki space route in config"}
		
		pages_removed = []
		config_updated = False
		
		# Check each page in config to see if markdown file still exists
		for group in config.get("groups", []):
			pages_to_keep = []
			
			for page_config in group.get("pages", []):
				# File paths in config are relative to wiki space folder
				file_path = os.path.join(item_path, page_config.get("file", ""))
				
				# If markdown file doesn't exist, remove corresponding wiki page
				if not os.path.exists(file_path):
					wiki_page_route = page_config.get("route")
					
					# Find and delete wiki page
					wiki_pages = frappe.get_all("Wiki Page", filters={"route": wiki_page_route})
					for wiki_page in wiki_pages:
						frappe.delete_doc("Wiki Page", wiki_page.name)
						pages_removed.append({
							"route": wiki_page_route,
							"title": page_config.get("title"),
							"file": page_config.get("file")
						})
					
					config_updated = True
					# Don't add this page to pages_to_keep
				else:
					pages_to_keep.append(page_config)
			
			# Update group with remaining pages
			group["pages"] = pages_to_keep
		
		# Remove empty groups
		config["groups"] = [g for g in config.get("groups", []) if g.get("pages")]
		
		# Update config file if changes were made
		if config_updated:
			with open(config_path, 'w') as f:
				json.dump(config, f, indent=2)
		
		return {
			"success": True,
			"pages_removed": pages_removed,
			"config_updated": config_updated,
			"message": f"Removed {len(pages_removed)} wiki pages for missing markdown files"
		}
		
	except Exception as e:
		frappe.log_error(f"Single docs folder sync error: {str(e)}", "Docs Sync Error")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def sync_all_docs_folders():
	"""Sync all enabled docs folders to remove wiki pages for deleted markdown files"""
	try:
		all_settings = frappe.get_all("Wiki Dev Settings", 
			filters={"enabled": 1, "sync_on_wiki_update": 1},
			fields=["name"]
		)
		
		results = []
		for setting_data in all_settings:
			result = sync_docs_folder_to_wiki(setting_data.name)
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
def check_orphaned_wiki_pages(settings_name=None):
	"""Find wiki pages that don't have corresponding markdown files"""
	try:
		if settings_name:
			settings_list = [frappe.get_doc("Wiki Dev Settings", settings_name)]
		else:
			settings_list = [frappe.get_doc("Wiki Dev Settings", s.name) 
				for s in frappe.get_all("Wiki Dev Settings", filters={"enabled": 1})]
		
		orphaned_pages = []
		
		for settings in settings_list:
			docs_path = settings.get_full_docs_path()
			if not docs_path or not os.path.exists(docs_path):
				continue
			
			for item in os.listdir(docs_path):
				item_path = os.path.join(docs_path, item)
				config_path = os.path.join(item_path, "_config.json")
				
				if os.path.isdir(item_path) and os.path.exists(config_path):
					with open(config_path, 'r') as f:
						config = json.load(f)
					
					wiki_space_route = config.get("wiki_space", {}).get("route")
					if not wiki_space_route:
						continue
					
					# Get all wiki pages for this space
					wiki_pages = frappe.get_all("Wiki Page", 
						filters=[["route", "like", f"{wiki_space_route}/%"]],
						fields=["name", "title", "route"]
					)
					
					# Check if each wiki page has a corresponding markdown file
					for page in wiki_pages:
						page_in_config = False
						
						for group in config.get("groups", []):
							for page_config in group.get("pages", []):
								if page_config.get("route") == page.route:
									# File paths in config are relative to wiki space folder
									file_path = os.path.join(item_path, page_config.get("file", ""))
									if not os.path.exists(file_path):
										orphaned_pages.append({
											"name": page.name,
											"title": page.title,
											"route": page.route,
											"missing_file": page_config.get("file"),
											"settings": settings.name
										})
									page_in_config = True
									break
							if page_in_config:
								break
						
						# If page not found in config at all, it's orphaned
						if not page_in_config:
							orphaned_pages.append({
								"name": page.name,
								"title": page.title,
								"route": page.route,
								"missing_file": "Not in config",
								"settings": settings.name
							})
		
		return {
			"success": True,
			"orphaned_pages": orphaned_pages,
			"count": len(orphaned_pages)
		}
		
	except Exception as e:
		return {"success": False, "error": str(e)}