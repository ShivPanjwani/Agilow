import requests
from agilow_config import NOTION_API_KEY, NOTION_DATABASE_ID

# Constants
NOTION_API_VERSION = "2022-06-28"
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_API_VERSION
}

def fetch_tasks():
    """Fetch all tasks from Notion"""
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    response = requests.post(url, headers=HEADERS)
    
    if response.status_code == 200:
        return response.json().get("results", [])
    else:
        print(f"❌ Error fetching tasks: {response.text}")
        return []

def format_task_title(number, task_name):
    """Format task title with number prefix"""
    return f"{number}. {task_name}"

def update_task_in_notion(task_dict, existing_task):
    """Update an existing task in Notion"""
    page_id = existing_task["id"]
    url = f"https://api.notion.com/v1/pages/{page_id}"
    
    # Prepare update data
    data = {
        "properties": {
            "Name": {
                "title": [{"text": {"content": format_task_title(task_dict['number'], task_dict['task'])}}]
            },
            "Status": {
                "status": {"name": task_dict['status']}
            },
            "Task Number": {
                "number": task_dict['number']
            },
            "Deadline": {
                "date": {"start": task_dict['deadline']} if task_dict['deadline'] else None
            }
        }
    }

    try:
        response = requests.patch(url, headers=HEADERS, json=data)
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ Updated deadline for task #{task_dict['number']}")
            return True
        else:
            print(f"❌ Notion API error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Notion update failed: {str(e)}")
        return False

def add_to_notion(task_dict):
    """Add or update a task in Notion"""
    # Check if task exists
    existing_tasks = fetch_tasks()
    existing_task = next(
        (t for t in existing_tasks 
         if t["properties"]["Task Number"]["number"] == task_dict['number'] and
            t["properties"]["Status"]["status"]["name"] == task_dict['status']),
        None
    )
    
    if existing_task:
        return update_task_in_notion(task_dict, existing_task)
        
    # Add new task
    url = "https://api.notion.com/v1/pages"
    formatted_name = format_task_title(task_dict['number'], task_dict['task'])
    
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": formatted_name}}]
            },
            "Status": {
                "status": {"name": task_dict['status']}
            },
            "Task Number": {
                "number": task_dict['number']
            }
        }
    }

    if task_dict['deadline']:
        data["properties"]["Deadline"] = {
            "date": {"start": task_dict['deadline']}
        }

    try:
        response = requests.post(url, headers=HEADERS, json=data)
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ Added task #{task_dict['number']}: {task_dict['task']}")
            return True
        else:
            print(f"❌ Notion API error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Notion request failed: {str(e)}")
        return False
