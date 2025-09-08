# Copyright (c) 2025, srujan.00123@gmail.com and contributors
# For license information, please see license.txt

import frappe
import os
from frappe.model.document import Document


class WikiDevSettings(Document):
	def before_save(self):
		"""Auto-populate default values before saving"""
		self.set_default_paths()

	def validate(self):
		"""Validate Wiki Dev Settings configuration"""
		self.validate_paths()
		self.validate_app_exists()
	
	def after_insert(self):
		"""Auto-add wiki sync hook to target app after creation"""
		if self.sync_on_migrate:
			self.add_wiki_sync_hook()
	
	def on_update(self):
		"""Handle wiki sync hook when settings are updated"""
		if self.has_value_changed("sync_on_migrate"):
			if self.sync_on_migrate:
				self.add_wiki_sync_hook()
			else:
				self.remove_wiki_sync_hook()

	def set_default_paths(self):
		"""Set default paths based on app_name if not provided"""
		if self.app_name:
			# Set default wiki_space_name if not provided
			if not self.wiki_space_name:
				self.wiki_space_name = "docs"
			
			# Set default docs_folder_path if not provided
			if not self.docs_folder_path:
				self.docs_folder_path = f"apps/{self.app_name}/docs/{self.wiki_space_name}"
			
			# Set default wiki_route_prefix if not provided
			if not self.wiki_route_prefix:
				self.wiki_route_prefix = self.wiki_space_name.replace('_', '-')
			
			# Set default file_upload_path if not provided
			if not self.file_upload_path:
				self.file_upload_path = f"apps/{self.app_name}/public/docs/images"
			
			# Set default public_assets_path if not provided
			if not self.public_assets_path:
				self.public_assets_path = f"/assets/{self.app_name}/docs"

	def validate_paths(self):
		"""Validate file paths are properly formatted"""
		if self.docs_folder_path:
			if not self.docs_folder_path.startswith('apps/'):
				frappe.throw("Docs folder path should start with apps/")
		
		if self.file_upload_path:
			if not self.file_upload_path.startswith('apps/'):
				frappe.throw("File upload path should start with apps/")
		
		if self.public_assets_path:
			if not self.public_assets_path.startswith('/assets/'):
				frappe.throw("Public assets path should start with /assets/")

	def validate_app_exists(self):
		"""Check if the specified app exists"""
		if self.app_name:
			try:
				app_path = frappe.get_app_path(self.app_name)
				if not os.path.exists(app_path):
					frappe.throw(f"App '{self.app_name}' does not exist")
			except:
				frappe.throw(f"App '{self.app_name}' is not installed")

	def get_full_docs_path(self):
		"""Get the absolute path to docs folder"""
		if not self.docs_folder_path:
			return None
		bench_path = frappe.utils.get_bench_path()
		return os.path.join(bench_path, self.docs_folder_path)

	def get_full_upload_path(self):
		"""Get the absolute path to file upload folder"""
		if not self.file_upload_path:
			return None
		bench_path = frappe.utils.get_bench_path()
		return os.path.join(bench_path, self.file_upload_path)

	@staticmethod
	def get_settings_for_app(app_name):
		"""Get Wiki Dev Settings for a specific app"""
		settings = frappe.get_all("Wiki Dev Settings", 
			filters={"app_name": app_name, "enabled": 1},
			limit=1
		)
		if settings:
			return frappe.get_doc("Wiki Dev Settings", settings[0].name)
		return None

	@staticmethod
	def get_all_enabled_settings():
		"""Get all enabled Wiki Dev Settings"""
		return frappe.get_all("Wiki Dev Settings", 
			filters={"enabled": 1},
			fields=["name", "app_name", "wiki_space_name", "docs_folder_path", 
					"wiki_route_prefix", "sync_on_migrate", "sync_on_wiki_update"]
		)

	def add_wiki_sync_hook(self):
		"""Add wiki sync hook to the target app's hooks.py"""
		try:
			hooks_path = self.get_app_hooks_path()
			if not hooks_path or not os.path.exists(hooks_path):
				frappe.log_error(f"Hooks file not found: {hooks_path}", "Wiki Hook Setup")
				return False
			
			# Read current hooks file
			with open(hooks_path, 'r') as f:
				content = f.read()
			
			wiki_hook = 'wiki_dev.wiki_dev.api.wiki_sync.sync_all_enabled_settings'
			
			# Check if hook already exists
			if wiki_hook in content:
				return True  # Already exists
			
			# Add hook to after_migrate
			if 'after_migrate = [' in content:
				# Hook list exists, add to it
				if 'after_migrate = []' in content:
					# Empty list, replace with wiki hook
					content = content.replace(
						'after_migrate = []',
						f'after_migrate = [\n\t"{wiki_hook}"  # Sync wiki docs on migration\n]'
					)
				else:
					# Add to existing list
					lines = content.split('\n')
					for i, line in enumerate(lines):
						if line.strip().startswith('after_migrate = ['):
							# Find the closing bracket
							bracket_count = line.count('[') - line.count(']')
							j = i
							while j < len(lines) and bracket_count > 0:
								j += 1
								if j < len(lines):
									bracket_count += lines[j].count('[') - lines[j].count(']')
							
							# Insert wiki hook before the closing bracket
							if j < len(lines):
								lines.insert(j, f'\t"{wiki_hook}",  # Sync wiki docs on migration')
							break
					content = '\n'.join(lines)
			else:
				# No after_migrate hook exists, add it
				content += f'\n\n# Wiki sync hook (auto-added by wiki-dev)\nafter_migrate = [\n\t"{wiki_hook}"  # Sync wiki docs on migration\n]\n'
			
			# Write back to file
			with open(hooks_path, 'w') as f:
				f.write(content)
			
			frappe.msgprint(f"Added wiki sync hook to {self.app_name}/hooks.py")
			return True
			
		except Exception as e:
			frappe.log_error(f"Failed to add wiki sync hook: {str(e)}", "Wiki Hook Setup")
			return False

	def remove_wiki_sync_hook(self):
		"""Remove wiki sync hook from the target app's hooks.py"""
		try:
			hooks_path = self.get_app_hooks_path()
			if not hooks_path or not os.path.exists(hooks_path):
				return False
			
			# Read current hooks file
			with open(hooks_path, 'r') as f:
				content = f.read()
			
			wiki_hook = 'wiki_dev.wiki_dev.api.wiki_sync.sync_all_enabled_settings'
			
			# Remove the wiki hook line and its comment
			lines = content.split('\n')
			filtered_lines = []
			
			for line in lines:
				# Skip lines containing the wiki hook
				if wiki_hook in line:
					continue
				# Skip comment lines about wiki sync
				if '# Sync wiki docs on migration' in line:
					continue
				filtered_lines.append(line)
			
			content = '\n'.join(filtered_lines)
			
			# Clean up empty after_migrate if it only contained wiki hook
			content = content.replace('after_migrate = [\n]', 'after_migrate = []')
			content = content.replace('after_migrate = [\n\n]', 'after_migrate = []')
			
			# Write back to file
			with open(hooks_path, 'w') as f:
				f.write(content)
			
			frappe.msgprint(f"Removed wiki sync hook from {self.app_name}/hooks.py")
			return True
			
		except Exception as e:
			frappe.log_error(f"Failed to remove wiki sync hook: {str(e)}", "Wiki Hook Setup")
			return False

	def get_app_hooks_path(self):
		"""Get the path to the target app's hooks.py file"""
		try:
			app_path = frappe.get_app_path(self.app_name)
			return os.path.join(app_path, "hooks.py")
		except:
			return None
