import openai
from agilow_config import OPENAI_API_KEY

client = openai.OpenAI(api_key=OPENAI_API_KEY)

def extract_tasks(transcription):
    """
    Extracts tasks from transcription using GPT-4
    Returns: List of tasks
    """
    if not transcription:
        return []

    prompt = f"""
    Extract actionable task titles from the following spoken input.
    Guidelines:
    - Convert natural speech into clear, actionable task titles.
    - Maintain the original intent but make each task specific and trackable.
    - Use imperative verbs (e.g., "Create", "Update", "Research").
    - Combine related items into single tasks where logical.
    - Remove filler words and conversational elements.

    Spoken Input:
    {transcription}

    Format each task as a single line without bullets or numbers.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI that extracts clear, actionable tasks from natural speech."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        tasks_text = response.choices[0].message.content.strip()
        tasks = [
            line.strip().lstrip("-•1234567890. ")
            for line in tasks_text.split('\n')
            if line.strip()
        ]

        if not tasks:
            print("❌ No actionable tasks extracted.")
            return []
            
        print(f"\n📋 Extracted Tasks:")
        for i, task in enumerate(tasks, 1):
            print(f"{i}. {task}")

        return tasks
        
    except Exception as e:
        print(f"❌ OpenAI API error: {str(e)}")
        return []