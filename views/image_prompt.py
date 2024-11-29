import streamlit as st
import psycopg2
import os
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

# Database Functions
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

def update_image(sno, image_filename, image_feedback=0, image_status="Pending"):
    try:
        conn = psycopg2.connect(**db_connection)
        cursor = conn.cursor()
        query = """
        UPDATE upload_images
        SET image = %s, status = %s, image_feedback = %s
        WHERE sno = %s;
        """
        cursor.execute(query, (image_filename, image_status, image_feedback, sno))
        conn.commit()
        conn.close()
        st.success(f"Image record for Serial No. {sno} updated successfully!")
    except Exception as e:
        st.error(f"Error updating image record: {e}")

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

def update_prompt(sno, old_prompt, new_prompt):
    try:
        conn = psycopg2.connect(**db_connection)
        cursor = conn.cursor()
        query = """
        UPDATE upload_prompts
        SET image_prompts = %s
        WHERE sno = %s AND image_prompts = %s;
        """
        cursor.execute(query, (new_prompt, sno, old_prompt))
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        if rows_affected > 0:
            st.success(f"Prompt updated successfully!")
            return True
        else:
            st.warning("Prompt not found or update failed.")
            return False
    except Exception as e:
        st.error(f"Error updating prompt: {e}")
        return False

def delete_prompt(sno, prompt):
    try:
        conn = psycopg2.connect(**db_connection)
        cursor = conn.cursor()
        query = """
        DELETE FROM upload_prompts
        WHERE sno = %s AND image_prompts = %s;
        """
        cursor.execute(query, (sno, prompt))
        conn.commit()
        rows_affected = cursor.rowcount
        conn.close()
        if rows_affected > 0:
            st.success(f"Prompt deleted successfully!")
            return True
        else:
            st.warning("Prompt not found or deletion failed.")
            return False
    except Exception as e:
        st.error(f"Error deleting prompt: {e}")
        return False

def get_image_details(sno):
    try:
        conn = psycopg2.connect(**db_connection)
        cursor = conn.cursor()
        query = "SELECT image, status FROM upload_images WHERE sno = %s;"
        cursor.execute(query, (sno,))
        result = cursor.fetchone()
        conn.close()
        return result
    except Exception as e:
        st.error(f"Error retrieving image details: {e}")
        return None

def get_prompts(sno):
    try:
        conn = psycopg2.connect(**db_connection)
        cursor = conn.cursor()
        query = "SELECT image_prompts FROM upload_prompts WHERE sno = %s;"
        cursor.execute(query, (sno,))
        prompts = cursor.fetchall()
        conn.close()
        return [prompt[0] for prompt in prompts]
    except Exception as e:
        st.error(f"Error retrieving prompts: {e}")
        return []

def check_serial_exists(sno):
    try:
        conn = psycopg2.connect(**db_connection)
        cursor = conn.cursor()
        query = "SELECT COUNT(*) FROM upload_images WHERE sno = %s;"
        cursor.execute(query, (sno,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    except Exception as e:
        st.error(f"Error checking serial number: {e}")
        return False

# Streamlit Layout
st.title("Image and Prompt Management")

# Image Upload Section
with st.form(key="image_upload_form"):
    st.subheader("Add or Update Image")
    sno = st.text_input("Serial No.", placeholder="Enter a unique serial number")
    uploaded_file = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png"])
    image_status = st.selectbox("Image Status", ["Pending", "Approved", "Rejected"])
    image_feedback = st.number_input("Feedback Score (0-5)", min_value=0, max_value=5, step=1)
    submit_image = st.form_submit_button("Upload/Update Image")

    if sno and sno.isdigit():
        sno = int(sno)
        if submit_image and uploaded_file:
            image_filename = f"{uploaded_file.name}_{sno}"
            image_path = os.path.join(UPLOAD_DIR, image_filename)
            with open(image_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            if check_serial_exists(sno):
                update_image(sno, image_filename, image_feedback, image_status)
            else:
                insert_image(sno, image_filename, image_feedback, image_status)

            st.image(image_path, caption=f"Uploaded/Updated Image for Serial No. {sno}")

# Prompt Management Section
st.subheader("Prompt Management")
management_option = st.selectbox("Choose Action:", ["Add Prompts", "Edit Prompts", "Delete Prompts"])
prompt_sno = st.text_input("Serial No. for Prompts", placeholder="Enter Serial No.")

if prompt_sno and prompt_sno.isdigit():
    prompt_sno = int(prompt_sno)

    if management_option == "Add Prompts":
        prompts = st.text_area("Enter Prompts (one per line)")
        if st.button("Add Prompts"):
            for prompt in prompts.splitlines():
                if prompt.strip():
                    insert_prompt(prompt_sno, prompt.strip())

    elif management_option == "Edit Prompts":
        existing_prompts = get_prompts(prompt_sno)
        for prompt in existing_prompts:
            new_prompt = st.text_input(f"Edit Prompt: {prompt}", value=prompt)
            if st.button(f"Update {prompt}"):
                update_prompt(prompt_sno, prompt, new_prompt)

    elif management_option == "Delete Prompts":
        existing_prompts = get_prompts(prompt_sno)
        for prompt in existing_prompts:
            if st.button(f"Delete {prompt}"):
                delete_prompt(prompt_sno, prompt)
