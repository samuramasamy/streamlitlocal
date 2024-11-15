import streamlit as st
import os
from PIL import Image
import pandas as pd
from sqlalchemy import create_engine, text
from google.cloud import storage
from io import BytesIO
import json
import tempfile

# Title of the page
st.title("Fine-tuning GenAI Project")

# Initialize session state variables
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
client = storage.Client()

# Specify your bucket name
bucket_name = 'open-to-public-rw-sairam'
bucket = client.get_bucket(bucket_name)

# Connect to the PostgreSQL database
connection_string = st.secrets["database"]["connection_string"]
engine = create_engine(connection_string)

# Function to check if image exists in bucket
def image_exists_in_bucket(bucket, image_path):
    blob = bucket.blob(image_path)
    try:
        blob.reload()
        return True
    except Exception:
        return False

# Navigation callback functions
def go_back():
    if st.session_state.image_number > 1 and not st.session_state.navigation_clicked:
        st.session_state.image_number -= 1
        st.session_state.navigation_clicked = True

def go_next():
    if not st.session_state.navigation_clicked:
        next_image = f"image{st.session_state.image_number + 1}.jpg"
        next_image_path = os.path.join("Prompts/Final images moodboard/", next_image)
        if image_exists_in_bucket(bucket, next_image_path):
            st.session_state.image_number += 1
            st.session_state.navigation_clicked = True

# Function to fetch prompts from PostgreSQL based on image number
def get_prompts(image_number):
    query = f"""
    SELECT serial_nos, sno, image_prompts, 
           COALESCE(prompt_feedback, 'GOOD') AS prompt_feedback
    FROM prompts
    WHERE sno = {image_number}
    ORDER BY serial_nos;
    """
    prompts_df = pd.read_sql(query, engine)
    return prompts_df

# Function to fetch image feedback
def get_image_feedback(image_name):
    query = text("""
    SELECT COALESCE(image_feedback, 'GOOD') AS image_feedback
    FROM images
    WHERE image = :image_name
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"image_name": image_name}).fetchone()
    return result[0] if result else 'GOOD'

# Function to update prompt
def update_prompt(serial_nos, new_prompt, feedback):
    try:
        serial_nos = int(serial_nos)
        update_query = text("""
        UPDATE prompts
        SET image_prompts = :new_prompt, prompt_feedback = :feedback
        WHERE serial_nos = :serial_nos
        """)
        with engine.connect() as conn:
            conn.execute(update_query, {"new_prompt": new_prompt, "feedback": feedback, "serial_nos": serial_nos})
            conn.commit()
        st.success("Prompt updated successfully!")
    except Exception as e:
        st.error(f"Failed to update prompt: {e}")

# Function to update image review
def update_image_review(image_name, review):
    try:
        update_query = text("""
        UPDATE images
        SET image_feedback = :review
        WHERE image = :image_name
        """)
        with engine.connect() as conn:
            conn.execute(update_query, {"review": review, "image_name": image_name})
            conn.commit()
        st.success("Image review updated successfully!")
    except Exception as e:
        st.error(f"Failed to update image review: {e}")

# Function to add new prompt
def add_new_prompt(image_number, new_prompt):
    try:
        insert_query = text("""
        INSERT INTO prompts (sno, image_prompts, prompt_feedback)
        VALUES (:sno, :new_prompt, 'GOOD')
        """)
        with engine.connect() as conn:
            conn.execute(insert_query, {"sno": image_number, "new_prompt": new_prompt})
            conn.commit()
        st.success("New prompt added successfully!")
    except Exception as e:
        st.error(f"Failed to add new prompt: {e}")

# Display the selected image and its prompts
image_name = f"image{st.session_state.image_number}.jpg"
image_path = os.path.join("Prompts/Final images moodboard/", image_name)

col1, col2 = st.columns([1, 2])

with col1:
    # Load the image from Google Cloud Storage
    blob = bucket.blob(image_path)
    image_data = blob.download_as_bytes()
    image = Image.open(BytesIO(image_data))
    st.image(image, caption=f"Image {st.session_state.image_number}")

    # Get existing review from the database or default to "GOOD"
    image_review_text = get_image_feedback(image_name)
    default_rating = 10 if image_review_text == "GOOD" else 1
    
    # Image rating slider
    image_review = st.slider(f"Rate Image {st.session_state.image_number}:", 1, 10, value=default_rating, format="%d")
    review_text = "GOOD" if image_review > 5 else "BAD"

    if st.button(f"Save Image Review {st.session_state.image_number}"):
        update_image_review(image_name, review_text)

with col2:
    prompts_df = get_prompts(st.session_state.image_number)
    if not prompts_df.empty:
        prompt_options = prompts_df['image_prompts'].tolist()
        selected_prompt_index = st.selectbox(f"Select Prompt for Image {st.session_state.image_number}", 
                                           range(len(prompt_options)), 
                                           format_func=lambda x: f"Prompt {x+1}")
        selected_prompt = prompt_options[selected_prompt_index]
        serial_nos = prompts_df.iloc[selected_prompt_index]['serial_nos']

        st.write(f"Prompt {selected_prompt_index + 1}:")
        new_prompt = st.text_area(f"Edit Prompt {selected_prompt_index + 1}", 
                                value=selected_prompt, 
                                key=f"prompt_{serial_nos}")
        
        default_rating = 10 if prompts_df.iloc[selected_prompt_index]['prompt_feedback'] == "GOOD" else 1
        prompt_review_score = st.slider(f"Rate Prompt {selected_prompt_index + 1}:", 
                                      1, 10, 
                                      value=default_rating, 
                                      format="%d", 
                                      key=f"review_{serial_nos}")
        
        prompt_review = "GOOD" if prompt_review_score > 5 else "BAD"

        if st.button(f"Save Prompt {selected_prompt_index + 1}", key=f"save_prompt_{serial_nos}"):
            update_prompt(serial_nos, new_prompt, prompt_review)
    else:
        st.warning(f"No prompts found for image {st.session_state.image_number}.")

    # Add new prompt section
    st.write(f"Add a new prompt for Image {st.session_state.image_number}:")
    new_prompt_input = st.text_area(f"New Prompt for Image {st.session_state.image_number}", 
                                  key=f"new_prompt_{st.session_state.image_number}")
    if st.button(f"Add New Prompt for Image {st.session_state.image_number}"):
        if new_prompt_input.strip():
            add_new_prompt(st.session_state.image_number, new_prompt_input)
        else:
            st.warning("New prompt cannot be empty.")



# Approve/Reject buttons styling
button_styles = """
    <style>
        .stButton > button[kind="primary"] {
            background-color: #28a745;
            color: white;
            border: none;
            width: 100%;
        }
        #reject_button button {
            background-color: #dc3545; /* Red background color */
            color: white;
            border: none;
            width: 100%;
            font-size: 16px;
            padding: 10px;
        }
        
        .stButton > button[kind="secondary"] {
            background-color: #2f4f4f;
            color: white;
            border: none;
            width: 100%;
        }
        .stButton > button[kind="secondary"] {
            background-color: #2f4f4f;
            color: white;
            border: none;
            width: 100%;
        }
    </style>
"""
st.markdown(button_styles, unsafe_allow_html=True)

# Approve/Reject buttons
col1, col2 = st.columns(2)

with col1:
    if st.button("✓ Approve", key="approve_button", type="primary"):
        st.success(f"Image {st.session_state.image_number} Approved.")
        try:
            update_query = text("""
            UPDATE images
            SET status = 'APPROVED'
            WHERE image = :image_name
            """)
            with engine.connect() as conn:
                conn.execute(update_query, {"image_name": image_name})
                conn.commit()
            st.success("Image status updated to Approved in the database.")
        except Exception as e:
            st.error(f"Failed to update status to Approved: {e}")

with col2:
    if st.button("✕ Reject", key="reject_button", type="secondary"):
        st.warning(f"Image {st.session_state.image_number} Rejected.")
        try:
            update_query = text("""
            UPDATE images
            SET status = 'REJECTED'
            WHERE image = :image_name
            """)
            with engine.connect() as conn:
                conn.execute(update_query, {"image_name": image_name})
                conn.commit()
            st.warning("Image status updated to Rejected in the database.")
        except Exception as e:
            st.error(f"Failed to update status to Rejected: {e}")

# Navigation buttons
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("← Back", key="back_button", on_click=go_back):
        pass

with col2:
    st.markdown(f"<h3 style='text-align: center'>Image {st.session_state.image_number}</h3>", unsafe_allow_html=True)

with col3:
    if st.button("Next →", key="next_button", on_click=go_next):
        pass

# Reset navigation_clicked state at the end of the script
if st.session_state.navigation_clicked:
    st.session_state.navigation_clicked = False
