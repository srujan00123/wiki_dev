import frappe

@frappe.whitelist()
def create_test_page_with_new_parent():
    """Test creating a page with a new parent label"""
    try:
        # Get the existing wiki space
        wiki_spaces = frappe.get_all("Wiki Space", filters={"route": "docs"}, limit=1)
        if not wiki_spaces:
            return {"success": False, "error": "No wiki space found with route 'docs'"}
        
        wiki_space = frappe.get_doc("Wiki Space", wiki_spaces[0].name)
        
        # Create a new wiki page
        wiki_page = frappe.new_doc("Wiki Page")
        wiki_page.title = "Test New Parent"
        wiki_page.route = "docs/test-new-parent"
        wiki_page.content = "This page tests if new parent labels work correctly."
        wiki_page.published = 1
        wiki_page.insert()
        
        # Add to sidebar under a NEW parent label
        wiki_space.append("wiki_sidebars", {
            "parent_label": "NewParentTest", 
            "wiki_page": wiki_page.name,
            "hide_on_sidebar": 0
        })
        wiki_space.save()  # This should trigger the Wiki Space on_update hook
        
        return {
            "success": True,
            "page_name": wiki_page.name,
            "page_title": wiki_page.title,
            "page_route": wiki_page.route,
            "expected_folder": "newparenttest",
            "expected_file": "docs/newparenttest/test-new-parent.md"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }