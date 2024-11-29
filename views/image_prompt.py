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

# Function to update the image record in the database
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

# Function to insert the prompt into the database
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

# Function to get the image details for a given Serial No.
def get_image_details(sno):
    try:
        conn = psycopg2.connect(**db_connection)
        cursor = conn.cursor()
        query = "SELECT image, status FROM upload_images WHERE sno = %s;"
        cursor.execute(query, (sno,))
        result = cursor.fetchone()
        conn.close()
        return result  # Returns a tuple (image_filename, status)
    except Exception as e:
        st.error(f"Error retrieving image details: {e}")
        return None

# Function to get prompts for a given Serial No.
def get_prompts(sno):
    try:
        conn = psycopg2.connect(**db_connection)
        cursor = conn.cursor()
        query = "SELECT image_prompts FROM upload_prompts WHERE sno = %s;"
        cursor.execute(query, (sno,))
        prompts = cursor.fetchall()
        conn.close()
        return [prompt[0] for prompt in prompts]  # Returns a list of prompts
    except Exception as e:
        st.error(f"Error retrieving prompts: {e}")
        return []

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

# Section for adding or editing an image
with st.form(key="image_upload_form"):
    st.subheader("Add or Edit Image")
    sno = st.text_input("Serial No.", placeholder="Enter a unique serial number")
    uploaded_file = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png"])
    submit_image = st.form_submit_button("Upload/Update Image")

    if sno and sno.isdigit():
        sno = int(sno)  # Convert Serial No to integer

        # If Serial No. exists, show existing image and prompts
        if check_serial_exists(sno):
            st.write(f"Serial No. {sno} already exists. You can update the image or prompts.")
            image_details = get_image_details(sno)
            if image_details:
                image_path = os.path.join(UPLOAD_DIR, image_details[0])
                st.write(f"Image path: {image_path}")
                if os.path.exists(image_path):
                    st.image(image_path, caption="Existing Image", use_container_width=True)
                else:
                    st.error(f"Image file not found at {image_path}")
            
            # Display existing prompts
            prompts = get_prompts(sno)
            if prompts:
                st.write("Current Prompts:")
                for prompt in prompts:
                    st.write(f"- {prompt}")

        if submit_image:
            # If a file is uploaded, either add new or update existing image
            if uploaded_file:
                image_filename = f"{uploaded_file.name}_{sno}"
                image_path = os.path.join(UPLOAD_DIR, image_filename)
                with open(image_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.write(f"Image uploaded successfully at {image_path}")
                insert_image(sno, image_filename)

# New function to update an existing prompt
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

# New function to delete a specific prompt
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

def prompt_management_section():
    st.subheader("Prompt Management")
    management_option = st.selectbox("Choose an action:", 
        ["Add Prompts", "Edit Existing Prompts", "Delete Prompts"])

    prompt_sno = st.text_input("Serial No.", placeholder="Enter the Serial No. of the uploaded image")

    # Initialize variables to store existing prompts
    existing_prompts = []

    if prompt_sno and prompt_sno.isdigit():
        prompt_sno = int(prompt_sno)
        
        # Check if the Serial No. exists in the image records
        if not check_serial_exists(prompt_sno):
            st.warning(f"Serial No. {prompt_sno} does not exist in the database. Please upload an image first.")
        else:
            # Retrieve existing prompts
            existing_prompts = get_prompts(prompt_sno)

    if management_option == "Add Prompts":
        with st.form(key="add_prompt_form"):
            prompts = st.text_area(
                "Enter New Prompts (one per line)", 
                placeholder="Enter multiple prompts separated by new lines"
            )
            submit_prompts = st.form_submit_button("Add Prompts")
            
            if submit_prompts:
                if prompts:
                    new_prompts_added = False
                    for prompt in prompts.splitlines():
                        if prompt.strip():
                            insert_prompt(sno=prompt_sno, image_prompt=prompt.strip())
                            new_prompts_added = True
                    
                    if new_prompts_added:
                        st.success("Prompts added successfully!")
                        prompts = ""
                else:
                    st.warning("Please enter at least one prompt.")

    elif management_option == "Edit Existing Prompts":
        if not existing_prompts:
            st.warning("No existing prompts to edit.")
        else:
            st.write("Existing Prompts:")
            for idx, prompt in enumerate(existing_prompts):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{idx + 1}. {prompt}")
                with col2:
                    edit_prompt = st.text_input(f"Edit Prompt {idx + 1}", value=prompt)
                    update_button = st.button(f"Update {idx + 1}")
                    
                    if update_button:
                        if update_prompt(sno=prompt_sno, old_prompt=prompt, new_prompt=edit_prompt):
                            st.experimental_rerun()  # Rerun to update displayed prompts

    elif management_option == "Delete Prompts":
        if not existing_prompts:
            st.warning("No prompts to delete.")
        else:
            st.write("Existing Prompts:")
            for idx, prompt in enumerate(existing_prompts):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"{idx + 1}. {prompt}")
                with col2:
                    delete_button = st.button(f"Delete {idx + 1}", key=f"delete_{idx}")
                    
                    if delete_button:
                        if delete_prompt(sno=prompt_sno, prompt=prompt):
                            st.experimental_rerun()  # Rerun to update displayed prompts

# Call the prompt management section to enable prompt addition, editing, or deletion
prompt_management_section()
