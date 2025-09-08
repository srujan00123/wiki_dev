import frappe
import os
import json

@frappe.whitelist()
def test_wiki_page_deletion_sync():
    """Test deleting a wiki page from UI and check if markdown file is removed"""
    try:
        # Create a test wiki page first
        wiki_spaces = frappe.get_all("Wiki Space", filters={"route": "docs"}, limit=1)
        if not wiki_spaces:
            return {"success": False, "error": "No wiki space found with route 'docs'"}
        
        wiki_space_name = wiki_spaces[0].name
        
        # Create test page
        test_page = frappe.new_doc("Wiki Page")
        test_page.title = "Test Deletion Page"
        test_page.route = "docs/test-deletion-page"
        test_page.content = """# Test Deletion Page

This page will be deleted to test sync functionality.
"""
        test_page.wiki_space = wiki_space_name
        test_page.published = 1
        test_page.insert()
        
        # Trigger sync to create markdown file
        test_page.content += "\n\n## Additional content to trigger sync"
        test_page.save()
        
        # Check if markdown file was created
        expected_file_path = "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/miscellaneous/test-deletion-page.md"
        file_exists_before = os.path.exists(expected_file_path)
        
        # Check _config.json before deletion
        config_path = "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/_config.json"
        config_before = {}
        page_in_config_before = False
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_before = json.load(f)
            
            for group in config_before.get("groups", []):
                for page in group.get("pages", []):
                    if page.get("route") == "docs/test-deletion-page":
                        page_in_config_before = True
                        break
        
        # Now delete the wiki page (this should trigger markdown file deletion)
        page_name = test_page.name
        frappe.delete_doc("Wiki Page", page_name)
        
        # Check if markdown file was deleted
        file_exists_after = os.path.exists(expected_file_path)
        
        # Check _config.json after deletion
        config_after = {}
        page_in_config_after = False
        
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_after = json.load(f)
            
            for group in config_after.get("groups", []):
                for page in group.get("pages", []):
                    if page.get("route") == "docs/test-deletion-page":
                        page_in_config_after = True
                        break
        
        return {
            "success": True,
            "test_results": {
                "page_created": page_name,
                "file_exists_before": file_exists_before,
                "file_exists_after": file_exists_after,
                "page_in_config_before": page_in_config_before,
                "page_in_config_after": page_in_config_after,
                "file_path": expected_file_path,
                "deletion_sync_worked": file_exists_before and not file_exists_after and not page_in_config_after
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def test_markdown_file_deletion_sync():
    """Test deleting a markdown file and check if wiki page is removed"""
    try:
        # First create a test page
        result = test_wiki_page_deletion_sync()
        if not result.get("success"):
            return {"success": False, "error": "Failed to setup test"}
        
        # Create a test markdown file manually
        test_file_path = "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/miscellaneous/test-file-deletion.md"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(test_file_path), exist_ok=True)
        
        # Create test markdown file
        with open(test_file_path, 'w') as f:
            f.write("""# Test File Deletion

This markdown file will be deleted to test reverse sync.
""")
        
        # Update _config.json to include this page
        config_path = "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/_config.json"
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Add page to Miscellaneous group
        misc_group = None
        for group in config.get("groups", []):
            if group.get("name") == "Miscellaneous":
                misc_group = group
                break
        
        if not misc_group:
            misc_group = {
                "name": "Miscellaneous",
                "order": 99,
                "pages": []
            }
            config.setdefault("groups", []).append(misc_group)
        
        misc_group.setdefault("pages", []).append({
            "file": "docs/miscellaneous/test-file-deletion.md",
            "title": "Test File Deletion",
            "route": "docs/test-file-deletion",
            "order": 99
        })
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Create corresponding wiki page
        wiki_spaces = frappe.get_all("Wiki Space", filters={"route": "docs"}, limit=1)
        wiki_space_name = wiki_spaces[0].name
        
        test_wiki_page = frappe.new_doc("Wiki Page")
        test_wiki_page.title = "Test File Deletion"
        test_wiki_page.route = "docs/test-file-deletion"
        test_wiki_page.content = """# Test File Deletion

This markdown file will be deleted to test reverse sync.
"""
        test_wiki_page.wiki_space = wiki_space_name
        test_wiki_page.published = 1
        test_wiki_page.insert()
        
        wiki_page_exists_before = frappe.db.exists("Wiki Page", {"route": "docs/test-file-deletion"})
        
        # Now delete the markdown file
        os.remove(test_file_path)
        
        # Run the docs folder sync to detect the deletion
        from wiki_dev.wiki_dev.api.docs_watcher import sync_docs_folder_to_wiki
        sync_result = sync_docs_folder_to_wiki("WDS-00001")
        
        wiki_page_exists_after = frappe.db.exists("Wiki Page", {"route": "docs/test-file-deletion"})
        
        return {
            "success": True,
            "test_results": {
                "file_created": os.path.exists(test_file_path),
                "wiki_page_exists_before": wiki_page_exists_before,
                "wiki_page_exists_after": wiki_page_exists_after,
                "sync_result": sync_result,
                "reverse_deletion_sync_worked": wiki_page_exists_before and not wiki_page_exists_after
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def test_orphaned_pages_detection():
    """Test detecting orphaned wiki pages that don't have markdown files"""
    try:
        from wiki_dev.wiki_dev.api.docs_watcher import check_orphaned_wiki_pages
        
        result = check_orphaned_wiki_pages("WDS-00001")
        
        return {
            "success": True,
            "orphaned_pages_check": result
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def cleanup_deletion_tests():
    """Clean up all test files and pages"""
    try:
        # Delete test wiki pages
        test_routes = [
            "docs/test-deletion-page",
            "docs/test-file-deletion"
        ]
        
        for route in test_routes:
            pages = frappe.get_all("Wiki Page", filters={"route": route})
            for page in pages:
                try:
                    frappe.delete_doc("Wiki Page", page.name)
                except:
                    pass
        
        # Delete test files
        test_files = [
            "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/miscellaneous/test-deletion-page.md",
            "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/miscellaneous/test-file-deletion.md"
        ]
        
        for file_path in test_files:
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Clean up empty directories
        misc_dir = "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/miscellaneous"
        if os.path.exists(misc_dir) and not os.listdir(misc_dir):
            os.rmdir(misc_dir)
        
        # Clean up _config.json
        config_path = "/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/_config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # Remove test pages and empty groups
            for group in config.get("groups", []):
                pages = group.get("pages", [])
                group["pages"] = [p for p in pages if p.get("route") not in test_routes]
            
            config["groups"] = [g for g in config.get("groups", []) if g.get("pages")]
            
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