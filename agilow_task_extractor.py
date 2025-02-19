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
    """Extract tasks from transcription"""
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

    Based on the current board state above:
    1. Use EXACT status values from Available Status Options
    2. Use EXACT names from team members list
    3. For existing tasks, use their exact names
    4. For dates, use YYYY-MM-DD format

    Return ONLY the JSON array of tasks to create or update.

    Example response format:
    [
        {{
            "task": "Task name",
            "status": "In Progress",  # Must match exactly
            "deadline": "YYYY-MM-DD",
            "assignee": "Exact Name"
        }}
    ]
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
            if all(key in task for key in ['task', 'status', 'deadline', 'assignee']):
                valid_tasks.append(task)
            else:
                print(f"⚠️ Skipping invalid task format: {task}")
        
        if not valid_tasks:
            print("❌ No valid tasks found in response")
            return []
        
        print(f"\n📋 Tasks to be added/updated:")
        for task in valid_tasks:
            deadline = task['deadline'] or 'No deadline'
            print(f"{task['task']} ({task['status']}) - Due: {deadline}")

        return valid_tasks
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {str(e)}")
        print(f"Received response: {response}")
        return []