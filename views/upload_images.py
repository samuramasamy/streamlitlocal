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

# Define the maximum image number for navigation
MAX_IMAGE_NUMBER = 100  # Adjust as needed

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
def insert_image_metadata(sno, image_filename, status=None, image_feedback=None):
    try:
        conn = psycopg2.connect(**db_connection)
        cursor = conn.cursor()
        query = """
        INSERT INTO upload_images (sno, image, status, image_feedback)
        VALUES (%s, %s, %s, %s);
        """
        cursor.execute(query, (sno, image_filename, status, image_feedback))
        conn.commit()
        cursor.close()
        conn.close()
        st.success("Image metadata inserted successfully.")
    except Exception as e:
        st.error(f"Error inserting metadata: {e}")

# Function to fetch data from PostgreSQL database
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

# Streamlit form for uploading a new image
st.subheader("Upload New Image")
uploaded_image_placeholder = st.empty()

with st.form(key="new_image_form"):
    sno = st.text_input("Serial No.")
    uploaded_file = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png"])
    submit_button = st.form_submit_button("Add Image Record")

    if submit_button:
        if sno and uploaded_file:
            if sno.isdigit():
                # Save the image locally first
                image_filename = f"{uploaded_file.name}"
                image_path = os.path.join("uploaded_images", image_filename)
                Path("uploaded_images").mkdir(parents=True, exist_ok=True)
                with open(image_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                # Upload image to Google Cloud Storage
                upload_image_to_gcs(image_path, f"Upload_images/Moodboard Images/{image_filename}")

                # Insert metadata into the database
                insert_image_metadata(int(sno), image_filename)

                # Display the uploaded image
                uploaded_image_placeholder.image(image_path, caption="Uploaded Image", use_container_width=True)
            else:
                st.warning("Serial No. must be a valid number.")
        else:
            st.warning("Please fill in all required fields and upload an image.")

# Display data from the 'upload_images' table
st.subheader("Existing Data")
df = fetch_data_from_db()
if df is not None:
    st.write("Data from the 'upload_images' table:")
    st.dataframe(df)
else:
    st.write("No data available.")

# Image navigation
st.subheader("Image Navigation")
col1, col2, col3 = st.columns([1, 2, 3])
with col1:
    st.markdown(f"<h4 style='text-align: center'>Image {st.session_state.image_number}</h4>", unsafe_allow_html=True)

with col3:
    image_number_input = st.text_input(
        "",
        value=str(st.session_state.image_number),
        placeholder="Enter image number (1-100)",
        key="image_number_input",
        on_change=lambda: update_image_number()
    )

# Function to update the current image number
def update_image_number():
    try:
        input_number = int(st.session_state.image_number_input)
        if input_number < 1 or input_number > MAX_IMAGE_NUMBER:
            st.error(f"Please enter a number between 1 and {MAX_IMAGE_NUMBER}.")
        else:
            st.session_state.image_number = input_number
    except ValueError:
        st.error("Please enter a valid integer.")

# Display the selected image
image_name = f"image{st.session_state.image_number}.jpg"
image_path = os.path.join("Upload_images/Moodboard Images/", image_name)

try:
    if image_exists_in_bucket(bucket, image_path):
        blob = bucket.blob(image_path)
        image_data = blob.download_as_bytes()
        image = Image.open(BytesIO(image_data))
        st.image(image, caption=f"Image {st.session_state.image_number}", use_container_width=True)
    else:
        st.error(f"Image {st.session_state.image_number} not found.")
except Exception as e:
    st.error(f"Error loading image: {e}")



# import streamlit as st
# import psycopg2
# import pandas as pd
# import os
# from pathlib import Path

# # Database connection configuration
# db_connection = {
#     "host": "34.93.64.44",
#     "port": "5432",
#     "dbname": "genai",
#     "user": "postgres",
#     "password": "postgres-genai"
# }

# # Directory to save uploaded images
# UPLOAD_DIR = "uploaded_images"
# Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)  # Create directory if it doesn't exist

# # Function to fetch data from the 'upload_images' table
# def fetch_data_from_db():
#     try:
#         # Connect to PostgreSQL database
#         conn = psycopg2.connect(**db_connection)
#         query = "SELECT * FROM upload_images;"  # SQL query to fetch all data from 'upload_images' table
#         df = pd.read_sql(query, conn)  # Using pandas to fetch data into a dataframe
#         conn.close()  # Close the connection
#         return df
#     except psycopg2.OperationalError as e:
#         st.error(f"OperationalError: Unable to connect to the database: {e}")
#         return None
#     except Exception as e:
#         st.error(f"Error: {e}")
#         return None

# # Function to insert a new image record into the 'upload_images' table
# def insert_new_image(sno, image_filename, status, image_feedback):
#     try:
#         # Connect to PostgreSQL database
#         conn = psycopg2.connect(**db_connection)
#         cursor = conn.cursor()
#         query = """
#         INSERT INTO upload_images (sno, image, status, image_feedback)
#         VALUES (%s, %s, %s, %s);
#         """
#         cursor.execute(query, (sno, image_filename, status, image_feedback))
#         conn.commit()  # Commit the transaction
#         conn.close()  # Close the connection
#         st.success("New image record added successfully!")
#     except Exception as e:
#         st.error(f"Error inserting new image record: {e}")
# # Streamlit app layout
# st.title("Upload Images - Data from Database")

# # Section to Add New Image
# st.subheader("Add New Image Record")

# # Placeholder to display uploaded images
# uploaded_image_placeholder = st.empty()

# # Streamlit form for adding a new image record
# with st.form(key="new_image_form"):
#     sno = st.text_input("Serial No.")
#     status = st.selectbox("Status", ["APPROVED", "REJECTED"])
#     image_feedback = st.slider("Image Feedback (Integer)", min_value=0,max_value=10, value=0, step=1)

#     # Image upload
#     uploaded_file = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png"])

#     submit_button = st.form_submit_button("Add Image Record")

#     # If the form is submitted, handle the image upload
#     if submit_button:
#         if sno and uploaded_file:  # Check for required fields
#             if sno.isdigit():
#                 image_filename = f"{uploaded_file.name}"
#                 image_path = os.path.join(UPLOAD_DIR, image_filename)
#                 with open(image_path, "wb") as f:
#                     f.write(uploaded_file.getbuffer())
#                 insert_new_image(int(sno), image_filename, status, image_feedback)
#                 # uploaded_image_placeholder.image(image_path, caption="Uploaded Image", use_container_width=True)
#                 uploaded_image_placeholder.image(image_path, caption="Uploaded Image", use_column_width=True)

#             else:
#                 st.warning("Serial No. must be a valid number.")
#         else:
#             st.warning("Please fill in all required fields and upload an image.")

# # Fetch and display data from the 'upload_images' table at the bottom
# st.subheader("Existing Data")
# df = fetch_data_from_db()
# if df is not None:
#     st.write("Data from the 'upload_images' table:")
#     st.dataframe(df)  # Display data in a table format
# else:
#     st.write("No data available.")
