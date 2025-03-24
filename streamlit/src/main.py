import streamlit as st
import streamlit_authenticator as stauth
import yaml
import tempfile
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Eye Report Generator", layout="wide")


def get_config():
    with open('streamlit/src/auth.yaml') as file:
        config = yaml.safe_load(file)
    return config


def app():
    config = get_config()
    authenticator = stauth.Authenticate(credentials=config['credentials'])

    try:
        authenticator.login(fields={'Form name':'Login', 'Username':'Username', 'Password':'Password', 'Login':'Login', 'Captcha':'Captcha'})
    except Exception as e:
        st.error(e)

    if 'authentication_status' not in st.session_state:
        st.warning("Please go to the 'Login' page to authenticate.")
        st.stop()
    elif st.session_state['authentication_status'] != True:
        token_value = st.text_input("Enter your access token", type="password", key="token")
        if token_value:
            st.session_state.token = token_value
        else:
            st.warning("Token is required for authentication.")
        st.warning("You are not authenticated.")
        st.stop()

    st.title("Eye Report Generator :eyes: :sparkles:")
    st.markdown(
        "This page allows you to upload left eye and right eye images, set custom prompts, and generate a combined report."
    )
    
    if st.session_state.get("authentication_status") is True:
        from utils import analyze_image, synthesize_medical_report
    
    # --------------------------------------------------
    # Helper function to process a single image in parallel
    # --------------------------------------------------
    def process_single_image(file, exam_type, prompt, eye_key):
        """
        file: the uploaded file from st.file_uploader
        exam_type: e.g. "oct_macula"
        prompt: the text prompt to pass to analyze_image
        eye_key: "right" or "left" so we know which eye it belongs to
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.name) as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name

        result = analyze_image(tmp_path, exam_type, prompt)  # call your custom function
        os.remove(tmp_path)

        # Return both the eye_key (to sort results later) and the analysis result
        return eye_key, result



    # Select exam type
    exam_type = st.selectbox("Exam Type", ["oct_macula", "retinografia", "campimetria"])
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Right Eye")
        right_eye_image = st.file_uploader(
            "Upload Right Eye Image(s)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="right_eye"
        )
        
    with col2:
        st.subheader("Left Eye")
        left_eye_image = st.file_uploader(
            "Upload Left Eye Image(s)",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key="left_eye"
        )

    with st.expander("Additional Options", expanded=False):
        col3, col4 = st.columns(2)
        with col3:
            prompt_right = st.text_area(
                "Prompt for Right Eye Description",value=("Aja como um oftalmologista experiente. Você receberá imagens oftálmicas (como fotografias de fundo de olho, exames de OCT, campimetria ou outros exames visuais). Para cada imagem enviada:\n\n"
                                                          "Descreva detalhadamente todos os achados clínicos visuais presentes, utilizando uma linguagem técnica e precisa, como faria em um laudo médico.\n\n"
                                                          "Transcreva todo o conteúdo textual visível na imagem (como nomes de exames, parâmetros, valores numéricos, datas, identificação de paciente ou olhos, anotações do aparelho etc.).\n\n"
                                                          "Se aplicável, mencione a provável localização anatômica (ex.: mácula, disco óptico, arcadas vasculares etc.) dos achados descritos.\n\n"
                                                          "Não forneça diagnósticos definitivos, mas indique possíveis hipóteses ou condições associadas aos achados, se pertinente.\n\n"
                                                          "Mantenha uma linguagem objetiva, como se estivesse redigindo um relatório para outro profissional da área.")
            )
        with col4:
            prompt_left = st.text_area(
                "Prompt for Left Eye Description",value=("Aja como um oftalmologista experiente. Você receberá imagens oftálmicas (como fotografias de fundo de olho, exames de OCT, campimetria ou outros exames visuais). Para cada imagem enviada:\n\n"
                                                          "Descreva detalhadamente todos os achados clínicos visuais presentes, utilizando uma linguagem técnica e precisa, como faria em um laudo médico.\n\n"
                                                          "Transcreva todo o conteúdo textual visível na imagem (como nomes de exames, parâmetros, valores numéricos, datas, identificação de paciente ou olhos, anotações do aparelho etc.).\n\n"
                                                          "Se aplicável, mencione a provável localização anatômica (ex.: mácula, disco óptico, arcadas vasculares etc.) dos achados descritos.\n\n"
                                                          "Não forneça diagnósticos definitivos, mas indique possíveis hipóteses ou condições associadas aos achados, se pertinente.\n\n"
                                                          "Mantenha uma linguagem objetiva, como se estivesse redigindo um relatório para outro profissional da área.")
            )

        st.markdown("---")
        reasoning_prompt = st.text_area("Prompt for Combined Medical Report",
                                        value=("""Você é um oftalmologista experiente. A seguir, será apresentada uma série de descrições clínicas extraídas de exames oftálmicos (como fundoscopia, OCT, campimetria), cada uma representando diferentes achados em imagens distintas do mesmo olho.
                                               Sua tarefa é:
                                               1. Sintetizar essas descrições em um laudo único e coeso, como se estivesse redigindo um relatório médico para outro profissional da área.
                                               2. Utilize o seguinte modelo de estrutura:"""
            )
        )

        with open('streamlit/src/layouts.json') as file:
            layouts = yaml.safe_load(file)
        st.write("Estrutura do Laudo:")
        st.code(layouts[exam_type])

        description_model = st.text_input("Model for Description (Azure)", value="gpt-4o", disabled=True)
        reasoning_model   = st.text_input("Model for Reasoning (Azure)", value="gpt-4o", disabled=True)

    generate_button = st.button("Generate Medical Report")

    if generate_button:
        if not right_eye_image or not left_eye_image:
            st.error("Please upload images for both right and left eye.")
            st.stop()

        # Accumulate total costs from all calls
        total_costs = {
            "input_cost": 0.0,
            "cached_input_cost": 0.0,
            "output_cost": 0.0,
            "total_cost": 0.0
        }

        # ----------------------------------------------------------
        # 1. Analyze all images (right + left) in parallel
        # ----------------------------------------------------------
        right_descriptions = []
        left_descriptions = []

        st.markdown("<p style='color: blue;'><strong>## 1. Analyzing images in parallel...</strong></p>", 
                    unsafe_allow_html=True)

        with st.spinner("Analyzing images in parallel..."):
            futures = []
            with ThreadPoolExecutor() as executor:
                # Queue up Right Eye images
                for file in right_eye_image:
                    futures.append(
                        executor.submit(
                            process_single_image, file, exam_type, prompt_right, "right"
                        )
                    )
                # Queue up Left Eye images
                for file in left_eye_image:
                    futures.append(
                        executor.submit(
                            process_single_image, file, exam_type, prompt_left, "left"
                        )
                    )

                # Gather results
                for f in as_completed(futures):
                    eye_key, result = f.result()

                    # Accumulate costs from each call
                    for k in total_costs:
                        total_costs[k] += result["costs"][k]

                    if eye_key == "right":
                        right_descriptions.append(result["output"])
                    else:
                        left_descriptions.append(result["output"])

        st.success("All images analyzed!")

        # Optional: Show the raw descriptions
        with st.expander("Show Raw Descriptions", expanded=False):
            st.markdown("<p style='color: blue; font-weight:bold;'> 🖼️ Descriptions of each image</p>", unsafe_allow_html=True)
            colA, colB = st.columns(2)

            with colA:
                st.markdown("**Right Eye Descriptions**")
                for idx, desc in enumerate(right_descriptions, start=1):
                    st.write(f"**Image #{idx}**:")
                    st.write(desc)

            with colB:
                st.markdown("**Left Eye Descriptions**")
                for idx, desc in enumerate(left_descriptions, start=1):
                    st.write(f"**Image #{idx}**:")
                    st.write(desc)

        # ----------------------------------------------------------
        # 2. Generate final reports for each eye in parallel
        # ----------------------------------------------------------
        st.markdown("<p style='color: blue;'><strong>## 2. Generating final reports in parallel...</strong></p>", 
                    unsafe_allow_html=True)

        with st.spinner("Generating final reports in parallel..."):
            with ThreadPoolExecutor() as executor:
                future_right = executor.submit(
                    synthesize_medical_report,
                    right_descriptions,
                    exam_type,
                    reasoning_prompt
                )
                future_left = executor.submit(
                    synthesize_medical_report,
                    left_descriptions,
                    exam_type,
                    reasoning_prompt
                )

                final_report_right = future_right.result()
                final_report_left  = future_left.result()

                # Accumulate costs
                for k in total_costs:
                    total_costs[k] += final_report_right["costs"][k]
                for k in total_costs:
                    total_costs[k] += final_report_left["costs"][k]

        st.success("Final reports generated!")

        # ----------------------------------------------------------
        # Display final
        # ----------------------------------------------------------
        st.markdown("### Right Eye Final Report")
        st.json(final_report_right["output"])

        st.markdown("### Left Eye Final Report")
        st.json(final_report_left["output"])

        st.markdown("---")
        st.markdown("<p style='color: blue;'>**## 3. Total Costs 💰**</p>", unsafe_allow_html=True)
        st.write("Below is the sum of input, cached input, and output costs for **all** calls:")
        st.json({k: f"U${round(v, 3)}" for k, v in total_costs.items()})

    st.sidebar.title("Navigation")
    authenticator.logout("Logout", "sidebar")


if __name__ == "__main__":
    app()
