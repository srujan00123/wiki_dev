import frappe
import os
import json

@frappe.whitelist()
def test_new_page_creation():
    """Test creating a new wiki page in the UI to see if it syncs to markdown"""
    try:
        # Get the existing wiki space
        wiki_spaces = frappe.get_all("Wiki Space", filters={"route": "docs"}, limit=1)
        if not wiki_spaces:
            return {"success": False, "error": "No wiki space found with route 'docs'"}
        
        wiki_space_name = wiki_spaces[0].name
        wiki_space = frappe.get_doc("Wiki Space", wiki_space_name)
        
        # Create a test wiki page
        test_page = frappe.new_doc("Wiki Page")
        test_page.title = "Test New Page"
        test_page.route = "docs/test-new-page"
        test_page.content = """# Test New Page

This is a test page created through the UI to verify new page sync functionality.

## Features

- Should create markdown file
- Should update _config.json
- Should be placed in appropriate folder based on parent label
"""
        test_page.wiki_space = wiki_space_name
        test_page.published = 1
        test_page.insert()
        
        # Add to wiki space sidebar with a parent label
        wiki_space.append("wiki_sidebars", {
            "parent_label": "Testing",
            "wiki_page": test_page.name,
            "hide_on_sidebar": 0
        })
        wiki_space.save()
        
        # Trigger the sync by updating the page (simulates UI edit)
        test_page.content += "\n\n## Updated Content\n\nThis content was added to trigger sync."
        test_page.save()
        
        return {
            "success": True,
            "message": f"Created test wiki page: {test_page.name}",
            "page_name": test_page.name,
            "route": test_page.route,
            "title": test_page.title
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def check_new_page_files():
    """Check if the new page created files and updated config"""
    try:
        # Check if markdown file was created
        expected_file_path = "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/testing/test-new-page.md"
        file_exists = os.path.exists(expected_file_path)
        
        file_content = ""
        if file_exists:
            with open(expected_file_path, 'r') as f:
                file_content = f.read()[:200] + "..." if len(f.read()) > 200 else f.read()
        
        # Check if _config.json was updated
        config_path = "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/_config.json"
        config_updated = False
        config_content = {}
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_content = json.load(f)
            
            # Check if "Testing" group was added
            for group in config_content.get("groups", []):
                if group.get("name") == "Testing":
                    config_updated = True
                    break
        
        return {
            "success": True,
            "file_exists": file_exists,
            "file_path": expected_file_path,
            "file_content_preview": file_content,
            "config_updated": config_updated,
            "config_groups": [g.get("name") for g in config_content.get("groups", [])]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def cleanup_test_page():
    """Clean up the test page and files"""
    try:
        # Delete wiki page
        test_pages = frappe.get_all("Wiki Page", filters={"route": "docs/test-new-page"})
        for page in test_pages:
            frappe.delete_doc("Wiki Page", page.name)
        
        # Remove test file
        test_file_path = "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/testing/test-new-page.md"
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
        
        # Remove empty testing directory
        test_dir = os.path.dirname(test_file_path)
        if os.path.exists(test_dir) and not os.listdir(test_dir):
            os.rmdir(test_dir)
        
        # Clean up _config.json (remove Testing group)
        config_path = "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/_config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Remove Testing group
            config["groups"] = [g for g in config.get("groups", []) if g.get("name") != "Testing"]
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        
        return {
            "success": True,
            "message": "Cleanup completed"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }