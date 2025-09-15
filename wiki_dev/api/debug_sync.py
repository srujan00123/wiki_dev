import frappe


@frappe.whitelist()
def test_sync():
	"""Test sync functionality"""
	try:
		# Check if settings exist
		settings_count = frappe.db.count("Wiki Dev Settings", {"enabled": 1})
		print(f"Found {settings_count} enabled settings")
		
		if settings_count == 0:
			return {"success": False, "message": "No enabled Wiki Dev Settings found"}
		
		# Get the settings
		settings_list = frappe.get_all("Wiki Dev Settings", 
			filters={"enabled": 1, "sync_on_migrate": 1},
			fields=["name", "app_name", "docs_folder_path"]
		)
		
		print(f"Settings to sync: {settings_list}")
		
		results = []
		for setting_data in settings_list:
			settings = frappe.get_doc("Wiki Dev Settings", setting_data.name)
			docs_path = settings.get_full_docs_path()
			
			print(f"Checking path: {docs_path}")
			
			import os
			if not os.path.exists(docs_path):
				results.append({
					"settings": setting_data.name,
					"error": f"Docs path does not exist: {docs_path}"
				})
				continue
			
			# Check for _config.json
			config_path = os.path.join(docs_path, settings.wiki_space_name, "_config.json")
			print(f"Config path: {config_path}")
			
			if not os.path.exists(config_path):
				results.append({
					"settings": setting_data.name,
					"error": f"Config file not found: {config_path}"
				})
				continue
			
			# Try to call the actual sync function
			from wiki_dev.api.wiki_sync import update_wiki_space_from_folder
			result = update_wiki_space_from_folder(setting_data.name)
			results.append({
				"settings": setting_data.name,
				"result": result
			})
		
		return {
			"success": True,
			"message": f"Tested {len(results)} settings",
			"results": results
		}
		
	except Exception as e:
		import traceback
		return {
			"success": False,
			"error": str(e),
			"traceback": traceback.format_exc()
		}