import frappe

@frappe.whitelist()
def debug_current_sidebar():
    """Debug current sidebar structure to see parent labels"""
    try:
        # Get the wiki space
        wiki_spaces = frappe.get_all("Wiki Space", filters={"route": "docs"}, limit=1)
        if not wiki_spaces:
            return {"success": False, "error": "No wiki space found with route 'docs'"}
        
        wiki_space = frappe.get_doc("Wiki Space", wiki_spaces[0].name)
        
        sidebar_info = []
        for sidebar_item in wiki_space.wiki_sidebars:
            # Get the actual page details
            page_doc = None
            if sidebar_item.wiki_page:
                try:
                    page_doc = frappe.get_doc("Wiki Page", sidebar_item.wiki_page)
                except:
                    page_doc = None
            
            sidebar_info.append({
                "parent_label": sidebar_item.parent_label,
                "wiki_page_id": sidebar_item.wiki_page,
                "page_title": page_doc.title if page_doc else "Not Found",
                "page_route": page_doc.route if page_doc else "Not Found",
                "hide_on_sidebar": sidebar_item.hide_on_sidebar
            })
        
        return {
            "success": True,
            "wiki_space_name": wiki_space.name,
            "sidebar_items": sidebar_info,
            "total_items": len(sidebar_info)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def debug_specific_page_sidebar(page_route):
    """Debug specific page's sidebar entry"""
    try:
        # Get the page
        pages = frappe.get_all("Wiki Page", filters={"route": page_route}, limit=1)
        if not pages:
            return {"success": False, "error": f"Page with route '{page_route}' not found"}
        
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
        
        return {
            "success": True,
            "page_name": page.name,
            "page_title": page.title,
            "page_route": page.route,
            "sidebar_entry": found_sidebar
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }