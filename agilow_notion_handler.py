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
    users = fetch_users()
    page_id = existing_task["id"]
    url = f"https://api.notion.com/v1/pages/{page_id}"
    
    # Prepare update data
    data = {
        "properties": {
            "Name": {
                "title": [{"text": {"content": task_dict['task']}}]
            },
            "Status": {
                "status": {"name": task_dict['status']}
            }
        }
    }

    # Update deadline if provided
    if task_dict.get('deadline'):
        data["properties"]["Deadline"] = {
            "date": {"start": task_dict['deadline']}
        }
    
    # Update assignee if provided
    if task_dict.get('assignee'):
        user_id = users.get(task_dict['assignee'])
        if user_id:
            data["properties"]["Assign"] = {
                "people": [{"id": user_id}]
            }
            print(f"✅ Updating assignee to: {task_dict['assignee']}")
        else:
            print(f"⚠️ Could not find user ID for {task_dict['assignee']}")

    try:
        response = requests.patch(url, headers=HEADERS, json=data)
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ Updated task: {task_dict['task']} to {task_dict['status']}")
            return True
        else:
            print(f"❌ Notion API error {response.status_code}: {response.text}")
            print(f"Request data: {data}")  # Debug info
            return False
    except Exception as e:
        print(f"❌ Notion update failed: {str(e)}")
        return False

def fetch_users():
    """Fetch all users from Notion"""
    url = "https://api.notion.com/v1/users"
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        users = {}
        for user in response.json().get("results", []):
            users[user["name"]] = user["id"]
        return users
    else:
        print(f"❌ Error fetching users: {response.text}")
        return {}

def add_to_notion(task_dict):
    """Add or update a task in Notion"""
    users = fetch_users()
    
    # Check if task exists by name only
    existing_tasks = fetch_tasks()
    existing_task = next(
        (t for t in existing_tasks 
         if t["properties"]["Name"]["title"][0]["text"]["content"].lower() == task_dict['task'].lower()),
        None
    )
    
    if existing_task:
        return update_task_in_notion(task_dict, existing_task)
        
    # Add new task
    url = "https://api.notion.com/v1/pages"
    
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": task_dict['task']}}]
            },
            "Status": {
                "status": {"name": task_dict['status']}
            }
        }
    }

    # Only add deadline if it's a valid date string
    if task_dict.get('deadline') and task_dict['deadline'] not in ['Unknown', 'No deadline']:
        data["properties"]["Deadline"] = {
            "date": {"start": task_dict['deadline']}
        }
        
    if task_dict.get('assignee') and task_dict['assignee'] in users:
        data["properties"]["Assign"] = {
            "people": [{"id": users[task_dict['assignee']]}]
        }

    try:
        response = requests.post(url, headers=HEADERS, json=data)
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ Added task: {task_dict['task']}")
            return True
        else:
            print(f"❌ Notion API error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Notion request failed: {str(e)}")
        return False

def delete_from_notion(task_name):
    """Delete (archive) a task from Notion"""
    # Find task by name
    existing_tasks = fetch_tasks()
    task_to_delete = next(
        (t for t in existing_tasks 
         if t["properties"]["Name"]["title"][0]["text"]["content"].lower() == task_name.lower()),
        None
    )
    
    if not task_to_delete:
        print(f"❌ Task not found: {task_name}")
        return False
        
    # Archive the page
    page_id = task_to_delete["id"]
    url = f"https://api.notion.com/v1/pages/{page_id}"  # Using pages endpoint
    
    try:
        data = {
            "archived": True,  # This archives the page
        }
        response = requests.patch(url, headers=HEADERS, json=data)
        
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ Archived task: {task_name}")
            return True
        else:
            print(f"❌ Notion API error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Notion archive failed: {str(e)}")
        return False

def handle_task_operations(task_dict):
    """Route task operations to appropriate handlers"""
    if task_dict.get('operation') == 'delete':
        return delete_from_notion(task_dict['task'])
    elif task_dict.get('operation') == 'rename':
        # Find existing task and update it
        existing_tasks = fetch_tasks()
        existing_task = next(
            (t for t in existing_tasks 
             if t["properties"]["Name"]["title"][0]["text"]["content"].lower() == task_dict['old_name'].lower()),
            None
        )
        if existing_task:
            task_dict['task'] = task_dict['new_name']  # Set the new name
            return update_task_in_notion(task_dict, existing_task)
        return False
    else:
        return add_to_notion(task_dict)

