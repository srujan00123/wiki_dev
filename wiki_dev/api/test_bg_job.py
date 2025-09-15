import frappe
from frappe.utils import now, random_string

@frappe.whitelist()
def test_background_job():
    """Test if background jobs are working for wiki page placement"""
    results = []
    
    results.append("Testing background job functionality...")
    
    try:
        # Create a new Wiki Page to test background job
        wiki_page = frappe.new_doc('Wiki Page')
        wiki_page.title = 'Test Background Job Page'
        wiki_page.route = 'docs/test-bg-job-' + str(random_string(5))
        wiki_page.content = '# Test Background Job\n\nThis page tests the background job functionality.'
        wiki_page.wiki_space = 'docs'
        wiki_page.published = 1

        results.append(f'Creating Wiki Page with title: {wiki_page.title}')
        results.append(f'Route: {wiki_page.route}')
        
        wiki_page.save()
        frappe.db.commit()
        
        results.append(f'✓ Created Wiki Page: {wiki_page.name}')
        
        # Check if the background job function exists and can be called
        try:
            from wiki_dev.api.wiki_sync import fix_page_placement_if_needed
            results.append("✓ Background job function is importable")
            
            # Test the function directly
            result = fix_page_placement_if_needed(wiki_page.name, wiki_page.route)
            results.append(f"✓ Background job function executed: {result}")
            
        except Exception as e:
            results.append(f"✗ Error with background job function: {e}")
        
        # Check scheduler function
        try:
            from wiki_dev.api.wiki_sync import check_and_fix_misplaced_pages
            results.append("✓ Scheduler function is importable")
            
            result = check_and_fix_misplaced_pages()
            results.append(f"✓ Scheduler function executed: {result}")
            
        except Exception as e:
            results.append(f"✗ Error with scheduler function: {e}")
            
        # Check if page was properly placed
        wiki_page.reload()
        results.append(f"Final wiki page route: {wiki_page.route}")
        results.append(f"Final wiki page parent: {getattr(wiki_page, 'parent_label', 'None')}")
        
    except Exception as e:
        results.append(f"✗ Error creating wiki page: {e}")
        frappe.log_error(f"Test background job error: {e}")
    
    return "\n".join(results)

@frappe.whitelist()
def check_queue_status():
    """Check background job queue status"""
    results = []
    
    try:
        from frappe.utils.background_jobs import get_jobs
        
        # Check current background job status
        jobs = get_jobs(site=frappe.local.site)
        results.append(f'Current background jobs in queue: {len(jobs)}')

        if jobs:
            results.append('Recent jobs:')
            for job in jobs[-10:]:
                results.append(f'  - Job Name: {job.get("job_name", "Unknown")}')
                results.append(f'    Status: {job.get("status", "Unknown")}')
                results.append(f'    Queue: {job.get("queue", "Unknown")}')
                results.append('    ---')
        else:
            results.append('No jobs currently in queue')

        # Check if workers are running
        from frappe.utils.background_jobs import get_queues
        queues = get_queues()
        results.append(f'Available queues: {list(queues.keys())}')
        
    except Exception as e:
        results.append(f"Error checking queue: {e}")
        frappe.log_error(f"Queue check error: {e}")
    
    return "\n".join(results)

@frappe.whitelist()
def test_enqueue():
    """Test enqueueing a background job"""
    results = []
    
    try:
        # Test enqueue directly
        frappe.enqueue(
            'wiki_dev.api.test_bg_job.test_bg_job_task',
            queue='short',
            timeout=60,
            enqueue_after_commit=True,
            test_param='test_value'
        )
        
        results.append("✓ Successfully enqueued test background job")
        
        frappe.db.commit()
        results.append("✓ Committed transaction")
        
    except Exception as e:
        results.append(f"✗ Error enqueuing job: {e}")
        frappe.log_error(f"Enqueue test error: {e}")
    
    return "\n".join(results)

def test_bg_job_task(test_param):
    """Background job task for testing"""
    frappe.log_error(f"Background job executed with param: {test_param}", "Test Background Job")
    return f"Background job completed with {test_param}"

@frappe.whitelist()
def test_misplaced_page_fix():
    """Test fixing misplaced pages functionality"""
    results = []
    
    try:
        # Find the wiki space
        wiki_space = frappe.get_doc("Wiki Space", "1e6tabukg9")
        results.append(f"Found wiki space: {wiki_space.name}")
        
        # Check current sidebar structure
        results.append(f"Current sidebar items: {len(wiki_space.wiki_sidebars)}")
        
        for item in wiki_space.wiki_sidebars:
            # Access fields that exist on the wiki sidebar item
            title = getattr(item, 'title', getattr(item, 'item', 'Unknown'))
            item_type = getattr(item, 'type', 'Unknown')
            parent = getattr(item, 'parent_label', getattr(item, 'parent', 'None'))
            route = getattr(item, 'route', 'No route')
            results.append(f"  - {title} (type: {item_type}, parent: {parent}, route: {route})")
        
        # Find a test page that might be misplaced
        test_page_route = "docs/test-bg-job-S3Ds9"
        if frappe.db.exists("Wiki Page", {"route": test_page_route}):
            wiki_page = frappe.get_doc("Wiki Page", {"route": test_page_route})
            results.append(f"Found test page: {wiki_page.name} with route: {wiki_page.route}")
            
            # Test the fix function directly - this is the main functionality
            results.append(f"Testing fix_page_placement_if_needed...")
            
            from wiki_dev.api.wiki_sync import fix_page_placement_if_needed
            fix_result = fix_page_placement_if_needed(wiki_page.name, wiki_page.route)
            results.append(f"Fix result: {fix_result}")
            
            # Check the _config.json to see if the page was moved
            results.append("Checking _config.json after fix...")
            from wiki_dev.api.wiki_sync import sync_all_enabled_settings
            sync_result = sync_all_enabled_settings()
            results.append(f"Sync result: {sync_result}")
        else:
            results.append("Test page not found")
            
        # Also test the scheduled task function
        results.append("Testing scheduled task function...")
        from wiki_dev.api.wiki_sync import check_and_fix_misplaced_pages
        scheduled_result = check_and_fix_misplaced_pages()
        results.append(f"Scheduled task result: {scheduled_result}")
        
    except Exception as e:
        results.append(f"✗ Error testing misplaced page fix: {e}")
        frappe.log_error(f"Misplaced page fix test error: {e}")
    
    return "\n".join(results)

@frappe.whitelist()
def list_wiki_spaces():
    """List all available wiki spaces"""
    results = []
    
    try:
        spaces = frappe.get_all('Wiki Space', fields=['name', 'route'])
        results.append('Available Wiki Spaces:')
        
        if spaces:
            for space in spaces:
                results.append(f'  - Name: {space.name}, Route: {space.route}')
        else:
            results.append('  No wiki spaces found')
            
        # Also check wiki pages
        pages = frappe.get_all('Wiki Page', fields=['name', 'route', 'title', 'wiki_space'], limit=10)
        results.append(f'\nSample Wiki Pages ({len(pages)} found):')
        
        for page in pages:
            results.append(f'  - Page: {page.title} (Route: {page.route}, Space: {page.wiki_space})')
            
    except Exception as e:
        results.append(f"Error listing wiki spaces: {e}")
        frappe.log_error(f"List wiki spaces error: {e}")
    
    return "\n".join(results)