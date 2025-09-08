import frappe
import os

@frappe.whitelist()
def test_empty_hooks_scenario():
    """Test hook addition when after_migrate doesn't exist"""
    try:
        # Create a temporary hooks file without after_migrate
        test_hooks_content = '''app_name = "test_app"
app_title = "Test App"

# Some other hooks
doc_events = {
    "User": {
        "validate": ["test_app.api.validate_user"]
    }
}
'''
        
        # Get the path where we would write (using example app path)
        settings = frappe.get_doc("Wiki Dev Settings", "WDS-00001")
        hooks_path = settings.get_app_hooks_path()
        
        # Backup original content
        with open(hooks_path, 'r') as f:
            original_content = f.read()
        
        # Write test content
        with open(hooks_path, 'w') as f:
            f.write(test_hooks_content)
        
        # Test adding hook to empty file
        result = settings.add_wiki_sync_hook()
        
        # Read the result
        with open(hooks_path, 'r') as f:
            new_content = f.read()
        
        # Restore original content
        with open(hooks_path, 'w') as f:
            f.write(original_content)
        
        return {
            "success": True,
            "hook_added": result,
            "original_length": len(original_content),
            "test_content": test_hooks_content,
            "new_content": new_content,
            "message": "Test completed - original content restored"
        }
        
    except Exception as e:
        # Always try to restore original content on error
        try:
            if 'original_content' in locals():
                with open(hooks_path, 'w') as f:
                    f.write(original_content)
        except:
            pass
            
        return {
            "success": False,
            "error": str(e)
        }