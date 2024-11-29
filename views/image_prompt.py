import streamlit as st
import psycopg2
import os
import pandas as pd
from pathlib import Path

# Database connection configuration
db_connection = {
    "host": "34.93.64.44",
    "port": "5432",
    "dbname": "genai",
    "user": "postgres",
    "password": "postgres-genai"
}

# Directory to save uploaded images
UPLOAD_DIR = "uploaded_images"
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist

# Function to insert the image record into the database
def insert_image(sno, image_filename, image_feedback=0, image_status="Pending"):
    try:
        conn = psycopg2.connect(**db_connection)
        cursor = conn.cursor()
        query = """
        INSERT INTO upload_images (sno, image, status, image_feedback)
        VALUES (%s, %s, %s, %s);
        """
        cursor.execute(query, (sno, image_filename, image_status, image_feedback))
        conn.commit()
        conn.close()
        st.success(f"Image record for Serial No. {sno} added successfully!")
    except Exception as e:
        st.error(f"Error inserting image record: {e}")

# Function to insert prompts into the database
def insert_prompt(sno, image_prompt, prompt_feedback=0, prompt_status="Pending"):
    try:
        conn = psycopg2.connect(**db_connection)
        cursor = conn.cursor()
        query = """
        INSERT INTO upload_prompts (sno, prompt_feedback, image_prompts, status)
        VALUES (%s, %s, %s, %s);
        """
        cursor.execute(query, (sno, prompt_feedback, image_prompt, prompt_status))
        conn.commit()
        conn.close()
        st.success(f"Prompt added successfully for Serial No. {sno}!")
    except Exception as e:
        st.error(f"Error inserting prompt: {e}")

# Function to check if Serial No. exists in the database
def check_serial_exists(sno):
    try:
        conn = psycopg2.connect(**db_connection)
        cursor = conn.cursor()
        query = "SELECT COUNT(*) FROM upload_images WHERE sno = %s;"
        cursor.execute(query, (sno,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0  # Return True if Serial No. exists
    except Exception as e:
        st.error(f"Error checking serial number: {e}")
        return False

# Streamlit app layout
st.title("Upload Image with Multiple Prompts")

# Section for adding an image
with st.form(key="image_upload_form"):
    st.subheader("Add Image")
    sno = st.text_input("Serial No.", placeholder="Enter a unique serial number")
    uploaded_file = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png"])
    submit_image = st.form_submit_button("Upload Image")

    if submit_image:
        if sno and sno.isdigit() and uploaded_file:
            sno = int(sno)  # Convert Serial No to integer
            
            # Check if Serial No. already exists
            if check_serial_exists(sno):
                st.warning(f"Serial No. {sno} has already been used. Please use a different Serial No.")
            else:
                # Save the uploaded image
                image_filename = f"{uploaded_file.name}_{sno}"
                image_path = os.path.join(UPLOAD_DIR, image_filename)
                with open(image_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Insert the image record into the database
                insert_image(sno=sno, image_filename=image_filename)

                # Display the uploaded image
                st.image(image_path, caption="Uploaded Image", use_container_width=True)
        else:
            st.warning("Please fill in all required fields and upload an image.")

# Section for adding multiple prompts for the same image
st.subheader("Add Prompts for Uploaded Image")
prompt_sno = st.text_input("Serial No. to Add Prompts", placeholder="Enter the Serial No. of the uploaded image")
if prompt_sno and prompt_sno.isdigit():
    prompt_sno = int(prompt_sno)
    
    # Check if the Serial No. exists in the image records before allowing prompt input
    if not check_serial_exists(prompt_sno):
        st.warning(f"Serial No. {prompt_sno} does not exist in the database. Please upload an image first.")
    else:
        with st.form(key="prompt_form"):
            prompts = st.text_area("Enter Prompts (one per line)", placeholder="Enter multiple prompts separated by new lines")
            submit_prompts = st.form_submit_button("Add Prompts")

            if submit_prompts:
                if prompts:
                    # Add each prompt into the database
                    for prompt in prompts.splitlines():
                        if prompt.strip():  # Ensure non-empty prompts are added
                            insert_prompt(sno=prompt_sno, image_prompt=prompt.strip())
                else:
                    st.warning("Please enter at least one prompt.")
