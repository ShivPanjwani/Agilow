from agilow_audio_recorder import record_audio
from agilow_transcription import transcribe_audio
from agilow_task_extractor import extract_tasks
from agilow_notion_handler import add_to_notion

def main():
    # 1) Record audio
    audio_buffer = record_audio()
    
    # 2) Transcribe audio
    if audio_buffer:
        transcript = transcribe_audio(audio_buffer)
        
        # 3) Extract tasks with status and deadlines
        if transcript:
            task_dicts = extract_tasks(transcript)
            
            # 4) Add tasks to Notion
            if task_dicts:
                for task_dict in task_dicts:
                    add_to_notion(task_dict)
                print("🚀 All tasks added to Notion!")
            else:
                print("⚠️ No tasks extracted.")

if __name__ == "__main__":
    main()