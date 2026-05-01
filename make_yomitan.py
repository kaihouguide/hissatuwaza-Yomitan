import os
import json
import re
import zipfile
import glob

def extract_term_and_reading(raw_name):
    """
    Extracts the term and reading from the move name.
    Expects formats like "180分の恋奴隷(インスタントラヴァー)" or "技名（よみ）"
    Returns (term, reading)
    """
    match = re.search(r'^(.*?)[(（](.*?)[)）]$', raw_name.strip())
    if match:
        term = match.group(1).strip()
        reading = match.group(2).strip()
        return term, reading
    return raw_name.strip(), ""

def build_structured_content(series_name, user, description):
    """
    Builds Yomitan structured content for clean formatting inside the extension.
    """
    content =[]
    
    # 1. Series Name
    content.append({
        "tag": "div",
        "content":[
            {"tag": "span", "style": {"fontWeight": "bold", "color": "#007BFF"}, "content": "【作品】 "},
            {"tag": "span", "content": series_name}
        ]
    })
    
    # 2. User / Character
    if user:
        content.append({
            "tag": "div",
            "content":[
                {"tag": "span", "style": {"fontWeight": "bold", "color": "#28A745"}, "content": "【使用者】 "},
                {"tag": "span", "content": user}
            ]
        })
        
    # 3. Description
    if description:
        desc_content =[]
        for line in description.split('\n'):
            desc_content.append(line)
            desc_content.append({"tag": "br"})
            
        if desc_content:
            desc_content.pop() # Remove the trailing <br>
            
        content.append({
            "tag": "div",
            "style": {"marginTop": "0.5em"},
            "content": desc_content
        })
        
    return {
        "type": "structured-content",
        "content": content
    }

def build_yomitan_dictionary(input_dir=".", output_zip="Hissatsu_Waza_Yomitan.zip"):
    print("Finding scraped JSON files...")
    files = glob.glob(os.path.join(input_dir, "moves_*.json"))
    
    if not files:
        print("No 'moves_*.json' files found in the current directory.")
        return

    term_bank =[]
    sequence = 0
    
    for file in files:
        print(f"Processing {file}...")
        with open(file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"  ! Skipping {file} due to JSON format error.")
                continue
                
            for series in data:
                series_name = series.get("series_name", "Unknown Series")
                
                for move in series.get("moves",[]):
                    raw_name = move.get("move_name", "")
                    if not raw_name:
                        continue
                        
                    user = move.get("user", "")
                    description = move.get("description", "")
                    
                    term, reading = extract_term_and_reading(raw_name)
                    definition = build_structured_content(series_name, user, description)
                    
                    # Yomitan format:[term, reading, definition_tags, rules, score, definitions, sequence, term_tags]
                    entry =[
                        term,
                        reading,
                        "", 
                        "", 
                        0,  
                        [definition],
                        sequence,
                        ""  
                    ]
                    
                    term_bank.append(entry)
                    sequence += 1

    total_entries = len(term_bank)
    print(f"\nTotal moves processed: {total_entries}")
    
    # Yomitan requires term banks to be split into chunks (max 10,000 entries per file)
    chunk_size = 10000
    chunks = [term_bank[i:i + chunk_size] for i in range(0, total_entries, chunk_size)]
    
    print(f"Building {output_zip}...")
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        
        # 1. Write the term banks
        for i, chunk in enumerate(chunks):
            filename = f"term_bank_{i + 1}.json"
            json_str = json.dumps(chunk, ensure_ascii=False, separators=(',', ':'))
            zf.writestr(filename, json_str)
            
        # 2. Write the index.json (Dictionary Metadata)
        index_data = {
            "title": "必殺技辞典 (Hissatsu Waza)",
            "format": 3,
            "revision": "1.0",
            "sequenced": True,
            "author": "Scraper",
            "url": "https://hissatuwaza.kill.jp/list/",
            "description": "A dictionary of anime/manga/game special moves.\nScraped from hissatuwaza.kill.jp.",
            "attribution": "Data from hissatuwaza.kill.jp"
        }
        zf.writestr("index.json", json.dumps(index_data, ensure_ascii=False, indent=2))
        
    print(f"Successfully created Yomitan dictionary: {output_zip}")

if __name__ == "__main__":
    build_yomitan_dictionary()
