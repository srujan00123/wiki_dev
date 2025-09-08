import frappe

@frappe.whitelist()
def debug_test_ui_page():
    """Debug the test-ui page specifically"""
    try:
        # Get the page
        pages = frappe.get_all("Wiki Page", filters={"route": "docs/test-ui"}, limit=1)
        if not pages:
            return {"success": False, "error": "Page with route 'docs/test-ui' not found"}
        
        page = frappe.get_doc("Wiki Page", pages[0].name)
        
        # Get the wiki space
        wiki_spaces = frappe.get_all("Wiki Space", filters={"route": "docs"}, limit=1)
        if not wiki_spaces:
            return {"success": False, "error": "No wiki space found with route 'docs'"}
        
        wiki_space = frappe.get_doc("Wiki Space", wiki_spaces[0].name)
        
        # Find this page in the sidebar
        found_sidebar = None
        for sidebar_item in wiki_space.wiki_sidebars:
            if sidebar_item.wiki_page == page.name:
                found_sidebar = {
                    "parent_label": sidebar_item.parent_label,
                    "wiki_page_id": sidebar_item.wiki_page,
                    "hide_on_sidebar": sidebar_item.hide_on_sidebar
                }
                break
        
        # Also test the sync logic manually
        parent_label = found_sidebar["parent_label"] if found_sidebar else None
        folder_name = parent_label.lower().replace(" ", "-").replace("_", "-") if parent_label else "unknown"
        expected_file_path = f"docs/{folder_name}/test-ui.md"
        
        return {
            "success": True,
            "page_name": page.name,
            "page_title": page.title,
            "page_route": page.route,
            "sidebar_entry": found_sidebar,
            "expected_folder_name": folder_name,
            "expected_file_path": expected_file_path
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }