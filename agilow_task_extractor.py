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
    
    for task in tasks:
        status = task["properties"]["Status"]["status"]["name"]
        name = task["properties"]["Name"]["title"][0]["text"]["content"]
        statuses[status].append(name)
    
    for status, tasks in statuses.items():
        board_state += f"\n{status}:\n"
        for task in tasks:
            board_state += f"- {task}\n"
    
    return board_state

def extract_tasks(transcription):
    """
    Extracts tasks with status and deadlines from transcription using GPT-4
    Returns: List of task dictionaries
    """
    if not transcription:
        return []

    # Get current board state
    current_tasks = fetch_tasks()
    board_state = format_board_state(current_tasks)
    current_date = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
    {board_state}
    Today's date is {current_date}.
    
    Based on the current board state and the following spoken input, extract new tasks.
    For each task:
    1. Determine the appropriate status (Not started/In Progress/Done)
    2. Extract any deadlines
    3. The task number should continue the sequence in its respective column
    
    Spoken Input:
    {transcription}

    Return a valid JSON array of tasks. Example:
    [
        {{
            "task": "Review documentation",
            "status": "Not started",
            "deadline": null,
            "number": 1  # Based on current column state
        }}
    ]
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI that extracts tasks and determines their proper placement on a Kanban board. Always return a valid JSON array."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        tasks_json = response.choices[0].message.content.strip()
        
        # Clean up the response to handle potential formatting issues
        tasks_json = tasks_json.replace("```json", "").replace("```", "").strip()
        
        try:
            tasks = json.loads(tasks_json)
            if not isinstance(tasks, list):
                print("❌ Invalid response format: Expected a list of tasks")
                return []
                
            # Validate each task has required fields
            valid_tasks = []
            for task in tasks:
                if all(key in task for key in ['task', 'status', 'deadline', 'number']):
                    valid_tasks.append(task)
                else:
                    print(f"⚠️ Skipping invalid task format: {task}")
            
            if not valid_tasks:
                print("❌ No valid tasks found in response")
                return []
                
            print(f"\n📋 Extracted Tasks:")
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