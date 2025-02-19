import openai
from agilow_config import OPENAI_API_KEY
from datetime import datetime
from agilow_notion_handler import fetch_tasks
import json

client = openai.OpenAI(api_key=OPENAI_API_KEY)

def format_board_state(tasks):
    """Format current board state for GPT"""
    board_state = "Current Board State:\n"
    statuses = {"Not started": [], "In Progress": [], "Done": []}
    
    # Group tasks by status
    for task in tasks:
        status = task["properties"]["Status"]["status"]["name"]
        name = task["properties"]["Name"]["title"][0]["text"]["content"]
        number = task["properties"]["Task Number"]["number"]
        statuses[status].append((number, name))
    
    # Format tasks
    for status, tasks in statuses.items():
        board_state += f"\n{status}:\n"
        for number, name in sorted(tasks):
            board_state += f"{number}. {name}\n"
    
    return board_state

def extract_tasks(transcription):
    """Extract tasks from transcription"""
    if not transcription:
        return []

    current_tasks = fetch_tasks()
    board_state = format_board_state(current_tasks)
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Calculate highest number for each status
    max_numbers = {
        status: max([
            t["properties"]["Task Number"]["number"] 
            for t in current_tasks 
            if t["properties"]["Status"]["status"]["name"] == status
        ] + [0])
        for status in ["Not started", "In Progress", "Done"]
    }

    prompt = f"""
    {board_state}
    Today's date is {current_date}.
    
    SPOKEN INPUT TO PROCESS:
    "{transcription}"

    Extract new tasks and return them in this EXACT JSON format:
    [
        {{
            "task": "Task description here",
            "status": "Not started",
            "deadline": "YYYY-MM-DD",
            "number": 1
        }}
    ]

    Rules:
    1. Status must be exactly one of: "Not started", "In Progress", or "Done"
    2. Deadline must be in YYYY-MM-DD format or null
    3. Number new tasks starting from the highest existing number + 1 in each status
    4. Return ONLY the JSON array

    Current highest numbers:
    - Not started: {max_numbers['Not started']}
    - In Progress: {max_numbers['In Progress']}
    - Done: {max_numbers['Done']}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are a task extraction AI. Extract new tasks and number them sequentially after existing tasks."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        tasks_json = response.choices[0].message.content.strip()
        tasks_json = tasks_json.replace("```json", "").replace("```", "").strip()
        
        try:
            tasks = json.loads(tasks_json)
            if not isinstance(tasks, list):
                print("❌ Invalid response format: Expected a list of tasks")
                return []
            
            # Validate tasks
            valid_tasks = []
            for task in tasks:
                if all(key in task for key in ['task', 'status', 'deadline', 'number']):
                    valid_tasks.append(task)
                else:
                    print(f"⚠️ Skipping invalid task format: {task}")
            
            if not valid_tasks:
                print("❌ No valid tasks found in response")
                return []
            
            print(f"\n📋 Tasks to be added:")
            for task in valid_tasks:
                deadline = task['deadline'] or 'No deadline'
                print(f"{task['number']}. {task['task']} ({task['status']}) - Due: {deadline}")

            return valid_tasks
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {str(e)}")
            print(f"Received response: {tasks_json}")
            return []
            
    except Exception as e:
        print(f"❌ OpenAI API error: {str(e)}")
        return []