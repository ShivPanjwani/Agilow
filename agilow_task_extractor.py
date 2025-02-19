import openai
from agilow_config import OPENAI_API_KEY
from datetime import datetime

client = openai.OpenAI(api_key=OPENAI_API_KEY)

def extract_tasks(transcription):
    """
    Extracts tasks with status and deadlines from transcription using GPT-4
    Returns: List of task dictionaries
    """
    if not transcription:
        return []

    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""
    Today's date is {current_date}.
    Extract tasks, their status, and deadlines from the following spoken input.
    Convert relative dates (e.g., "next Friday", "in two weeks") to YYYY-MM-DD format.
    Guidelines:
    - Convert natural speech into clear, actionable task titles
    - Determine task status (Not started, In Progress, or Done)
    - Extract any mentioned deadlines
    - Use imperative verbs (e.g., "Create", "Update", "Research")
    - Remove filler words and conversational elements

    Spoken Input:
    {transcription}

    Return a valid JSON array of tasks. Example:
    [
        {{
            "task": "Review documentation",
            "status": "Not started",
            "deadline": null
        }},
        {{
            "task": "Work on API integration",
            "status": "In Progress",
            "deadline": "2024-03-01"
        }}
    ]
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI that extracts tasks, their status, and deadlines from natural speech."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        tasks_json = response.choices[0].message.content.strip()
        # Parse the entire response as a single JSON array
        import json
        tasks = json.loads(tasks_json)

        if not tasks:
            print("❌ No actionable tasks extracted.")
            return []
            
        print(f"\n📋 Extracted Tasks:")
        for i, task in enumerate(tasks, 1):
            deadline = task['deadline'] or 'No deadline'
            print(f"{i}. {task['task']} ({task['status']}) - Due: {deadline}")

        return tasks
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {str(e)}")
        print(f"Received response: {tasks_json}")
        return []
    except Exception as e:
        print(f"❌ OpenAI API error: {str(e)}")
        return []