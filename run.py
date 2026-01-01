import sys
from streamlit.web import cli as stcli

def start():
    # Було src/ui/app.py, стало просто app.py
    sys.argv = ["streamlit", "run", "app.py"]
    sys.exit(stcli.main())

if __name__ == "__main__":
    start()