import streamlit as st
from openai import OpenAI
from pathlib import Path
import PyPDF2
import io
import base64
from docx import Document
import os
from PIL import Image

client = OpenAI(api_key=st.secrets['openai_api_key'])

def read_pdf(uploaded_file):
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(uploaded_file.read()))
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def read_docx(uploaded_file):
    doc = Document(io.BytesIO(uploaded_file.read()))
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def read_image(uploaded_file):
    # Save the uploaded image temporarily
    temp_img_path = "temp_image.jpg"
    with open(temp_img_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Encode the image to base64
    with open(temp_img_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")
    
    # Call the OpenAI API with the image
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract all text from this image, including any job description details. Provide a complete and accurate transcription.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
    )
    
    # Clean up the temporary file
    if os.path.exists(temp_img_path):
        os.remove(temp_img_path)
    
    return response.choices[0].message.content

def read_file_content(uploaded_file):
    if uploaded_file.type == "application/pdf":
        return read_pdf(uploaded_file)
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return read_docx(uploaded_file)
    elif uploaded_file.type.startswith("image/"):
        return read_image(uploaded_file)
    else:  # For text files
        return uploaded_file.getvalue().decode("utf-8")

def chat_page():
    st.title("chat")

    if "openai_model" not in st.session_state:
        st.session_state["openai_model"] = "gpt-4o-mini"

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("What is up?"):
        new_prompt = """
        You are developed by the devs of careersynchrony and you are a chatbot that can help users with our website. 
        here is what the features of our website are:
        careersynchrony is an AI-powered career development platform designed to help students, job seekers, and organizations optimize resumes and prepare for interviews. It offers an AI-driven resume builder with ATS compliance checking, job description parsing, and skill gap analysis. The platform features customizable mock interview sessions with real-time feedback, transcription, and video analysis to enhance interview performance. Progress tracking tools allow users and management teams to monitor career development milestones, while customizable dashboards provide insights into performance and progress. Built with a multi-tenant, white-label architecture, careersynchrony can be tailored for institutions or enterprises, offering seamless integrations and scalable solutions.
        """
        new_prompt = new_prompt + "\n" + "USER QUERY: " + prompt
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model=st.session_state["openai_model"],
                messages=[
                    {"role": m["role"], "content": new_prompt}
                    for m in st.session_state.messages
                ],
                stream=True,
            )
            response = st.write_stream(stream)
        st.session_state.messages.append({"role": "assistant", "content": response})

def jd_parser():
    st.title("Job Description Parser")

    uploaded_resume = st.file_uploader("Upload Resume (PDF/DOCX/TXT/JPG)", 
                                       type=["pdf", "txt", "docx", "jpg", "jpeg"])
    uploaded_jd = st.file_uploader("Upload Job Description (PDF/DOCX/TXT/JPG)", 
                                   type=["pdf", "txt", "docx", "jpg", "jpeg"])
    
    if uploaded_resume is not None and uploaded_jd is not None:
        with st.spinner("Processing files..."):
            # Parse both files using the appropriate method
            resume_text = read_file_content(uploaded_resume)
            jd_text = read_file_content(uploaded_jd)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an ATS system that analyzes resumes and job descriptions."},
                    {"role": "user", "content": f"Analyze the resume and job description. Provide an ATS score, list missing skills, and give detailed suggestions for improvement. Resume: {resume_text} Job Description: {jd_text}"}
                ]
            )

            analysis = response.choices[0].message.content
            st.write("Analysis Results:", analysis)

def cover_letter_generator():
    st.title("Cover Letter Generator")
    
    uploaded_resume = st.file_uploader("Upload Resume (PDF/DOCX/TXT/JPG)", 
                                       type=["pdf", "txt", "docx", "jpg", "jpeg"])
    uploaded_jd = st.file_uploader("Upload Job Description (PDF/DOCX/TXT/JPG)", 
                                   type=["pdf", "txt", "docx", "jpg", "jpeg"])
    
    if uploaded_resume is not None and uploaded_jd is not None:
        with st.spinner("Processing files..."):
            resume_text = read_file_content(uploaded_resume)
            jd_text = read_file_content(uploaded_jd)
            
            # Additional inputs for personalization
            company_name = st.text_input("Company Name:")
            hiring_manager = st.text_input("Hiring Manager's Name (if known):")
            
            if st.button("Generate Cover Letter"):
                prompt = f"""
                Generate a professional cover letter based on the following:
                Resume: {resume_text}
                Job Description: {jd_text}
                Company Name: {company_name}
                Hiring Manager: {hiring_manager}

                Create a compelling cover letter that:
                1. Matches the candidate's experience with the job requirements
                2. Highlights relevant achievements
                3. Shows enthusiasm for the role and company
                4. Maintains a professional yet personable tone
                """
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a professional cover letter writer."},
                        {"role": "user", "content": prompt}
                    ]
                )
                
                cover_letter = response.choices[0].message.content
                st.markdown("### Generated Cover Letter")
                st.write(cover_letter)
                
                # Add download button for the cover letter
                st.download_button(
                    label="Download Cover Letter",
                    data=cover_letter,
                    file_name="cover_letter.txt",
                    mime="text/plain"
                )

def tts_mode():
    st.title("Text-to-Speech Mode")

    # Input for the user text
    text_input = st.text_area("Enter text for speech:", "Today is a wonderful day to build something people love!")

    # List of available voices
    voices = ["alloy", "ash", "coral", "echo", "fable", "onyx", "nova", "sage", "shimmer"]
    voice = st.selectbox("Select voice:", voices)

    # Generate the speech file using OpenAI API
    if st.button("Generate Speech"):
        speech_file_path = Path(__file__).parent / "speech.mp3"
        response = client.audio.speech.create(
            model="tts-1",
            voice=voice,
            input=text_input
        )
        response.stream_to_file(speech_file_path)

        # Play the audio
        st.audio(speech_file_path)

def stt_mode():
    st.title("Speech-to-Text Mode")

    audio_file = st.file_uploader("Upload audio file", type=["mp3", "wav"])

    if audio_file is not None:
        # Transcription with Whisper model
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="en"
        )

        st.write("Transcription: ", transcription.text)

        # Analyze the transcription using OpenAI GPT-4o-mini
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI that can analyze user audio transcription and give a final summary to the student on where to improve and how to improve. Give your summary in english"},
                {"role": "user", "content": transcription.text}
            ]
        )

        st.write("Suggestions: ", response.choices[0].message.content)

def day_to_day_analysis():
    st.title("Day-to-Day Job Analysis")
    
    # Accept either file upload or direct text input
    input_method = st.radio("Choose input method:", ["Upload JD File", "Paste JD Text"])
    
    jd_text = ""
    if input_method == "Upload JD File":
        uploaded_jd = st.file_uploader("Upload Job Description (PDF/DOCX/TXT/JPG)", 
                                       type=["pdf", "txt", "docx", "jpg", "jpeg"])
        if uploaded_jd is not None:
            with st.spinner("Processing file..."):
                jd_text = read_file_content(uploaded_jd)
    else:
        jd_text = st.text_area("Paste Job Description Here:")
    
    if jd_text and st.button("Analyze Day-to-Day Life"):
        with st.spinner("Analyzing..."):
            prompt = f"""
            Based on this job description, provide a detailed analysis of what a typical day-to-day life would look like in this role. Include:

            1. Daily responsibilities and tasks
            2. Typical work schedule and time allocation
            3. Key interactions and collaborations
            4. Potential challenges and how to handle them
            5. Required skills in practice
            6. Work environment and culture indicators
            7. Career growth opportunities

            Job Description: {jd_text}
            """
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a career advisor with extensive knowledge of workplace dynamics and job roles."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            analysis = response.choices[0].message.content
            st.markdown("### Day-to-Day Analysis")
            st.write(analysis)

def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Choose a page", 
        ("Chat Page", "TTS Mode", "STT Mode", "JD Parser", "Cover Letter Generator", "Day-to-Day Analysis")
    )

    if page == "Chat Page":
        chat_page()
    elif page == "TTS Mode":
        tts_mode()
    elif page == "STT Mode":
        stt_mode()
    elif page == "JD Parser":
        jd_parser()
    elif page == "Cover Letter Generator":
        cover_letter_generator()
    elif page == "Day-to-Day Analysis":
        day_to_day_analysis()

if __name__ == "__main__":
    main()