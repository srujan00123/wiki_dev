import frappe

@frappe.whitelist()
def test_auto_hook_addition():
    """Test the automatic hook addition functionality"""
    try:
        # Get the existing Wiki Dev Settings record
        settings = frappe.get_doc("Wiki Dev Settings", "WDS-00001")
        
        # Test adding the hook
        result = settings.add_wiki_sync_hook()
        
        return {
            "success": True,
            "hook_added": result,
            "app_name": settings.app_name,
            "message": f"Hook addition test completed for app: {settings.app_name}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def test_hook_removal():
    """Test the hook removal functionality"""
    try:
        # Get the existing Wiki Dev Settings record
        settings = frappe.get_doc("Wiki Dev Settings", "WDS-00001")
        
        # Test removing the hook
        result = settings.remove_wiki_sync_hook()
        
        return {
            "success": True,
            "hook_removed": result,
            "app_name": settings.app_name,
            "message": f"Hook removal test completed for app: {settings.app_name}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }