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

    # 1. Load existing data
    existing_series = {}
    if os.path.exists(output_filename):
        with open(output_filename, 'r', encoding='utf-8') as f:
            try:
                old_data = json.load(f)
                for item in old_data:
                    # Store existing moves with all their detail data
                    moves_dict = {m['move_name']: m for m in item.get('moves', [])}
                    existing_series[item['series_name']] = {
                        "series_url": item['series_url'],
                        "moves": moves_dict
                    }
            except json.JSONDecodeError:
                print("Existing JSON is corrupted or empty. Starting fresh.")

    new_series_count = 0
    new_moves_count = 0
    upgraded_moves_count = 0
    
    # We use this cache to ensure we only download each detail page (like a-ku2.htm) ONCE per run.
    # It contains dozens of moves, so this makes the script extremely fast!
    page_cache = {} 

    print("Checking for new and un-detailed entries...\n")

    for page in pages:
        target_url = urljoin(base_url, page)
        print(f"Checking index: {target_url} ... ", end="", flush=True)
        
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
                    
                    if series_name not in existing_series:
                        existing_series[series_name] = {
                            "series_url": series_url,
                            "moves": {}
                        }
                        new_series_count += 1
                        print(f"\n[NEW SERIES] {series_name}")
                        
                    # Check the moves inside this series
                    move_links = tds[1].find_all('a', href=True)
                    for move_a in move_links:
                        move_name = move_a.get_text(strip=True)
                        move_link = urljoin(target_url, move_a['href'])
                        
                        if not move_name:
                            continue
                            
                        existing_move = existing_series[series_name]["moves"].get(move_name)
                        
                        # We trigger a deep scrape if it's a completely NEW move, 
                        # OR if it's an old move that is missing the "description" data.
                        if not existing_move or "description" not in existing_move:
                            
                            user_text = ""
                            desc_text = ""
                            
                            # Parse out the base page and anchor (e.g. #a-ku2:5)
                            if '#' in move_link:
                                base_detail_url, anchor = move_link.split('#', 1)
                            else:
                                base_detail_url, anchor = move_link, None
                                
                            # Download and parse the detail page if we haven't already
                            if base_detail_url not in page_cache:
                                time.sleep(1) # Be polite when hitting a new detail page!
                                print(f"\n    -> Downloading details from {base_detail_url}")
                                try:
                                    detail_resp = requests.get(base_detail_url, timeout=15)
                                    detail_resp.encoding = 'utf-8'
                                    detail_soup = BeautifulSoup(detail_resp.text, 'html.parser')
                                    
                                    # Parse all move tables on this specific detail page
                                    parsed_details = {}
                                    detail_tables = detail_soup.find_all('table')
                                    for dt in detail_tables:
                                        d_rows = dt.find_all('tr')
                                        if not d_rows: continue
                                        d_tds = d_rows[0].find_all('td')
                                        if not d_tds: continue
                                        
                                        a_tag = d_tds[0].find('a', attrs={'name': True})
                                        if not a_tag: continue
                                        
                                        m_anchor = a_tag['name']
                                        
                                        # Extract the Character/User (Column 2 of Row 1)
                                        m_user = d_tds[1].get_text(strip=True) if len(d_tds) > 1 else ""
                                        
                                        # Extract the Description (Usually the last row)
                                        m_desc = ""
                                        if len(d_rows) >= 3:
                                            desc_td = d_rows[-1].find('td')
                                            if desc_td:
                                                # separator='\n' elegantly converts <br> tags into linebreaks!
                                                m_desc = desc_td.get_text(separator='\n', strip=True)
                                                
                                        parsed_details[m_anchor] = {
                                            "user": m_user,
                                            "description": m_desc
                                        }
                                        
                                    page_cache[base_detail_url] = parsed_details
                                except Exception as e:
                                    print(f"       Failed to load details: {e}")
                                    page_cache[base_detail_url] = {}
                            
                            # Now retrieve the user/desc from our cache using the anchor
                            if anchor and anchor in page_cache[base_detail_url]:
                                user_text = page_cache[base_detail_url][anchor]["user"]
                                desc_text = page_cache[base_detail_url][anchor]["description"]
                            
                            # Save the new move data
                            existing_series[series_name]["moves"][move_name] = {
                                "move_name": move_name,
                                "url": move_link,
                                "user": user_text,
                                "description": desc_text
                            }
                            
                            if not existing_move:
                                new_moves_count += 1
                                print(f"    + [NEW] {move_name} (User: {user_text})")
                            else:
                                upgraded_moves_count += 1
                                print(f"    *[UPGRADED] {move_name}")
                            
            print("Done!")
            
        except Exception as e:
            print(f"Failed! Error: {e}")

        # Pause to be polite to the server for the index pages
        time.sleep(1) 

    # 2. If nothing is new, stop here
    if new_series_count == 0 and new_moves_count == 0 and upgraded_moves_count == 0:
        print("\n" + "="*40)
        print("No new entries found today! Database is up to date.")
        return

    # 3. Convert tracking dictionary back into JSON list
    final_data =[]
    for s_name, s_data in existing_series.items():
        moves_list = list(s_data["moves"].values())
        final_data.append({
            "series_name": s_name,
            "series_url": s_data["series_url"],
            "moves": moves_list
        })

    # 4. Overwrite JSON
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

    print("\n" + "="*40)
    print(f"Update complete!")
    print(f"New Series Added: {new_series_count}")
    print(f"New Moves Added: {new_moves_count}")
    print(f"Old Moves Upgraded with descriptions: {upgraded_moves_count}")
    print(f"File updated: {output_filename}")

if __name__ == "__main__":
    scrape_hissatuwaza_dictionary()
