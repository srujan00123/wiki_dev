import frappe

@frappe.whitelist()
def check_wiki_page_exists():
    """Check if the test wiki page still exists"""
    try:
        pages = frappe.get_all('Wiki Page', filters={'route': 'docs/test-deletion-page'})
        return {
            "success": True,
            "pages_found": len(pages),
            "page_details": pages
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def manually_test_deletion_hook():
    """Manually test the deletion hook functionality"""
    try:
        # Find a wiki page to test with
        pages = frappe.get_all('Wiki Page', filters={'route': 'docs/test-deletion-page'})
        if not pages:
            return {"success": False, "message": "No test page found"}
        
        # Get the page document
        page = frappe.get_doc('Wiki Page', pages[0].name)
        
        # Manually call the deletion sync function
        from wiki_dev.wiki_dev.api.wiki_sync import sync_wiki_page_deletion_to_markdown
        sync_wiki_page_deletion_to_markdown(page)
        
        return {
            "success": True,
            "message": "Manually called deletion sync function",
            "page_route": page.route,
            "page_title": page.title
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }