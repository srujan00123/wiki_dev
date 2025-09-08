import frappe
import os

@frappe.whitelist()
def check_recent_wiki_pages():
    """Check recent wiki pages to see what was created"""
    try:
        pages = frappe.get_all('Wiki Page', 
            filters=[['route', 'like', 'docs/%']], 
            fields=['name', 'title', 'route', 'creation'], 
            order_by='creation desc', 
            limit=10
        )
        
        result = {
            "success": True,
            "total_pages": len(pages),
            "recent_pages": []
        }
        
        for page in pages:
            # Check if there's a corresponding markdown file
            page_info = {
                "name": page.name,
                "title": page.title,
                "route": page.route,
                "creation": str(page.creation),
                "has_markdown_file": False,
                "markdown_path": None
            }
            
            # Try to find corresponding markdown file
            if page.route.startswith("docs/"):
                page_name = page.route.replace("docs/", "")
                
                # Common paths to check
                possible_paths = [
                    f"/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/basics/{page_name}.md",
                    f"/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/advanced/{page_name}.md",
                    f"/home/frappe/frappe_docker/frappe-bench/apps/emr_plus/emr_plus/docs/docs/miscellaneous/{page_name}.md",
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        page_info["has_markdown_file"] = True
                        page_info["markdown_path"] = path
                        break
            
            result["recent_pages"].append(page_info)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def check_wiki_space_sidebar():
    """Check the wiki space sidebar structure"""
    try:
        wiki_spaces = frappe.get_all("Wiki Space", filters={"route": "docs"}, limit=1)
        if not wiki_spaces:
            return {"success": False, "error": "No wiki space found with route 'docs'"}
        
        wiki_space = frappe.get_doc("Wiki Space", wiki_spaces[0].name)
        
        sidebar_info = []
        for sidebar_item in wiki_space.wiki_sidebars:
            page_doc = frappe.get_doc("Wiki Page", sidebar_item.wiki_page) if sidebar_item.wiki_page else None
            
            sidebar_info.append({
                "parent_label": sidebar_item.parent_label,
                "wiki_page": sidebar_item.wiki_page,
                "page_title": page_doc.title if page_doc else "Unknown",
                "page_route": page_doc.route if page_doc else "Unknown",
                "hide_on_sidebar": sidebar_item.hide_on_sidebar
            })
        
        return {
            "success": True,
            "wiki_space_name": wiki_space.name,
            "sidebar_items": sidebar_info,
            "total_sidebar_items": len(sidebar_info)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }