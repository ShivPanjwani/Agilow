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

def add_to_notion(task_dict):
    """Add a task to Notion"""
    url = "https://api.notion.com/v1/pages"
    
    # Check for duplicate task
    existing_tasks = fetch_tasks()
    task_exists = any(
        t["properties"]["Task Number"]["number"] == task_dict['number'] and
        t["properties"]["Status"]["status"]["name"] == task_dict['status']
        for t in existing_tasks
    )
    
    if task_exists:
        print(f"ℹ️ Task #{task_dict['number']} already exists, skipping...")
        return True
        
    # Format task name with number
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
