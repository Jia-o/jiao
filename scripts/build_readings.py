"""Fetch the reading list Google Doc and write readings.json.

Runs in GitHub Actions. Expects two environment variables (set as repo secrets):
  GOOGLE_CREDS - the full service account JSON
  DOC_ID       - the Google Doc ID
"""
import json
import os
import re

from google.oauth2 import service_account
from googleapiclient.discovery import build

OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "readings.json")
SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]


def get_docs_service():
    info = json.loads(os.environ["GOOGLE_CREDS"])
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("docs", "v1", credentials=creds)


def parse_doc(doc):
    content = doc.get("body", {}).get("content", [])
    readings = []
    all_tags = set()

    for element in content:
        if "paragraph" not in element:
            continue

        full_text = ""
        extracted_link = None

        for run in element["paragraph"]["elements"]:
            text_run = run.get("textRun", {})
            full_text += text_run.get("content", "")
            style = text_run.get("textStyle", {})
            if "link" in style:
                extracted_link = style["link"].get("url")

        clean_line = full_text.replace("\n", " ").replace("\xa0", " ").strip()

        if "|" in clean_line:
            parts = clean_line.split("|")
            title = parts[0].strip()
            tags = re.findall(r"#(\w+)", parts[1].lower())
            all_tags.update(tags)

            if title:
                readings.append({"title": title, "url": extracted_link, "themes": tags})

    return {"readings": readings, "tags": sorted(all_tags)}


def main():
    service = get_docs_service()
    doc = service.documents().get(documentId=os.environ["DOC_ID"]).execute()
    data = parse_doc(doc)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(data['readings'])} readings and {len(data['tags'])} tags to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()