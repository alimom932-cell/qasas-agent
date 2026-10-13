name: Agent V10 Trend Hunter NO MUSIC

on:
  schedule:
    - cron: '0 17 * * *'  # 8 مساءً بتوقيت السعودية كل يوم
  workflow_dispatch:  # تشغيل يدوي

jobs:
  run-agent:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          
      - name: Install system deps
        run: |
          sudo apt-get update
          sudo apt-get install -y ffmpeg fonts-noto-core fonts-dejavu-core
          
      - name: Install Python deps
        run: |
          pip install --upgrade pip
          pip install google-generativeai edge-tts gTTS moviepy==1.0.3 pillow numpy requests pytrends arabic-reshaper python-bidi google-api-python-client google-auth
          
      - name: Run Trend Agent V10
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          TOKEN_B64: ${{ secrets.TOKEN_B64 }}
          PEXELS_API_KEY: ${{ secrets.PEXELS_API_KEY }}
        run: |
          python main.py
          
      - name: Save history
        if: always()
        run: |
          git config --global user.name "Agent"
          git config --global user.email "agent@qasas.com"
          git add history.json .last_upload || true
          git commit -m "Update history" || true
          git push || true
