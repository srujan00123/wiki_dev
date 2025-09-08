import frappe
from wiki_dev.wiki_dev.api.wiki_sync import sync_wiki_page_to_markdown

@frappe.whitelist()
def test_manual_sync_for_new_page():
    """Test manual sync for the new page that didn't sync"""
    try:
        # Get the specific page that was created
        page = frappe.get_doc('Wiki Page', 'un24067jfa')
        
        result = {
            "page_name": page.name,
            "page_title": page.title,
            "page_route": page.route,
            "page_content": page.content[:200] if page.content else "No content",
        }
        
        # Manually call the sync function
        sync_result = sync_wiki_page_to_markdown(page)
        result["sync_result"] = sync_result
        
        return {
            "success": True,
            "result": result
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }