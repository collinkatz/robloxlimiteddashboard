## Initial setup goes like this for Windows
0. Copy and paste the text in your browsers roblosecurity cookie (you can find this cookie while you're logged into roblox) into a new text file in this directory as `roblosecurity.txt`
1. Create a new virtual environment while in this repository `python -m venv .venv`
2. Activate virtual environment `.\.venv\Scripts\activate`
3. Install requirements from file `python -m pip install -r requirements.txt`
4. Run dashboard `streamlit run .\dashboard.py`