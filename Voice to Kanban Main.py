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
                success_count = 0
                for task_dict in task_dicts:
                    if add_to_notion(task_dict):
                        success_count += 1
                
                if success_count > 0:
                    print(f"🚀 Successfully added {success_count}/{len(task_dicts)} tasks to Notion!")
                else:
                    print("⚠️ Failed to add any tasks to Notion.")
            else:
                print("⚠️ No valid tasks were extracted.")

if __name__ == "__main__":
    main()