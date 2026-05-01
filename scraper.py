import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

def scrape_hissatuwaza_dictionary():
    base_url = "https://hissatuwaza.kill.jp/list/"
    
    pages =[
        "a.htm", "i.htm", "u.htm", "e.htm", "o.htm",
        "ka.htm", "ki.htm", "ku.htm", "ke.htm", "ko.htm",
        "sa.htm", "shi.htm", "su.htm", "se.htm", "so.htm",
        "ta.htm", "ti.htm", "tu.htm", "te.htm", "to.htm",
        "na.htm", "ni.htm", "nu.htm", "ne.htm", "no.htm",
        "ha.htm", "hi.htm", "hu.htm", "he.htm", "ho.htm",
        "ma.htm", "mi.htm", "mu.htm", "me.htm", "mo.htm",
        "ya.htm", "yu.htm", "yo.htm",
        "ra.htm", "ri.htm", "ru.htm", "re.htm", "ro.htm",
        "wa.htm", "wo.htm", "nn.htm"
    ]

    output_filename = "all_special_moves.json"

    # 1. Load existing data to compare against
    existing_series = {}
    if os.path.exists(output_filename):
        with open(output_filename, 'r', encoding='utf-8') as f:
            try:
                old_data = json.load(f)
                for item in old_data:
                    # Store existing moves in a dictionary for quick lookup
                    moves_dict = {m['move_name']: m['url'] for m in item['moves']}
                    existing_series[item['series_name']] = {
                        "series_url": item['series_url'],
                        "moves": moves_dict
                    }
            except json.JSONDecodeError:
                print("Existing JSON is corrupted or empty. Starting fresh.")

    print(f"Loaded {len(existing_series)} existing series from local JSON.")

    new_series_count = 0
    new_moves_count = 0
    
    print("Checking for new entries...\n")

    for page in pages:
        target_url = urljoin(base_url, page)
        print(f"Checking {target_url} ... ", end="", flush=True)
        
        try:
            response = requests.get(target_url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            main_table = soup.find('table', {'border': '1'})
            if not main_table:
                print("No data table found. Skipping.")
                continue
                
            rows = main_table.find_all('tr')
            for row in rows:
                tds = row.find_all('td')
                if len(tds) >= 2:
                    series_a = tds[0].find('a', href=True)
                    if not series_a:
                        continue
                        
                    series_name = series_a.get_text(strip=True)
                    series_url = urljoin(target_url, series_a['href'])
                    
                    # If this series has never been seen before, initialize it
                    if series_name not in existing_series:
                        existing_series[series_name] = {
                            "series_url": series_url,
                            "moves": {}
                        }
                        new_series_count += 1
                        print(f"\n[NEW SERIES] {series_name}")
                        
                    # Now check the moves inside this series
                    move_links = tds[1].find_all('a', href=True)
                    for move_a in move_links:
                        move_name = move_a.get_text(strip=True)
                        move_link = urljoin(target_url, move_a['href'])
                        
                        # If we find a move we haven't seen yet, add it
                        if move_name and move_name not in existing_series[series_name]["moves"]:
                            existing_series[series_name]["moves"][move_name] = move_link
                            new_moves_count += 1
                            print(f"\n    + [NEW MOVE] {move_name} ({series_name})")
                            
            print("Done!")
            
        except Exception as e:
            print(f"Failed! Error: {e}")

        # Pause to be polite to the server
        time.sleep(1) 

    # 2. If nothing is new, stop here so GitHub doesn't make an empty commit
    if new_series_count == 0 and new_moves_count == 0:
        print("\n" + "="*40)
        print("No new entries found today! Database is up to date.")
        return

    # 3. If there is new data, convert our tracking dictionary back into the JSON list format
    final_data =[]
    for s_name, s_data in existing_series.items():
        moves_list =[{"move_name": m_name, "url": m_url} for m_name, m_url in s_data["moves"].items()]
        final_data.append({
            "series_name": s_name,
            "series_url": s_data["series_url"],
            "moves": moves_list
        })

    # 4. Overwrite the JSON file with the merged, updated data
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print("\n" + "="*40)
    print(f"Update complete!")
    print(f"New Series Added: {new_series_count}")
    print(f"New Moves Added: {new_moves_count}")
    print(f"File updated: {output_filename}")

if __name__ == "__main__":
    scrape_hissatuwaza_dictionary()
