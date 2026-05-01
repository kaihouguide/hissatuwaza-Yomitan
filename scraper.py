import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import concurrent.futures
import time

# Use a 'Session' to hold the connection open.
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

def fetch_and_parse_detail(url):
    """Downloads a single detail page and extracts the User and Description"""
    try:
        resp = session.get(url, timeout=15)
        soup = BeautifulSoup(resp.content, 'html.parser')
        parsed = {}
        
        for dt in soup.find_all('table', {'border': '1'}):
            d_rows = dt.find_all('tr')
            if not d_rows: continue
            d_tds = d_rows[0].find_all('td')
            if not d_tds: continue
            
            a_tag = d_tds[0].find('a', attrs={'name': True})
            if not a_tag: continue
            
            m_anchor = a_tag['name']
            
            # 1. Grab the User (Character)
            m_user = d_tds[1].get_text(strip=True) if len(d_tds) > 1 else ""
            
            # 2. Grab the Description (Combines all text from row 3 downwards)
            desc_parts =[]
            if len(d_rows) >= 3:
                for dr in d_rows[2:]:
                    td = dr.find('td')
                    if td:
                        desc_parts.append(td.get_text(separator='\n', strip=True))
            
            parsed[m_anchor] = {
                "user": m_user,
                "description": '\n'.join(desc_parts).strip()
            }
        return url, parsed
    except Exception as e:
        return url, {}

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
    
    # Keep cache outside the loop so we don't redownload shared detail pages
    page_cache = {}

    print("Starting Hyper-Fast Splitting Scraper...\n")

    for page in pages:
        target_url = urljoin(base_url, page)
        
        # Create a specific filename for this letter (e.g., "moves_a.json")
        file_prefix = page.split('.')[0]
        output_filename = f"moves_{file_prefix}.json"
        
        print(f"Scraping Index: {target_url} -> Saving to {output_filename}")
        
        # 1. Load existing data for THIS specific letter
        existing_series = {}
        if os.path.exists(output_filename):
            with open(output_filename, 'r', encoding='utf-8') as f:
                try:
                    old_data = json.load(f)
                    for item in old_data:
                        moves_dict = {m['move_name']: m for m in item.get('moves',[])}
                        existing_series[item['series_name']] = {
                            "series_url": item['series_url'],
                            "moves": moves_dict
                        }
                except json.JSONDecodeError:
                    print(f"Existing {output_filename} is corrupted. Starting fresh.")

        try:
            response = session.get(target_url, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            main_table = soup.find('table', {'border': '1'})
            if not main_table:
                continue
                
            pending_moves =[]
            needed_urls = set()
            
            for row in main_table.find_all('tr'):
                tds = row.find_all('td')
                if len(tds) >= 2:
                    series_a = tds[0].find('a', href=True)
                    if not series_a: continue
                    series_name = series_a.get_text(strip=True)
                    series_url = urljoin(target_url, series_a['href'])
                    
                    for move_a in tds[1].find_all('a', href=True):
                        move_name = move_a.get_text(strip=True)
                        if not move_name: continue
                        
                        move_link = urljoin(target_url, move_a['href'])
                        if '#' in move_link:
                            base_detail_url, anchor = move_link.split('#', 1)
                        else:
                            base_detail_url, anchor = move_link, None
                            
                        existing_move = existing_series.get(series_name, {}).get("moves", {}).get(move_name)
                        needs_details = not existing_move or "description" not in existing_move
                        
                        if needs_details and base_detail_url not in page_cache:
                            needed_urls.add(base_detail_url)
                            
                        pending_moves.append({
                            "series_name": series_name,
                            "series_url": series_url,
                            "move_name": move_name,
                            "move_link": move_link,
                            "base_url": base_detail_url,
                            "anchor": anchor,
                            "needs_details": needs_details
                        })
                        
            # Download the needed detail pages 10 at a time
            if needed_urls:
                print(f"    -> Fetching {len(needed_urls)} detail pages concurrently...")
                with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                    futures = {executor.submit(fetch_and_parse_detail, u): u for u in needed_urls}
                    for future in concurrent.futures.as_completed(futures):
                        url, parsed_data = future.result()
                        page_cache[url] = parsed_data

            # Assign the downloaded data
            for p in pending_moves:
                s_name = p["series_name"]
                m_name = p["move_name"]
                
                if s_name not in existing_series:
                    existing_series[s_name] = {"series_url": p["series_url"], "moves": {}}
                    
                if p["needs_details"]:
                    user_text, desc_text = "", ""
                    if p["anchor"] and p["base_url"] in page_cache:
                        details = page_cache[p["base_url"]].get(p["anchor"], {})
                        user_text = details.get("user", "")
                        desc_text = details.get("description", "")
                        
                    existing_series[s_name]["moves"][m_name] = {
                        "move_name": m_name,
                        "url": p["move_link"],
                        "user": user_text,
                        "description": desc_text
                    }
                        
        except Exception as e:
            print(f"    ! Failed Index {target_url}: {e}")
            
        # SAVE the JSON file for THIS LETTER immediately!
        final_data =[]
        
        # 1. SORT series alphabetically so Git doesn't falsely detect changes
        for s_name in sorted(existing_series.keys()):
            s_data = existing_series[s_name]
            
            # 2. SORT moves alphabetically within the series
            sorted_moves = sorted(list(s_data["moves"].values()), key=lambda x: x["move_name"])
            
            final_data.append({
                "series_name": s_name,
                "series_url": s_data["series_url"],
                "moves": sorted_moves
            })
            
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)
            
    print("\n" + "="*40)
    print("Scraping and updating successfully finished!")

if __name__ == "__main__":
    scrape_hissatuwaza_dictionary()
