from agilow_audio_recorder import record_audio
from agilow_transcription import transcribe_audio
from agilow_task_extractor import extract_tasks
from agilow_notion_handler import add_to_notion, handle_task_operations

def main():
    # 1) Record audio
    audio_buffer = record_audio()
    
    # 2) Transcribe audio
    if audio_buffer:
        transcript = transcribe_audio(audio_buffer)
        
        # 3) Extract tasks with status and deadlines
        if transcript:
            task_dicts = extract_tasks(transcript)
            
            # 4) Process each task operation
            for task_dict in task_dicts:
                if handle_task_operations(task_dict):
                    print("✅ Operation completed successfully")
                else:
                    print("❌ Operation failed")

if __name__ == "__main__":
    main()