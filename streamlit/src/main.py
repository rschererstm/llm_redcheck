# src/main.py

import streamlit as st
import streamlit_authenticator as stauth
import config as cfg
from utils import generate_image_description, generate_combined_report


def app():
#     config = get_config()
#     authenticator = stauth.Authenticate(
#         credentials=config['credentials'],
#         cookie_name=config['cookie']['name'],
#         key=config['cookie']['key'],
#         cookie_expiry_days=config['cookie']['expiry_days']
#     )

#     if 'authentication_status' not in st.session_state:
#         st.warning("Please go to the 'Login' page to authenticate.")
#         st.stop()
#     elif st.session_state['authentication_status'] != True:
#         st.warning("You are not authenticated. Please go to the 'Login' page.")
#         st.stop()

    st.title("Eye Report Generator :eyes: :sparkles:")
    st.markdown("This page allows you to upload left eye and right eye images, set custom prompts, and generate a combined report.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Right Eye")
        right_eye_image = st.file_uploader("Upload Right Eye Image", type=["jpg", "jpeg", "png"], key="right_eye")
        prompt_right = st.text_area("Prompt for Right Eye Description", value="Describe this medical exam...")

    with col2:
        st.subheader("Left Eye")
        left_eye_image = st.file_uploader("Upload Left Eye Image", type=["jpg", "jpeg", "png"], key="left_eye")
        prompt_left = st.text_area("Prompt for Left Eye Description", value="Describe this medical exam...")

    st.markdown("---")
    reasoning_prompt = st.text_area("Prompt for Combined Medical Report", value="Summarize each eye condition in a concise medical report...")

    st.subheader("Select Models")
    description_model = st.text_input("Model for Descriptions (Azure Deployment Name)", value="gpt-4")
    reasoning_model = st.text_input("Model for Reasoning (Azure Deployment Name)", value="gpt-4")

    generate_button = st.button("Generate Medical Report")

    if generate_button:
        if not right_eye_image or not left_eye_image:
            st.error("Please upload both right eye and left eye images.")
        else:
            with st.spinner("Generating descriptions..."):
                right_description = generate_image_description(right_eye_image, prompt_right, description_model)
                left_description = generate_image_description(left_eye_image, prompt_left, description_model)

            st.success("Descriptions generated successfully! :white_check_mark:")

            with st.spinner("Generating combined report..."):
                final_report_right = generate_combined_report(right_description, left_description, f'RIGHT EYE: {reasoning_prompt}', reasoning_model)
                final_report_left = generate_combined_report(right_description, left_description, f'LEFT EYE: {reasoning_prompt}', reasoning_model)
                st.success("Report generated!")

                st.markdown("---")
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### Right Eye Description")
                    st.write(right_description)

                    st.markdown("### Right Eye Report")
                    st.write(final_report_right)
                with col2:
                    st.markdown("### Left Eye Description")
                    st.write(left_description)
                    st.markdown("### Left Eye Report")
                    st.write(final_report_left)

    # authenticator.logout("Logout", "sidebar")

if __name__ == "__main__":
    app()
