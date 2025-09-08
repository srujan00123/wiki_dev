import frappe
import os
import json

@frappe.whitelist()
def manual_cleanup_test_files():
    """Manually clean up test files since the hook didn't work"""
    try:
        # Remove test markdown file
        test_file = "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/miscellaneous/test-deletion-page.md"
        file_removed = False
        if os.path.exists(test_file):
            os.remove(test_file)
            file_removed = True
        
        # Check if directory is empty and remove it
        misc_dir = os.path.dirname(test_file)
        dir_removed = False
        if os.path.exists(misc_dir) and not os.listdir(misc_dir):
            os.rmdir(misc_dir)
            dir_removed = True
        
        # Clean up _config.json
        config_path = "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/_config.json"
        config_updated = False
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Remove test page from config
            for group in config.get("groups", []):
                pages = group.get("pages", [])
                original_count = len(pages)
                group["pages"] = [p for p in pages if p.get("route") != "docs/test-deletion-page"]
                if len(group["pages"]) != original_count:
                    config_updated = True
            
            # Remove empty groups
            original_groups = len(config.get("groups", []))
            config["groups"] = [g for g in config.get("groups", []) if g.get("pages")]
            if len(config["groups"]) != original_groups:
                config_updated = True
            
            if config_updated:
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
        
        return {
            "success": True,
            "file_removed": file_removed,
            "dir_removed": dir_removed,
            "config_updated": config_updated,
            "message": "Manual cleanup completed"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }