import frappe
from wiki_dev.wiki_dev.api.wiki_sync import sync_wiki_page_to_markdown

@frappe.whitelist()
def test_fix_misplaced_page():
    """Test fixing the Test New Parent page that should be in NewParentTest"""
    try:
        # Get the page
        pages = frappe.get_all("Wiki Page", filters={"route": "docs/test-new-parent"}, limit=1)
        if not pages:
            return {"success": False, "error": "Page not found"}
        
        page = frappe.get_doc("Wiki Page", pages[0].name)
        
        # Manually trigger sync
        result = sync_wiki_page_to_markdown(page)
        
        return {
            "success": True,
            "page_name": page.name,
            "page_title": page.title,
            "page_route": page.route,
            "sync_result": result,
            "message": "Sync completed - check if page moved to correct group"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }