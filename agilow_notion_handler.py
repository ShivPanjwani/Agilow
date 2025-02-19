import requests
from agilow_config import NOTION_API_KEY, NOTION_DATABASE_ID
from dateutil import parser
from dateutil.parser import ParserError

# Constants
NOTION_API_VERSION = "2022-06-28"
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_API_VERSION
}

def fetch_tasks():
    """ Fetch all tasks from Notion """
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    response = requests.post(url, headers=HEADERS)
    
    if response.status_code == 200:
        return response.json().get("results", [])
    else:
        print(f"❌ Error fetching tasks: {response.text}")
        return []

def parse_deadline_and_simplify_task(task_name):
    """Helper function to parse deadline from task"""
    try:
        dt, leftover_tokens = parser.parse(task_name, fuzzy=True, fuzzy_with_tokens=True)
        leftover_text = "".join(leftover_tokens).strip()
        leftover_text = leftover_text.strip(",.:- ")
        final_words = leftover_text.split()
        if final_words and final_words[-1].lower() in ["by", "on", "before", "due"]:
            final_words.pop()
        leftover_text = " ".join(final_words).strip()
        return leftover_text, dt.date().isoformat()
    except (ParserError, ValueError):
        return task_name, None

def group_tasks_by_status(tasks):
    """ Group tasks by status """
    grouped_tasks = {"Not started": [], "In Progress": [], "Done": []}

    for task in tasks:
        status = task["properties"]["Status"]["status"]["name"]
        task_id = task["id"]
        task_name = task["properties"]["Name"]["title"][0]["text"]["content"]
        task_number = task["properties"].get("Task Number", {}).get("number", None)
        created_time = task["created_time"]  # Add this to help with ordering
        
        grouped_tasks[status].append({
            "id": task_id,
            "name": task_name,
            "task_number": task_number,
            "created_time": created_time
        })

    # Sort tasks by creation time (newest first)
    for status in grouped_tasks:
        grouped_tasks[status].sort(key=lambda x: x["created_time"], reverse=True)

    return grouped_tasks

def renumber_tasks(grouped_tasks):
    """ Renumber tasks in each column """
    updates = []
    for status, tasks in grouped_tasks.items():
        sorted_tasks = sorted(tasks, key=lambda x: x["task_number"] or 0)  # Keep order
        for index, task in enumerate(sorted_tasks, start=1):
            if task["task_number"] != index:  # Only update if needed
                updates.append({"id": task["id"], "task_number": index})
    return updates

def format_task_title(task_number, task_name):
    """Format task title with number prefix"""
    return f"{task_number}. {task_name}"

def update_task_title_and_number(task_id, new_number, task_name):
    """Update both task number property and title"""
    url = f"https://api.notion.com/v1/pages/{task_id}"
    data = {
        "properties": {
            "Name": {
                "title": [{"text": {"content": format_task_title(new_number, task_name)}}]
            },
            "Task Number": {
                "number": new_number
            }
        }
    }
    response = requests.patch(url, headers=HEADERS, json=data)
    return response.status_code >= 200 and response.status_code < 300

def update_tasks(updates):
    """ Push renumbering updates to Notion """
    for update in updates:
        task_id = update["id"]
        new_number = update["task_number"]
        task_name = update["name"]
        
        if update_task_title_and_number(task_id, new_number, task_name):
            print(f"✅ Updated Task {task_id} to {new_number}")
        else:
            print(f"❌ Failed to update {task_id}")

def auto_number_tasks():
    """ Full automation function """
    tasks = fetch_tasks()
    grouped_tasks = group_tasks_by_status(tasks)
    updates = renumber_tasks(grouped_tasks)
    
    if updates:
        update_tasks(updates)
        print("✅ Task renumbering completed!")
    else:
        print("✅ No changes needed!")

def add_to_notion(task_name):
    """
    Adds a task to Notion with automatic numbering
    Returns: Boolean indicating success
    """
    url = "https://api.notion.com/v1/pages"
    
    # Parse deadline and simplify task name
    simplified_name, deadline_date = parse_deadline_and_simplify_task(task_name)
    
    # Get current tasks to determine numbering
    tasks = fetch_tasks()
    grouped_tasks = group_tasks_by_status(tasks)
    
    # Default status is "Not started"
    status = "Not started"
    
    # Get next number for this status
    status_tasks = grouped_tasks[status]
    next_number = 1  # New task always gets number 1
    
    # Format task name with number
    formatted_name = format_task_title(next_number, simplified_name)
    
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
                "number": next_number
            }
        }
    }

    # Add deadline if found
    if deadline_date:
        data["properties"]["Deadline"] = {
            "date": {
                "start": deadline_date
            }
        }

    try:
        response = requests.post(url, headers=HEADERS, json=data)
        if response.status_code >= 200 and response.status_code < 300:
            result = response.json()
            page_url = result.get("url", "No page URL returned.")
            print(f"✅ Task added to Notion: {page_url}")
            
            # Run auto-numbering to ensure everything is in order
            auto_number_tasks()
            return True
        else:
            print(f"❌ Notion API error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Notion request failed: {str(e)}")
        return False

# Run the automation
auto_number_tasks()
