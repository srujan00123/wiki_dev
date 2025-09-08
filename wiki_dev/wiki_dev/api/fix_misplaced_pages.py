import frappe
import json
import os
import shutil

@frappe.whitelist()
def fix_test_ui_page():
    """Fix the test-ui page that was placed in wrong folder"""
    try:
        # Get Wiki Dev Settings
        settings_list = frappe.get_all("Wiki Dev Settings", 
            filters={"enabled": 1, "app_name": "emr_plus"}, 
            limit=1
        )
        if not settings_list:
            return {"success": False, "error": "No enabled Wiki Dev Settings for emr_plus"}
        
        settings = frappe.get_doc("Wiki Dev Settings", settings_list[0].name)
        docs_path = settings.get_full_docs_path()
        config_path = os.path.join(docs_path, "docs", "_config.json")
        
        # Read current config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Current wrong paths
        old_file_path = "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/miscellaneous/test-ui.md"
        
        # New correct paths
        new_folder_path = "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/sidebarparentui"
        new_file_path = "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/sidebarparentui/test-ui.md"
        
        # Create new folder
        os.makedirs(new_folder_path, exist_ok=True)
        
        # Move file
        if os.path.exists(old_file_path):
            shutil.move(old_file_path, new_file_path)
            file_moved = True
        else:
            file_moved = False
        
        # Update config.json
        # Remove from Miscellaneous
        for group in config.get("groups", []):
            if group.get("name") == "Miscellaneous":
                group["pages"] = [p for p in group.get("pages", []) if p.get("route") != "docs/test-ui"]
                break
        
        # Add to SidebarParentUI group (create if doesn't exist)
        target_group = None
        for group in config.get("groups", []):
            if group.get("name") == "SidebarParentUI":
                target_group = group
                break
        
        if not target_group:
            target_group = {
                "name": "SidebarParentUI",
                "order": len(config.get("groups", [])) + 1,
                "pages": []
            }
            config["groups"].append(target_group)
        
        # Add page to correct group
        page_config = {
            "file": "docs/sidebarparentui/test-ui.md",
            "title": "test ui",
            "route": "docs/test-ui",
            "order": len(target_group.get("pages", [])) + 1
        }
        
        # Check if page already exists in this group
        existing_routes = [p.get("route") for p in target_group.get("pages", [])]
        if "docs/test-ui" not in existing_routes:
            target_group["pages"].append(page_config)
        
        # Clean up empty Miscellaneous group
        config["groups"] = [g for g in config.get("groups", []) if g.get("pages")]
        
        # Write updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return {
            "success": True,
            "file_moved": file_moved,
            "old_path": old_file_path,
            "new_path": new_file_path,
            "config_updated": True
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }