import frappe
import os

@frappe.whitelist()
def debug_hooks_path():
    """Debug the hooks path resolution"""
    try:
        settings = frappe.get_doc("Wiki Dev Settings", "WDS-00001")
        
        app_path = frappe.get_app_path(settings.app_name)
        hooks_path = os.path.join(app_path, "hooks.py")
        
        # Check if file exists
        file_exists = os.path.exists(hooks_path)
        
        # Read content if it exists
        content_preview = ""
        if file_exists:
            with open(hooks_path, 'r') as f:
                lines = f.readlines()
                # Get lines around after_migrate
                for i, line in enumerate(lines):
                    if 'after_migrate' in line:
                        start = max(0, i-2)
                        end = min(len(lines), i+8)
                        content_preview = ''.join(lines[start:end])
                        break
        
        return {
            "success": True,
            "app_name": settings.app_name,
            "app_path": app_path,
            "hooks_path": hooks_path,
            "file_exists": file_exists,
            "content_preview": content_preview
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }