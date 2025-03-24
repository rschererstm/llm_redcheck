# Use bash shell for consistency
set shell := ["bash", "-cu"]

# Initialize a new project with an optional Python version (default: python3)
new PYTHON_VERSION="python3":
    sudo apt install graphviz graphviz-dev
    git init
    {{PYTHON_VERSION}} -m venv .venv
    conda deactivate || true
    source .venv/bin/activate
    pip install uv
    uv init
    uv add ipykernel numpy pandas matplotlib streamlit
    uv pip freeze > requirements.txt
    uv sync
    curl -o .gitignore https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore
    git add .gitignore


# Add packages and update requirements.txt
add PACKAGE:
    source .venv/bin/activate
    uv add {{PACKAGE}}
    uv pip freeze > requirements.txt
    uv sync

# Streamlit run
run:
    source .venv/bin/activate
    streamlit run streamlit/src/main.py

# test azure
test_azure:
    source .venv/bin/activate
    python streamlit/src/utils.py