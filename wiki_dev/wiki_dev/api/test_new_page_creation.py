import frappe

@frappe.whitelist()
def create_test_wiki_page():
    """Create a test wiki page to verify sync functionality"""
    try:
        # Get the existing wiki space
        wiki_spaces = frappe.get_all("Wiki Space", filters={"route": "docs"}, limit=1)
        if not wiki_spaces:
            return {"success": False, "error": "No wiki space found with route 'docs'"}
        
        wiki_space = frappe.get_doc("Wiki Space", wiki_spaces[0].name)
        
        # Create a new wiki page
        wiki_page = frappe.new_doc("Wiki Page")
        wiki_page.title = "New Test Page"
        wiki_page.route = "docs/new-test-page"
        wiki_page.content = "This is a test page created to verify sync functionality."
        wiki_page.published = 1
        wiki_page.insert()
        
        # Add to sidebar under "Basics"
        wiki_space.append("wiki_sidebars", {
            "parent_label": "Basics",
            "wiki_page": wiki_page.name,
            "hide_on_sidebar": 0
        })
        wiki_space.save()
        
        return {
            "success": True,
            "page_name": wiki_page.name,
            "page_title": wiki_page.title,
            "page_route": wiki_page.route
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }