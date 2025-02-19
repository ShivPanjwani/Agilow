import requests
from datetime import datetime
from dateutil.parser import parse, ParserError
from agilow_config import NOTION_API_KEY, NOTION_DATABASE_ID

def parse_deadline_and_simplify_task(task_name):
    """Helper function to parse deadline from task"""
    try:
        dt, leftover_tokens = parse(task_name, fuzzy=True, fuzzy_with_tokens=True)
        leftover_text = "".join(leftover_tokens).strip()
        leftover_text = leftover_text.strip(",.:- ")
        final_words = leftover_text.split()
        if final_words and final_words[-1].lower() in ["by", "on", "before", "due"]:
            final_words.pop()
        leftover_text = " ".join(final_words).strip()
        return leftover_text, dt.date().isoformat()
    except (ParserError, ValueError):
        return task_name, None

def extract_status_if_any(task_name):
    """Helper function to extract status from task"""
    status_synonyms = {
        "Not Started": ["not started", "haven't started", "no progress", "unbegun", "pending start"],
        "In Development": ["in development", "in dev", "developing", "currently working on", "wip"],
        "Testing": ["testing", "test phase", "validation", "qa", "quality assurance"],
        "Reviewing": ["reviewing", "under review", "to review", "check", "verify"],
        "Done": ["done", "complete", "completed", "finished", "wrapped up"]
    }

    lowered = task_name.lower()
    for status_name, synonyms in status_synonyms.items():
        for s in synonyms:
            if s in lowered:
                return status_name
    return None

def add_to_notion(task_name):
    """
    Adds a task to Notion
    Returns: Boolean indicating success
    """
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    simplified_name, deadline_date = parse_deadline_and_simplify_task(task_name)
    status = extract_status_if_any(simplified_name)

    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": simplified_name}}]
            }
        }
    }

    if deadline_date:
        data["properties"]["Deadline"] = {
            "date": {
                "start": deadline_date
            }
        }

    if status:
        data["properties"]["Status"] = {
            "status": {"name": status}
        }

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code >= 200 and response.status_code < 300:
            result = response.json()
            page_url = result.get("url", "No page URL returned.")
            print(f"✅ Task added to Notion: {page_url}")
            return True
        else:
            print(f"❌ Notion API error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Notion request failed: {str(e)}")
        return False