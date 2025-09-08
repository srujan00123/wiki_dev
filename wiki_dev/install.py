import frappe
from frappe import _

def before_install():
    """Check if Wiki app is installed before installing wiki_dev"""
    try:
        # Check if wiki app is installed
        if not frappe.db.exists("Module Def", {"app_name": "wiki"}):
            frappe.throw(
                _("Wiki app must be installed before installing wiki_dev. Please run:\n"
                  "bench get-app wiki\n"
                  "bench install-app wiki"),
                title=_("Missing Dependency")
            )
    except Exception:
        # If we can't check (maybe first install), just continue
        pass

def after_install():
    """Post-installation setup"""
    frappe.db.commit()
    print("Wiki Dev installed successfully!")
    print("Create a Wiki Dev Settings record to get started with wiki synchronization.")