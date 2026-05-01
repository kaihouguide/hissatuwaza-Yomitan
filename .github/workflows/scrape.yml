name: Daily Automated Scraper

on:
  schedule:
    - cron: '0 0 * * *' 
  workflow_dispatch: 

permissions:
  contents: write

jobs:
  scrape:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run scraper
        run: python scraper.py

      - name: Commit and push changes
        run: |
          git config --global user.name 'github-actions[bot]'
          git config --global user.email 'github-actions[bot]@users.noreply.github.com'
          
          # Add ALL JSON files starting with 'moves_' to the commit
          git add moves_*.json
          
          # Only commit if the files actually changed
          git diff --staged --quiet || git commit -m "Automated daily update: Fetched latest special moves"
          git push
