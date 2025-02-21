import openai
from agilow_config import OPENAI_API_KEY
from datetime import datetime
from agilow_notion_handler import fetch_tasks, fetch_users
import json

client = openai.OpenAI(api_key=OPENAI_API_KEY)

def format_board_state(tasks):
    """Format current board state for GPT"""
    # First, get all users
    users = fetch_users()
    
    board_state = "Current Board State:\n\n"
    
    # Add available assignees section
    board_state += "Available Team Members:\n"
    for user_name in users.keys():
        board_state += f"- {user_name}\n"
    
    board_state += "\nCurrent Tasks:\n"
    statuses = {"Not started": [], "In Progress": [], "Done": []}
    
    # Group tasks by status
    for task in tasks:
        status = task["properties"]["Status"]["status"]["name"]
        name = task["properties"]["Name"]["title"][0]["text"]["content"]
        
        # Get assignee
        assignee = None
        if "Assign" in task["properties"] and task["properties"]["Assign"]["people"]:
            assignee = task["properties"]["Assign"]["people"][0]["name"]
        
        # Get deadline
        deadline_prop = task["properties"].get("Deadline", {})
        deadline = deadline_prop.get("date", {}).get("start", "No deadline") if deadline_prop else "No deadline"
            
        statuses[status].append((name, assignee, deadline))
    
    # Format tasks by status
    for status, tasks in statuses.items():
        board_state += f"\n{status}:\n"
        for name, assignee, deadline in tasks:
            assignee_text = f", Assigned to: {assignee}" if assignee else ""
            board_state += f"- {name}{assignee_text} (Due: {deadline})\n"
    
    return board_state

def extract_tasks(transcription):
    """Extract tasks and operations from transcription"""
    current_tasks = fetch_tasks()
    board_state = format_board_state(current_tasks)
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    prompt = f"""
    {board_state}
    Today's date is {current_date}.

    Available Status Options:
    - "Not started"
    - "In Progress"
    - "Done"
    
    SPOKEN INPUT TO PROCESS:
    "{transcription}"

    You are a project management AI. Based on the current board state above, your role is to:
    1. Create new tasks
    2. Update existing tasks
    3. Delete tasks when requested
    4. Rename existing tasks
    5. Update task properties (assignee, deadline)

    When multiple operations are requested in a single command, combine ALL operations into ONE JSON array.
    Return ONLY the JSON array, no other text or explanations.

    Example of combined operations in one array:
    [
        {{
            "task": "Task Name",
            "operation": "delete"
        }},
        {{
            "operation": "rename",
            "old_name": "Old Task Name",
            "new_name": "New Task Name",
            "status": "Current Status",
            "deadline": "YYYY-MM-DD",
            "assignee": "Current Assignee"
        }},
        {{
            "task": "New Task",
            "status": "Not started",
            "deadline": "YYYY-MM-DD",
            "assignee": "Person Name"
        }}
    ]

    IMPORTANT:
    1. Return ONLY one JSON array containing ALL operations
    2. Use EXACT status values from Available Status Options
    3. Use EXACT names from team members list
    4. Use proper spacing in task names (e.g., "Database Migration Service")
    5. Use YYYY-MM-DD format for dates
    """

    response = get_gpt_response(prompt)
    return parse_json_response(response)

def get_gpt_response(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a task extraction AI. Extract new tasks and updates from spoken input."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ OpenAI API error: {str(e)}")
        return None

def parse_json_response(response):
    if not response:
        return []

    try:
        tasks_json = response.replace("```json", "").replace("```", "").strip()
        tasks = json.loads(tasks_json)
        if not isinstance(tasks, list):
            print("❌ Invalid response format: Expected a list of tasks")
            return []
        
        # Validate tasks
        valid_tasks = []
        for task in tasks:
            if task.get('operation') == 'delete' and task.get('task'):
                valid_tasks.append(task)
            elif task.get('operation') == 'rename' and all(key in task for key in ['old_name', 'new_name', 'status', 'deadline', 'assignee']):
                valid_tasks.append(task)
            elif all(key in task for key in ['task', 'status', 'deadline', 'assignee']):
                valid_tasks.append(task)
            else:
                print(f"⚠️ Skipping invalid task format: {task}")
        
        if not valid_tasks:
            print("❌ No valid tasks found in response")
            return []
        
        print(f"\n📋 Operations to perform:")
        for task in valid_tasks:
            if task.get('operation') == 'delete':
                print(f"🗑️  Delete: {task['task']}")
            elif task.get('operation') == 'rename':
                print(f"✏️  Rename: {task['old_name']} → {task['new_name']}")
            else:
                deadline = task['deadline'] or 'No deadline'
                print(f"✏️  Task: {task['task']} ({task['status']}) - Due: {deadline}")

        return valid_tasks
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {str(e)}")
        print(f"Received response: {response}")
        return []