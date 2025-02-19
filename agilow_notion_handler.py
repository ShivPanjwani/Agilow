import requests
from datetime import datetime
from dateutil.parser import parse, ParserError
from agilow_config import NOTION_API_KEY, NOTION_DATABASE_ID

def parse_deadline_and_simplify_task(task_name):
    """Helper function to parse deadline from task"""
    try:
        dt, leftover_tokens = parse(task_name, fuzzy=True, fuzzy_with_tokens=True)
        leftover_text = "".join(leftover_tokens).strip()
        leftover_text = leftover_text.strip(",.:- ")
        final_words = leftover_text.split()
        if final_words and final_words[-1].lower() in ["by", "on", "before", "due"]:
            final_words.pop()
        leftover_text = " ".join(final_words).strip()
        return leftover_text, dt.date().isoformat()
    except (ParserError, ValueError):
        return task_name, None

def extract_status_if_any(task_name):
    """Helper function to extract status from task"""
    status_synonyms = {
        "Not started": ["not started", "haven't started", "no progress", "unbegun", "pending start", "to complete"],
        "In Progress": ["in progress", "ongoing", "working on", "in dev", "developing", "wip", 
                       "testing", "reviewing", "under review", "in development"],
        "Done": ["done", "completed", "finished", "wrapped up"]
    }

    lowered = task_name.lower()
    for status_name, synonyms in status_synonyms.items():
        for s in synonyms:
            if s in lowered:
                return status_name
    return None

def get_tasks_count_by_status(status):
    """Get count of existing tasks for a given status"""
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    
    # Query for tasks with the given status
    data = {
        "filter": {
            "property": "Status",
            "status": {
                "equals": status
            }
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            results = response.json().get("results", [])
            return len(results)
        return 0
    except Exception as e:
        print(f"Error counting tasks: {str(e)}")
        return 0

def format_task_name(task_name, status):
    """Format task name with numbering based on status column"""
    # Remove any existing numbering if present
    if '. ' in task_name:
        task_name = task_name.split('. ', 1)[1]
    
    # Get current count of tasks in this status
    current_count = get_tasks_count_by_status(status)
    
    # For "Not started", we want to count down instead of up
    if status == "Not started":
        new_number = 1  # Always start with 1 for new tasks
        # Existing tasks will need to be renumbered
    else:
        # For other statuses, keep counting up
        new_number = current_count + 1
        
    return f"{new_number}. {task_name}"

def add_to_notion(task_name):
    """
    Adds a task to Notion
    Returns: Boolean indicating success
    """
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    simplified_name, deadline_date = parse_deadline_and_simplify_task(task_name)
    status = extract_status_if_any(simplified_name) or "Not started"  # Default to Not started if no status found
    
    # Format the task name with numbering
    formatted_name = format_task_name(simplified_name, status)

    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": formatted_name}}]
            },
            "Status": {
                "status": {"name": status}
            }
        }
    }

    if deadline_date:
        data["properties"]["Deadline"] = {
            "date": {
                "start": deadline_date
            }
        }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code >= 200 and response.status_code < 300:
            result = response.json()
            page_url = result.get("url", "No page URL returned.")
            print(f"✅ Task added to Notion: {page_url}")
            return True
        else:
            print(f"❌ Notion API error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Notion request failed: {str(e)}")
        return False