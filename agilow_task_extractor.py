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
        
        # Get deadline - FIXED to handle None values properly
        deadline = "No deadline"
        if "Deadline" in task["properties"] and task["properties"]["Deadline"] is not None:
            date_obj = task["properties"]["Deadline"].get("date")
            if date_obj:
                deadline = date_obj.get("start", "No deadline")
            
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
    5. Add comments to tasks

    CRITICAL: Return ONLY a JSON array. Do not include any explanations, text, or comments before or after the JSON array.

    IMPORTANT: When the user asks to "add a comment" or "comment on" a task, use the comment operation format below, NOT the update operation.

    For adding comments, use this format:
    {{
        "operation": "comment",
        "task": "Exact Task Name",
        "comment": "Comment text here"
    }}

    When updating existing tasks (status/deadline/assignee changes), use this format:
    {{
        "operation": "update",
        "task": "Exact Task Name",
        "status": "New Status",
        "deadline": "YYYY-MM-DD",  // maintain existing if not changing
        "assignee": "Person Name"   // maintain existing if not changing
    }}

    For deadlines:
    - Use ISO format dates (YYYY-MM-DD)
    - For "tonight" or "today", use "{current_date}"
    - If no specific deadline, omit the deadline field entirely

    IMPORTANT:
    1. Return ONLY one JSON array containing ALL operations
    2. Use EXACT status values from Available Status Options
    3. Use EXACT names from team members list
    4. For bulk updates, create separate operations for each task
    5. Always maintain existing values when updating tasks
    6. Return ONLY a JSON array for each task. Do not add any explanation or text.
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
            operation = task.get('operation', '')
            
            if operation == 'delete' and task.get('task'):
                valid_tasks.append(task)
            elif operation == 'comment' and all(key in task for key in ['task', 'comment']):
                valid_tasks.append(task)
            elif operation == 'rename' and all(key in task for key in ['old_name', 'new_name']):
                valid_tasks.append(task)
            elif operation == 'update' and task.get('task'):
                valid_tasks.append(task)
            elif (operation == 'create' or not operation) and task.get('task'):
                task['status'] = task.get('status', 'Not started')
                valid_tasks.append(task)
            else:
                print(f"⚠️ Skipping invalid task format: {task}")
        
        # Print operations summary
        print(f"\n📋 Operations to perform:")
        for task in valid_tasks:
            if task.get('operation') == 'delete':
                print(f"🗑️  Delete: {task['task']}")
            elif task.get('operation') == 'comment':
                print(f"💬 Comment on: {task['task']}")
            elif task.get('operation') == 'rename':
                print(f"✏️  Rename: {task['old_name']} → {task['new_name']}")
            elif task.get('operation') == 'update':
                updates = []
                if 'status' in task: updates.append(f"status: {task['status']}")
                if 'deadline' in task: updates.append(f"deadline: {task['deadline']}")
                if 'assignee' in task: updates.append(f"assignee: {task['assignee']}")
                print(f"✏️  Update {task['task']}: {', '.join(updates)}")
            else:
                # New task
                status = task.get('status', 'Not started')
                deadline = task.get('deadline', 'No deadline')
                assignee = task.get('assignee', 'Unassigned')
                print(f"✨ New Task: {task['task']} ({status}) - Due: {deadline}, Assigned to: {assignee}")

        return valid_tasks
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {str(e)}")
        print(f"Received response: {response}")
        return []