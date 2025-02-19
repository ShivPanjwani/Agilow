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
    
    task_name = task_dict['task']
    status = task_dict['status']
    deadline_date = task_dict['deadline']
    number = task_dict['number']  # GPT provides the number
    
    # Format task name with number
    formatted_name = format_task_title(number, task_name)
    
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": formatted_name}}]
            },
            "Status": {
                "status": {"name": status}
            },
            "Task Number": {
                "number": number
            }
        }
    }

    if deadline_date:
        data["properties"]["Deadline"] = {
            "date": {"start": deadline_date}
        }

    try:
        response = requests.post(url, headers=HEADERS, json=data)
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ Task added to Notion")
            return True
        else:
            print(f"❌ Notion API error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Notion request failed: {str(e)}")
        return False
