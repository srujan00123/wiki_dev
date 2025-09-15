import frappe

@frappe.whitelist()
def delete_test_wiki_space():
    """Delete the test wiki space and pages to test migration"""
    try:
        # Delete wiki pages first
        wiki_pages = frappe.get_all('Wiki Page', filters=[['route', 'like', 'docs/%']])
        pages_deleted = 0
        
        for page in wiki_pages:
            doc = frappe.get_doc('Wiki Page', page.name)
            doc.delete()
            pages_deleted += 1
        
        # Then delete wiki spaces
        wiki_spaces = frappe.get_all('Wiki Space', filters={'route': 'docs'})
        spaces_deleted = 0
        
        for space in wiki_spaces:
            doc = frappe.get_doc('Wiki Space', space.name)
            doc.delete()
            spaces_deleted += 1
        
        return {
            "success": True,
            "message": f"Deleted {spaces_deleted} wiki spaces and {pages_deleted} wiki pages with route 'docs'"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist() 
def test_migration_sync():
    """Test the full migration sync process"""
    try:
        # First delete existing wiki space
        delete_result = delete_test_wiki_space()
        
        # Then run migration sync (should create the wiki space)
        from wiki_dev.api.wiki_sync import sync_all_enabled_settings
        sync_result = sync_all_enabled_settings()
        
        return {
            "success": True,
            "delete_result": delete_result,
            "sync_result": sync_result
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }