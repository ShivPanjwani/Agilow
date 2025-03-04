import requests
import json
from datetime import datetime
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
    
    # Build properties to update
    properties = {
        "Status": {"status": {"name": task_dict.get('status', existing_task['properties']['Status']['status']['name'])}}
    }
    
    # Only include deadline if it's a valid date
    if 'deadline' in task_dict and task_dict['deadline'] not in ['No deadline', None]:
        properties["Deadline"] = {"date": {"start": task_dict['deadline']}}
    
    # Only include assignee if it's valid
    if 'assignee' in task_dict and task_dict['assignee']:
        user_id = users.get(task_dict['assignee'])
        if user_id:
            properties["Assign"] = {"people": [{"id": user_id}]}
            print(f"✅ Updating assignee to: {task_dict['assignee']}")
        else:
            print(f"⚠️ Could not find user ID for {task_dict['assignee']}")

    data = {"properties": properties}

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

def add_comment_to_notion(task_dict):
    """Add a comment to a task in Notion"""
    existing_tasks = fetch_tasks()
    task_to_update = next(
        (t for t in existing_tasks 
         if t["properties"]["Name"]["title"][0]["text"]["content"].lower() == task_dict['task'].lower()),
        None
    )
    
    if not task_to_update:
        print(f"❌ Task not found: {task_dict['task']}")
        return False
        
    page_id = task_to_update["id"]
    url = "https://api.notion.com/v1/comments"
    
    data = {
        "parent": {
            "page_id": page_id
        },
        "rich_text": [
            {
                "type": "text",
                "text": {
                    "content": task_dict['comment']
                }
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=HEADERS, json=data)
        if response.status_code == 200:
            print(f"✅ Added comment to task: {task_dict['task']}")
            return True
        else:
            print(f"❌ Notion API error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Notion comment failed: {str(e)}")
        return False

def move_task_after(task_id, after_id=None):
    """Move a task to appear after another task in the board
    
    Args:
        task_id: ID of the task to move
        after_id: ID of the task that should appear before the moved task.
                  If None, the task will move to the top.
    """
    url = f"https://api.notion.com/v1/pages/{task_id}"
    
    data = {
        "parent": {"database_id": NOTION_DATABASE_ID}
    }
    
    if after_id:
        data["after"] = after_id
    
    try:
        response = requests.patch(url, headers=HEADERS, json=data)
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ Repositioned task successfully")
            return True
        else:
            print(f"❌ Notion API error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Notion reposition failed: {str(e)}")
        return False

def handle_task_operations(task_dict):
    """Handle different task operations"""
    operation = task_dict.get('operation', 'create')
    
    if operation == 'create' or not operation:
        # Create a new task
        task_name = task_dict.get('task')
        status = task_dict.get('status', 'Not started')
        deadline = task_dict.get('deadline')
        assignee = task_dict.get('assignee')
        
        return add_to_notion(task_dict)
    
    elif operation == 'update':
        # Update an existing task
        task_name = task_dict.get('task')
        status = task_dict.get('status')
        deadline = task_dict.get('deadline')
        assignee = task_dict.get('assignee')
        
        # Find the task by name
        existing_tasks = fetch_tasks()
        task_to_update = None
        
        for task in existing_tasks:
            if task["properties"]["Name"]["title"][0]["text"]["content"] == task_name:
                task_to_update = task
                break
        
        if not task_to_update:
            print(f"❌ Task not found: {task_name}")
            return False
        
        # Update the task
        return update_task_in_notion(task_dict, task_to_update)
    
    elif operation == 'delete':
        # Delete a task
        task_name = task_dict.get('task')
        
        # Find the task by name
        existing_tasks = fetch_tasks()
        task_to_delete = None
        
        for task in existing_tasks:
            if task["properties"]["Name"]["title"][0]["text"]["content"] == task_name:
                task_to_delete = task
                break
        
        if not task_to_delete:
            print(f"❌ Task not found: {task_name}")
            return False
        
        # Delete the task
        return delete_from_notion(task_name)
    
    elif operation == 'comment':
        # Add a comment to a task
        task_name = task_dict.get('task')
        comment_text = task_dict.get('comment')
        
        # Find the task by name
        existing_tasks = fetch_tasks()
        task_to_comment = None
        
        for task in existing_tasks:
            if task["properties"]["Name"]["title"][0]["text"]["content"] == task_name:
                task_to_comment = task
                break
        
        if not task_to_comment:
            print(f"❌ Task not found: {task_name}")
            return False
        
        # Add the comment
        return add_comment_to_notion(task_dict)
    
    elif operation == 'rename':
        # Rename a task
        old_name = task_dict.get('old_name')
        new_name = task_dict.get('new_name')
        
        # Find the task with the old name
        existing_tasks = fetch_tasks()
        task_to_rename = None
        
        for task in existing_tasks:
            if task["properties"]["Name"]["title"][0]["text"]["content"] == old_name:
                task_to_rename = task
                break
        
        if not task_to_rename:
            print(f"❌ Task not found: {old_name}")
            return False
        
        # Update the task name
        return update_task_name(task_to_rename["id"], new_name)
    
    elif operation == 'reposition':
        # Currently not fully supported by Notion API
        print(f"⚠️ Task repositioning is not currently supported. The task '{task_dict.get('task')}' will remain in its current position.")
        return True  # Return success to avoid error messages
    
    else:
        print(f"❌ Unknown operation: {operation}")
        return False

def update_task_name(task_id, new_name):
    """Update a task's name in Notion"""
    url = f"https://api.notion.com/v1/pages/{task_id}"
    
    data = {
        "properties": {
            "Name": {
                "title": [
                    {
                        "text": {
                            "content": new_name
                        }
                    }
                ]
            }
        }
    }
    
    try:
        response = requests.patch(url, headers=HEADERS, json=data)
        
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ Renamed task successfully to: {new_name}")
            return True
        else:
            print(f"❌ Notion API error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Notion rename failed: {str(e)}")
        return False