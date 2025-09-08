import frappe
import os
import shutil
import re
from frappe.utils import get_files_path


@frappe.whitelist()
def process_wiki_file_uploads(wiki_page_name, settings_name=None):
	"""Process wiki page to move /private/files/ images to public docs folder"""
	try:
		page = frappe.get_doc("Wiki Page", wiki_page_name)
		content = page.content
		
		if not content:
			return {"success": False, "message": "No content to process"}
		
		# Find all /private/files/ references
		private_file_pattern = r'!\[(.*?)\]\(/private/files/(.*?)\)'
		matches = re.findall(private_file_pattern, content)
		
		if not matches:
			return {"success": True, "message": "No private files to process"}
		
		# Get settings - either provided or find by wiki space
		settings = None
		if settings_name:
			settings = frappe.get_doc("Wiki Dev Settings", settings_name)
		else:
			# Try to find settings by wiki space
			if page.wiki_space:
				wiki_space_doc = frappe.get_doc("Wiki Space", page.wiki_space)
				# Find settings that match this wiki space route
				all_settings = frappe.get_all("Wiki Dev Settings", 
					filters={"enabled": 1},
					fields=["name", "wiki_route_prefix"]
				)
				for setting_data in all_settings:
					if wiki_space_doc.route.startswith(setting_data.wiki_route_prefix):
						settings = frappe.get_doc("Wiki Dev Settings", setting_data.name)
						break
		
		if not settings:
			return {"success": False, "message": "No Wiki Dev Settings found for this page"}
		
		docs_assets_path = settings.get_full_upload_path()
		if not docs_assets_path:
			return {"success": False, "message": "No upload path configured in settings"}
		
		os.makedirs(docs_assets_path, exist_ok=True)
		
		updated_content = content
		moved_files = []
		
		for alt_text, filename in matches:
			private_file_path = os.path.join(get_files_path(), filename)
			
			if os.path.exists(private_file_path):
				# Copy file to public docs folder
				public_file_path = os.path.join(docs_assets_path, filename)
				shutil.copy2(private_file_path, public_file_path)
				
				# Update content with new path
				old_ref = f'![{alt_text}](/private/files/{filename})'
				new_ref = f'![{alt_text}]({settings.public_assets_path}/images/{filename})'
				updated_content = updated_content.replace(old_ref, new_ref)
				
				moved_files.append(filename)
				
				# Remove original private file
				try:
					os.remove(private_file_path)
				except:
					pass  # Don't fail if we can't remove the original
		
		if moved_files:
			# Update wiki page
			page.content = updated_content
			page.save()
			
			return {
				"success": True,
				"message": f"Moved {len(moved_files)} files to public docs folder",
				"files": moved_files
			}
		
		return {"success": True, "message": "No files needed moving"}
		
	except Exception as e:
		frappe.log_error(f"Wiki File Processing Error: {str(e)}")
		return {"success": False, "error": str(e)}


def auto_process_wiki_page_files(doc, method=None):
	"""Hook function: Auto-process uploaded files when wiki page is saved"""
	try:
		if doc.content and '/private/files/' in doc.content:
			result = process_wiki_file_uploads(doc.name)
			if result.get("success") and result.get("files"):
				frappe.log("Wiki File Handler", f"Auto-moved {len(result.get('files', []))} files for {doc.title}")
	except Exception as e:
		frappe.log_error(f"Auto Wiki File Processing Error: {str(e)}")


@frappe.whitelist()
def upload_wiki_image(file_content, filename, settings_name, wiki_page_name=None):
	"""Custom upload handler for wiki images - saves directly to public docs folder"""
	try:
		settings = frappe.get_doc("Wiki Dev Settings", settings_name)
		
		# Ensure docs assets folder exists
		docs_assets_path = settings.get_full_upload_path()
		if not docs_assets_path:
			return {"success": False, "error": "No upload path configured in settings"}
		
		os.makedirs(docs_assets_path, exist_ok=True)
		
		# Save file to public docs folder
		file_path = os.path.join(docs_assets_path, filename)
		
		# Handle base64 or file content
		if isinstance(file_content, str) and file_content.startswith('data:'):
			# Base64 data
			import base64
			header, data = file_content.split(',', 1)
			with open(file_path, 'wb') as f:
				f.write(base64.b64decode(data))
		else:
			# Regular file content
			with open(file_path, 'wb') as f:
				f.write(file_content)
		
		# Return public URL path
		public_url = f"{settings.public_assets_path}/images/{filename}"
		
		return {
			"success": True,
			"file_url": public_url,
			"filename": filename,
			"message": f"File uploaded to docs assets: {filename}"
		}
		
	except Exception as e:
		frappe.log_error(f"Wiki Image Upload Error: {str(e)}")
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
		if not docs_path or not os.path.exists(docs_path):
			return {"success": False, "message": f"Docs path not found: {docs_path}"}
		
		folder_path = os.path.join(docs_path, folder_name)
		config_path = os.path.join(folder_path, "_config.json")
		
		if not os.path.exists(config_path):
			return {"success": False, "message": f"Configuration file not found: {config_path}"}
		
		import json
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