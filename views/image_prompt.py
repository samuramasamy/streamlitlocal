import os
import json
import tempfile
import streamlit as st
from PIL import Image
from io import BytesIO
from google.cloud import storage
from sqlalchemy import create_engine, text
import psycopg2
import pandas as pd
from pathlib import Path

# Streamlit app title
st.title("Fine-tuning GenAI Project")

# Database connection configuration
db_connection = {
    "host": "34.93.64.44",
    "port": "5432",
    "dbname": "genai",
    "user": "postgres",
    "password": "postgres-genai"
}

# Set up session state
if "image_number" not in st.session_state:
    st.session_state.image_number = 1
if "navigation_clicked" not in st.session_state:
    st.session_state.navigation_clicked = False

# Load Google Cloud Storage credentials
gcs_credentials = json.loads(st.secrets["database"]["credentials"])
with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.json') as temp_file:
    json.dump(gcs_credentials, temp_file)
    temp_file_path = temp_file.name
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_file_path

# Initialize Google Cloud Storage client and bucket
client = storage.Client()
bucket_name = 'open-to-public-rw-sairam'
bucket = client.get_bucket(bucket_name)

# Connect to PostgreSQL database using SQLAlchemy
connection_string = st.secrets["database"]["connection_string"]
engine = create_engine(connection_string)

# Function to upload an image to Google Cloud Storage
def upload_image_to_gcs(file_path, destination_blob_name):
    try:
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(file_path)
        st.success(f"File '{file_path}' uploaded to Google Cloud Storage as '{destination_blob_name}'.")
    except Exception as e:
        st.error(f"Error uploading image to GCS: {e}")

# Function to check if an image exists in the bucket
def image_exists_in_bucket(bucket, image_path):
    blob = bucket.blob(image_path)
    try:
        blob.reload()
        return True
    except Exception:
        return False

# Function to insert image metadata into PostgreSQL database
def insert_image_metadata(sno, image_filename, status=None, image_feedback=None, gcs_url=None):
    try:
        conn = psycopg2.connect(**db_connection)
        cursor = conn.cursor()
        query = """
        INSERT INTO upload_images (sno, image, image_path, status, image_feedback)
        VALUES (%s, %s, %s, %s, %s);
        """
        cursor.execute(query, (sno, image_filename, gcs_url, status, image_feedback))
        conn.commit()
        cursor.close()
        conn.close()
        st.success("Image metadata inserted successfully.")
    except Exception as e:
        st.error(f"Error inserting metadata: {e}")
       
# Function to update image metadata in PostgreSQL database
def update_image_metadata(sno, image_filename, status=None, image_feedback=None, gcs_url=None):
    try:
        conn = psycopg2.connect(**db_connection)
        cursor = conn.cursor()
        query = """
        UPDATE upload_images
        SET image = %s, image_path = %s, status = %s, image_feedback = %s
        WHERE sno = %s;
        """
        cursor.execute(query, (image_filename, gcs_url, status, image_feedback, sno))
        conn.commit()
        cursor.close()
        conn.close()
        st.success(f"Image metadata for Serial No. {sno} updated successfully.")
    except Exception as e:
        st.error(f"Error updating metadata: {e}")

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

# Function to get the next available Serial Number
def get_next_serial_number():
    query = text("SELECT COALESCE(MAX(sno), 0) + 1 AS next_sno FROM upload_images")
    with engine.connect() as conn:
        result = conn.execute(query).scalar()
    return result

# Create two columns for upload and update
col1, col2 = st.columns(2)

with col1:
    # Upload New Image Section
    st.subheader("Upload New Image")
    with st.form(key="new_image_form"):
        new_uploaded_file = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png"], key="new_uploaded_file")
        new_submit_button = st.form_submit_button("Upload New Image")

        if new_submit_button:
            if new_uploaded_file:
                try:
                    # Get the next auto-incremental serial number from the database
                    next_sno = get_next_serial_number()
                    unique_filename = f"image{next_sno}.jpg"
                   
                    # Prepare local and GCS paths
                    local_image_path = os.path.join("uploaded_images", unique_filename)
                    gcs_image_path = f"Upload_images/Moodboard Images/{unique_filename}"
                   
                    # Ensure local directory exists
                    Path("uploaded_images").mkdir(parents=True, exist_ok=True)
                   
                    # Save the image locally
                    with open(local_image_path, "wb") as f:
                        f.write(new_uploaded_file.getbuffer())

                    try:
                        # Upload image to Google Cloud Storage
                        upload_image_to_gcs(local_image_path, gcs_image_path)

                        # Construct the GCS URL for the image
                        gcs_url = f"https://storage.cloud.google.com/{bucket_name}/{gcs_image_path}"

                        # Insert metadata into the database, including the GCS URL
                        insert_image_metadata(next_sno, unique_filename, status="UPLOADED", gcs_url=gcs_url)
                       
                        st.success(f"New image uploaded successfully with Serial No. {next_sno}")
   
                        # Display the uploaded image
                        st.image(local_image_path, caption=f"Uploaded Image (Serial No. {next_sno})", use_container_width=True)

                    except Exception as e:
                        st.error(f"Error uploading image: {e}")
                        # Remove local file if upload fails
                        os.remove(local_image_path)

                except Exception as e:
                    st.error(f"Error processing image: {e}")
            else:
                st.warning("Please select an image file to upload.")

with col2:
    # Update Existing Image Section
    st.subheader("Update Existing Image")
    with st.form(key="update_image_form"):
        update_sno = st.text_input("Serial No. (Existing)", key="update_sno")
        update_uploaded_file = st.file_uploader("Choose an image to update", type=["jpg", "jpeg", "png"], key="update_uploaded_file")
        update_submit_button = st.form_submit_button("Update Existing Image")

        if update_submit_button:
            if update_sno and update_uploaded_file:
                if update_sno.isdigit():
                    sno_int = int(update_sno)

                    try:
                        # Check if the serial number exists in the database
                        def check_sno_exists(sno):
                            query = text("SELECT 1 FROM upload_images WHERE sno = :sno")
                            with engine.connect() as conn:
                                return conn.execute(query, {"sno": sno}).fetchone() is not None

                        if not check_sno_exists(sno_int):
                            st.warning(f"Serial No. {sno_int} does not exist. Use the Upload New Image section.")
                        else:
                            # Generate the unique filename based on `sno`
                            unique_filename = f"image{sno_int}.jpg"
                            image_path = os.path.join("uploaded_images", unique_filename)
                            Path("uploaded_images").mkdir(parents=True, exist_ok=True)

                            # Save the new image locally
                            with open(image_path, "wb") as f:
                                f.write(update_uploaded_file.getbuffer())

                            # Prepare the GCS image path for the updated image
                            gcs_image_path = f"Upload_images/Moodboard Images/{unique_filename}"

                            # Upload image to Google Cloud Storage
                            upload_image_to_gcs(image_path, gcs_image_path)

                            # Generate the new GCS URL
                            gcs_url = f"https://storage.cloud.google.com/{bucket_name}/{gcs_image_path}"

                            # Update the image metadata in the database, including the new GCS URL
                            update_image_metadata(sno_int, unique_filename, gcs_url=gcs_url)

                            st.success(f"Image with Serial No. {sno_int} updated successfully.")

                            # Display the uploaded image
                            st.image(image_path, caption="Updated Image", use_container_width=True)

                    except Exception as e:
                        st.error(f"Error updating image: {e}")
                else:
                    st.warning("Serial No. must be a valid number.")
            else:
                st.warning("Please fill in all required fields for image update.")

# Display data from the 'upload_images' table
def fetch_data_from_db():
    try:
        conn = psycopg2.connect(**db_connection)
        query = "SELECT * FROM upload_images;"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

# st.subheader("Existing Data")
# df = fetch_data_from_db()
# if df is not None:
#     st.write("Data from the 'upload_images' table:")
#     st.dataframe(df)
# else:
#     st.write("No data available.")



# Image navigation and prompt management
st.subheader("Image Navigation & Prompt Management")
col1, col2, col3 = st.columns([1, 2, 3])
with col1:
    st.markdown(f"<h4 style='text-align: center'>Image {st.session_state.image_number}</h4>", unsafe_allow_html=True)

with col3:
    # Input for image number
    image_number_input = st.text_input(
        "",
        value=str(st.session_state.image_number),
        placeholder="Enter image number",
        key="image_number_input",
        on_change=lambda: update_image_number()
    )

# Function to update the current image number
def update_image_number():
    try:
        input_number = int(st.session_state.image_number_input)
        # No upper limit check, accept any integer
        st.session_state.image_number = input_number
    except ValueError:
        st.error("Please enter a valid integer.")
       
# Display the selected image with support for jpg, jpeg, and png formats
supported_formats = ["jpg", "jpeg", "png"]
image_found = False  # Flag to track if the image is found

for ext in supported_formats:
    image_name = f"image{st.session_state.image_number}.{ext}"
    image_path = os.path.join("Upload_images/Moodboard Images/", image_name)

    try:
        if image_exists_in_bucket(bucket, image_path):  # Check if the image exists in the bucket
            blob = bucket.blob(image_path)
            image_data = blob.download_as_bytes()  # Download the image data
            image = Image.open(BytesIO(image_data))  # Open the image
            # st.image(image, caption=f"Image {st.session_state.image_number}.{ext}", use_container_width=True)

        col1, col2, col3 = st.columns([1, 2, 3])
        with col2:
            st.image(
            image,
            caption=f"Image {st.session_state.image_number}",
            width=250  # Adjust this value to set the image width
        )
            image_found = True  # Mark the image as found
            break  # Exit the loop as we found the image
    except Exception as e:
        st.error(f"Error loading image: {e}")  # Log error and continue checking other formats

# If no image is found after trying all formats, display an error
if not image_found:
    st.error(f"Image {st.session_state.image_number} not found in the bucket with supported formats ({', '.join(supported_formats)}).")



st.subheader("Prompt Management")
management_option = st.selectbox("Choose an action:",
    ["Add Prompts", "Edit Existing Prompts", "Delete Prompts"])

# Use the current image number as the serial number
prompt_sno = st.session_state.image_number

#Function to check if Serial No. exists in the database
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



#Function to check if Serial No. exists in the database
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


# Check if the Serial No. exists in the image records
if not check_serial_exists(prompt_sno):
    st.warning(f"Serial No. {prompt_sno} does not exist in the database. Please upload an image first.")
else:
    # Retrieve existing prompts
    existing_prompts = get_prompts(prompt_sno)

    if management_option == "Add Prompts":
        # Use st.form to prevent multiple submissions
        with st.form(key="add_prompt_form"):
            prompts = st.text_area(
                "Enter New Prompts (one per line)",
                placeholder="Enter multiple prompts separated by new lines",
                height=150  # Increased height for better visibility
            )
            submit_prompts = st.form_submit_button("Add Prompts")
    
            if submit_prompts:
                if prompts:
                    # Add each prompt into the database
                    new_prompts_added = False
                    duplicate_prompts = []  # Keep track of duplicate prompts
                    new_valid_prompts = []  # Track successfully added prompts
    
                    for prompt in prompts.splitlines():
                        prompt = prompt.strip()
                        if prompt:  # Ensure non-empty prompts are processed
                            # Check if the prompt already exists
                            if prompt in existing_prompts:
                                duplicate_prompts.append(prompt)
                            else:
                                insert_prompt(sno=prompt_sno, image_prompt=prompt)
                                new_prompts_added = True
                                new_valid_prompts.append(prompt)
                    
    
                    if new_prompts_added:
                        st.success(f"Successfully added {len(new_valid_prompts)} new prompt(s)!")
                        # Create a visual display of newly added prompts
                        st.markdown("### Newly Added Prompts:")
                        for new_prompt in new_valid_prompts:
                            st.markdown(f"""
                            <div style='border: 1px solid #4CAF50; border-radius: 5px; padding: 10px; margin-bottom: 10px; background-color: #E8F5E9;'>
                                ✅ {new_prompt}
                            
                            """, unsafe_allow_html=True)
    
                    if duplicate_prompts:
                        st.warning(f"The following prompts already exist and were not added: {', '.join(duplicate_prompts)}")
                else:
                    st.warning("Please enter at least one prompt.")
        # Display existing prompts with more details
        st.write("### Existing Prompts:")
        if existing_prompts:
            for idx, prompt in enumerate(existing_prompts, 1):
                # Create a card-like display for each prompt
                st.markdown(f"""
                <div style='border: 1px solid #e0e0e0; border-radius: 5px; padding: 10px; margin-bottom: 10px;'>
                    <strong>Prompt {idx}:</strong> {prompt}
                """, unsafe_allow_html=True)
        else:
            st.info("No existing prompts for this image.")
    

   
    elif management_option == "Edit Existing Prompts":
        if not existing_prompts:
            st.warning("No existing prompts to edit.")
        else:
            st.write("Existing Prompts:")
            for idx, prompt in enumerate(existing_prompts):
                
                    edited_prompt = st.text_area(
                        f"Edit Prompt {idx + 1}",
                        value=prompt,
                        key=f"edit_{prompt_sno}_{idx}",
                        height = 200
                        
                    )
               
                    if st.button(f"Update", key=f"update_{prompt_sno}_{idx}"):
                        if edited_prompt and edited_prompt != prompt:
                            update_prompt(prompt_sno, prompt, edited_prompt)
                            st.success("Prompt updated successfully!")
                            # Trigger a rerun to refresh the view
                            st.rerun()
   
    elif management_option == "Delete Prompts":
        if not existing_prompts:
            st.warning("No existing prompts to delete.")
        else:
            st.write("Select Prompts to Delete:")
            prompts_to_delete = []
            for idx, prompt in enumerate(existing_prompts):
                if st.checkbox(prompt, key=f"delete_{prompt_sno}_{idx}"):
                    prompts_to_delete.append(prompt)
            if st.button("Confirm Deletion"):
                if prompts_to_delete:
                    for prompt in prompts_to_delete:
                        delete_prompt(prompt_sno, prompt)
                    st.success("Selected prompts deleted successfully!")
                    # Trigger a rerun to refresh the view
                    st.rerun()
                else:
                    st.warning("No prompts selected for deletion.")

