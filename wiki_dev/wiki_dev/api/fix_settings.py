import frappe

@frappe.whitelist()
def fix_wiki_dev_settings():
    """Fix the docs_folder_path in Wiki Dev Settings"""
    try:
        doc = frappe.get_doc('Wiki Dev Settings', 'WDS-00001')
        old_path = doc.docs_folder_path
        
        doc.docs_folder_path = 'apps/emr_plus/emr_plus/docs'
        doc.save()
        
        return {
            "success": True,
            "message": f"Updated docs_folder_path from '{old_path}' to '{doc.docs_folder_path}'"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }