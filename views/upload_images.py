import streamlit as st
import psycopg2
import pandas as pd
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

# Function to fetch data from the 'upload_images' table
def fetch_data_from_db():
    try:
        # Connect to PostgreSQL database
        conn = psycopg2.connect(**db_connection)
        query = "SELECT * FROM upload_images;"  # SQL query to fetch all data from 'upload_images' table
        df = pd.read_sql(query, conn)  # Using pandas to fetch data into a dataframe
        conn.close()  # Close the connection
        return df
    except psycopg2.OperationalError as e:
        st.error(f"OperationalError: Unable to connect to the database: {e}")
        return None
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# Function to insert a new image record into the 'upload_images' table
def insert_new_image(sno, image_filename, status, image_feedback):
    try:
        # Connect to PostgreSQL database
        conn = psycopg2.connect(**db_connection)
        cursor = conn.cursor()
        query = """
        INSERT INTO upload_images (sno, image, status, image_feedback)
        VALUES (%s, %s, %s, %s);
        """
        cursor.execute(query, (sno, image_filename, status, image_feedback))
        conn.commit()  # Commit the transaction
        conn.close()  # Close the connection
        st.success("New image record added successfully!")
    except Exception as e:
        st.error(f"Error inserting new image record: {e}")
# Streamlit app layout
st.title("Upload Images - Data from Database")

# Section to Add New Image
st.subheader("Add New Image Record")

# Placeholder to display uploaded images
uploaded_image_placeholder = st.empty()

# Streamlit form for adding a new image record
with st.form(key="new_image_form"):
    sno = st.text_input("Serial No.")
    status = st.selectbox("Status", ["APPROVED", "REJECTED"])
    image_feedback = st.slider("Image Feedback (Integer)", min_value=0,max_value=10, value=0, step=1)

    # Image upload
    uploaded_file = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png"])

    submit_button = st.form_submit_button("Add Image Record")

    # If the form is submitted, handle the image upload
    if submit_button:
        if sno and uploaded_file:  # Check for required fields
            if sno.isdigit():
                image_filename = f"{uploaded_file.name}"
                image_path = os.path.join(UPLOAD_DIR, image_filename)
                with open(image_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                insert_new_image(int(sno), image_filename, status, image_feedback)
                # uploaded_image_placeholder.image(image_path, caption="Uploaded Image", use_container_width=True)
                uploaded_image_placeholder.image(image_path, caption="Uploaded Image", use_column_width=True)

            else:
                st.warning("Serial No. must be a valid number.")
        else:
            st.warning("Please fill in all required fields and upload an image.")

# Fetch and display data from the 'upload_images' table at the bottom
st.subheader("Existing Data")
df = fetch_data_from_db()
if df is not None:
    st.write("Data from the 'upload_images' table:")
    st.dataframe(df)  # Display data in a table format
else:
    st.write("No data available.")