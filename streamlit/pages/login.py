# pages/login.py

import streamlit as st
import streamlit_authenticator as stauth
from config import get_config

def login_page():
    config = get_config()
    authenticator = stauth.Authenticate(
        credentials=config['credentials'],
        cookie_name=config['cookie']['name'],
        key=config['cookie']['key'],
        cookie_expiry_days=config['cookie']['expiry_days']
    )

    name, authentication_status, username = authenticator.login('Login', 'main')

    if authentication_status:
        st.success(f"Welcome, {name}! :sparkles:")
        st.experimental_rerun()
    elif authentication_status is False:
        st.error("Invalid username/password")
    else:
        st.info("Please enter your username and password to continue.")

def main():
    login_page()
