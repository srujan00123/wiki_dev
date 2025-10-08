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
	

	def set_default_paths(self):
		"""Set default paths based on app_name if not provided"""
		if self.app_name:
			# Set default wiki_space_name if not provided
			if not self.wiki_space_name:
				self.wiki_space_name = "docs"
			
			# Set default docs_folder_path if not provided
			if not self.docs_folder_path:
				self.docs_folder_path = f"apps/{self.app_name}/docs/{self.wiki_space_name}"
			
			
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
					"sync_on_migrate", "sync_on_wiki_update"]
		)

