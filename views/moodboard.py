import logging
import streamlit as st
import os
from PIL import Image
import pandas as pd
from sqlalchemy import create_engine, text
from google.cloud import storage
from io import BytesIO
import json
import tempfile
import psycopg2

db_connection = {
    "host": "34.93.64.44",
    "port": "5432",
    "dbname": "genai",
    "user": "postgres",
    "password": "postgres-genai"
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
logger = logging.getLogger()
logger.info("logger")
conn = psycopg2.connect(**db_connection)
cursor = conn.cursor()
logger.info("db_connection")


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

# Find the maximum image number in the bucket
def find_max_image_number(bucket, prefix):
    max_image_number = 0
    blobs = bucket.list_blobs(prefix=prefix)
    for blob in blobs:
        try:
            filename = os.path.basename(blob.name)
            if filename.startswith('image') and filename.endswith('.jpg'):
                num = int(filename[5:-4])
                max_image_number = max(max_image_number, num)
        except ValueError:
            continue
    return max_image_number

# Image prefix for storage
image_prefix = "Prompts/Final images moodboard/"
MAX_IMAGE_NUMBER = find_max_image_number(bucket, image_prefix)

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
    if not st.session_state.navigation_clicked and st.session_state.image_number < MAX_IMAGE_NUMBER:
        st.session_state.image_number += 1
        st.session_state.navigation_clicked = True

# Function to fetch prompts from PostgreSQL based on image number
def get_prompts(image_number):
    query = f"""
    SELECT serial_nos, sno, image_prompts,
           COALESCE(prompt_feedback, 10) AS prompt_feedback,
           COALESCE(status, 'PENDING') AS status
    FROM prompts
    WHERE sno = {image_number}
    ORDER BY serial_nos;
    """
    prompts_df = pd.read_sql(query, engine)
    return prompts_df

# Function to fetch image feedback and status
def get_prompt_feedback(image_name):
    query = text("""
    SELECT COALESCE(prompt_feedback, 10) AS prompt_feedback,
           COALESCE(status, 'PENDING') AS status
    FROM prompts
    WHERE image_prompts = :image_name
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"image_name": image_name}).fetchone()
    return result[0] if result else 10, result[1] if result else 'PENDING'

# Function to fetch image feedback and status
def get_image_feedback(image_name):
    query = text("""
    SELECT COALESCE(image_feedback, 10) AS image_feedback,
           COALESCE(status, 'PENDING') AS status
    FROM images
    WHERE image = :image_name
    """)
    with engine.connect() as conn:
        result = conn.execute(query, {"image_name": image_name}).fetchone()
    return result[0] if result else 10, result[1] if result else 'PENDING'

def update_prompt(serial_nos, new_prompt):
    try:
        serial_nos = int(serial_nos)
        logger.info(f"sno => {serial_nos}")
        logger.info(f"new_prompts => {new_prompt}")

        update_query = """
        UPDATE prompts
        SET image_prompts = %s
        WHERE serial_nos = %s
        """
        logger.info(f"update_query => {update_query}")

       
        cursor.execute(update_query, (
             
            # prompt_feedback,
            # image_prompts
            new_prompt,
            serial_nos
        ))
        conn.commit()
        logger.info("updated")

        # Check if any rows were affected
        if cursor.rowcount > 0:
            st.success("Prompt updated successfully!")
            logger.info(f"Rows updated: {cursor.rowcount}")
        else:
            st.warning("No rows were updated. Check if the serial_nos exists in the database.")
            logger.warning(f"Query executed, but no rows matched serial_nos: {serial_nos}")
           
    except Exception as e:
        # Log and show error if something goes wrong
        st.error(f"Failed to update prompt: {e}")
        logger.error(f"Exception occurred: {e}")
       
# Function to update image review
def update_image_review(image_name, review):
    logger.info(image_name, review)
    try:
        update_query = """
        UPDATE images
        SET image_feedback = %s
        WHERE image = %s
        """
        # with engine.connect() as conn:
        cursor.execute(update_query, (review, image_name))
        conn.commit()
        st.success("Image review updated successfully!")
    except Exception as e:
        st.error(f"Failed to update image review: {e}")
       
# Function to update image review
def update_prompt_review(serial_nos, review):
    logger.info("entering")
    try:
        update_query = """
        UPDATE prompts
        SET prompt_feedback = %s
        WHERE serial_nos = %s
        """
       
        # with engine.connect() as conn:
        cursor.execute(update_query, (review, int(serial_nos)))
        conn.commit()
        st.success("prompt review updated successfully!")
    except Exception as e:
        st.error(f"Failed to update prompt review: {e}")
       
def update_corelation_review(serial_nos, corelation_review):
    logger.info("entering")
    try:
        update_query = """
        UPDATE prompts
        SET correlation_feedback = %s
        WHERE serial_nos = %s
        """
       
        # with engine.connect() as conn:
        cursor.execute(update_query, (corelation_review, int(serial_nos)))
        conn.commit()
        st.success("correlation review updated successfully!")
    except Exception as e:
        st.error(f"Failed to update correlation review: {e}")

# Function to add comments
def add_comments(serial_nos, comments):
    try:
        update_query = """
        UPDATE prompts
        SET comments = %s
        WHERE serial_nos = %s
        """
        with conn.cursor() as cursor:
            cursor.execute(update_query, (comments, int(serial_nos)))
            conn.commit()

            # Check if rows were updated
            if cursor.rowcount > 0:
                st.success("Comments added successfully!")
                logger.info(f"Comments added to serial_nos {serial_nos}.")
            else:
                st.warning("No rows updated. Check if the serial number exists.")
    except Exception as e:
        st.error(f"Failed to add comments: {e}")
        logger.error(f"Error adding comments: {e}")
        

        

# Function to add new prompt
def add_new_prompt(image_number, prompt_text):
    try:
        insert_query = text("""
        INSERT INTO prompts (sno, image_prompts, prompt_feedback, status)
        VALUES (:sno, :prompt_text, 10, 'PENDING')
        """)
        with engine.connect() as conn:
            conn.execute(insert_query, {
                "sno": image_number,
                "prompt_text": prompt_text
            })
            conn.commit()
        st.success("New prompt added successfully!")
    except Exception as e:
        st.error(f"Failed to add new prompt: {e}")



# Function to handle image number update
def update_image_number():

   
    try:
        # Use the input from the text input to update image number
        input_number = int(st.session_state.image_number_input)
        if input_number < 1 or input_number > MAX_IMAGE_NUMBER:
            st.error(f"Please enter a number between 1 and {MAX_IMAGE_NUMBER}.")
        else:
            st.session_state.image_number = input_number
    except ValueError:
        st.error("Please enter a valid integer.")

st.markdown("""
    <style>
    /* Custom style for compact search input */
    div[data-testid="stTextInput"] {
        max-width: 250px;  /* Make the search bar smaller */
    }
    div[data-testid="stTextInput"] input {
        border: 3px solid #4CAF50;
        border-radius: 8px;
        padding: 10px 10px 10px 35px;  /* Space for icon */
        font-size: 14px;
        background-image: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-search"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>');
        background-repeat: no-repeat;
        background-position: 8px center;
        background-size: 20px;
    }
    div[data-testid="stTextInput"] input:focus {
        outline: none;
        border-color: #45a049;
        box-shadow: 0 0 5px rgba(76, 175, 80, 0.5);
    }
    </style>
""", unsafe_allow_html=True)

# Image number and navigation section
col1 = st.columns([1])  # One column for the left side
with col1[0]: 
    st.markdown(f"<h4 style='text-align: left'>Moodboard {st.session_state.image_number}</h4>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 3])  # Three columns for layout
with col3: 
    # Custom CSS to style the text_input box and move it upwards
    st.markdown("""
        <style>
            div[data-testid="stTextInput"] {
                margin-top: -90px;  /* Move the input box upwards */
                text-align: right;  /* Align text inside the input box to the right */
                width: 200px;  /* Set the width of the input box */
            }
            input[data-testid="stTextInput"] {
                font-size: 10px;  /* Adjust the font size inside the input box */
        </style>
    """, unsafe_allow_html=True)

    # Compact search input with icon
    image_number_input = st.text_input(
        "", 
        value=str(st.session_state.image_number),
        placeholder=f"Enter moodboard number (1-{MAX_IMAGE_NUMBER})",
        key="image_number_input",
        on_change=update_image_number
    )

       

# Display the selected image and its prompts
image_name = f"image{st.session_state.image_number}.jpg"
image_path = os.path.join(image_prefix, image_name)


col1, col2, col3 = st.columns([1, 2, 3])  # Three columns for layout
with col2: 
    try:
        if image_exists_in_bucket(bucket, image_path):
            blob = bucket.blob(image_path)
            image_data = blob.download_as_bytes()
            image = Image.open(BytesIO(image_data))

            # Display the image with a medium size
            st.image(
                image, 
                caption=f"Image {st.session_state.image_number}", 
                width=280  # Adjust this value to set the image width
            )
        else:
            st.error(f"Image {st.session_state.image_number} not found.")
    except Exception as e:
        st.error(f"Error loading image: {e}")
    
col1, col2 = st.columns([1, 2])

with col1:
    
    # Get existing review and status from the database
    image_review_score, image_status = get_image_feedback(image_name)
    # Image rating slider
    image_review = st.slider(f"Rate Image {st.session_state.image_number}:", 1, 10, value=image_review_score, format="%d")
    if st.button(f"Submit rating"):
        update_image_review(image_name, image_review)
        

 
    # Comments section
    st.subheader("Add Comments")
    comments = st.text_area("Add your comments:", placeholder="Write your comments here...")
    if st.button("Submit Comments"):
        if comments.strip():
            # Use the current image number as the serial_nos
            add_comments(st.session_state.image_number, comments)
        else:
            st.error("Please add a comment before submitting!")
        
        

with col2:
    prompts_df = get_prompts(st.session_state.image_number)
    if not prompts_df.empty:
        prompt_options = prompts_df['image_prompts'].tolist()
        
        selected_prompt_index = st.selectbox(
            f"Select prompt for image {st.session_state.image_number}",
            range(len(prompt_options)),
            format_func=lambda x: f"Prompt {x + 1}"
        )
        selected_prompt = prompt_options[selected_prompt_index]
        serial_nos = prompts_df.iloc[selected_prompt_index]['serial_nos']


        st.markdown("""
            <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
        """, unsafe_allow_html=True)

        # Use FontAwesome for Edit button with larger icon
        if st.button("Edit🖉 ", key=f"edit_prompt_{serial_nos}", help="Edit the prompt"):
            st.session_state.edit_mode = True

        # Display the text area to edit the prompt if in edit mode
        if st.session_state.get("edit_mode"):
            with st.form(key=f"edit_form_{serial_nos}"):
                new_prompt = st.text_area(
                    f"Edit prompt {selected_prompt_index + 1}",
                    value=selected_prompt,
                    key=f"new_prompt_{serial_nos}"
                )
                submitted = st.form_submit_button("Update Prompt")
                if submitted:
                    logger.info("Update button clicked.")
                    if new_prompt:
                        update_prompt(serial_nos, new_prompt)
                        st.session_state.edit_mode = False  # Exit edit mode
                        logger.info(f"Prompt {serial_nos} successfully updated.")
                    else:
                        st.warning("Please provide a new prompt value.")

      
       
       
    # Get existing review and status from the database
        prompt_review_score, image_status = get_prompt_feedback(image_name)

    # Image rating slider
        st.write(f"Prompt:- {selected_prompt}")
        prompt_review = st.slider(f"Rate Prompt:", 1, 10, value=1, format="%d")

        if st.button(f"prompt rating"):
            update_prompt_review(serial_nos, prompt_review)
                    
        corelation_review = st.slider(f"Correlation Rate:", 1, 10, value=1, format="%d")

        if st.button(f"correlation rating"):
            update_corelation_review(serial_nos, corelation_review)
            # st.experimental_rerun()



    else:
        st.warning(f"No prompts found for image {st.session_state.image_number}.")

    # Add new prompt section
    st.write(f"Add a new prompt for Image {st.session_state.image_number}:")

    # Check if button clicked
    if st.button(f"Add New Prompt"):
        # Set a session state variable to show the text area after the button is clicked
        st.session_state.show_new_prompt_text_area = True

    # Only show the text area if the session state variable is True
    if "show_new_prompt_text_area" in st.session_state and st.session_state.show_new_prompt_text_area:
        # Display the text area to add a new prompt
        new_prompt_input = st.text_area(f"New Prompt for Image {st.session_state.image_number}",
                                        key=f"new_prompts_{st.session_state.image_number}")

        # Submit button to add the new prompt
        if st.button(f"Submit New Prompt"):
            # Call the function to add the new prompt to the database
            add_new_prompt(st.session_state.image_number, new_prompt_input)

            # Reset the state to hide the text area and button after submission
            st.session_state.show_new_prompt_text_area = False


# Approve/Reject buttons styling
button_styles = """
    <style>
        .stButton > button[kind="primary"] {
            background-color: #28a745;
            color: white;
            border: none;
            width: 100%;
            padding: 15px;
            font-size: 18px;
        }
       
       
        .stButton > button[kind="secondary"] {
            background-color: #2f4f4f;
            color: white;
            border: none;
            width: 100%;
            padding: 15px;
            font-size: 18px;
        }
       
        /* Navigation buttons */
        .stButton > button {
            padding: 10px 20px;
            font-size: 16px;
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
            # Update image status
            image_update_query = text("""
            UPDATE images
            SET status = 'APPROVED'
            WHERE image = :image_name
            """)
           
            # Update all prompts status for this image
            prompts_update_query = text("""
            UPDATE prompts
            SET status = 'APPROVED'
            WHERE sno = :image_number
            """)
           
            with engine.connect() as conn:
                conn.execute(image_update_query, {"image_name": image_name})
                conn.execute(prompts_update_query, {"image_number": st.session_state.image_number})
                conn.commit()
            st.success("Image and associated prompts status updated to Approved in the database.")
        except Exception as e:
            st.error(f"Failed to update status to Approved: {e}")

with col2:
    if st.button("✕ Reject", key="reject_button", type="secondary"):
        st.warning(f"Image {st.session_state.image_number} Rejected.")
        try:
            # Update image status
            image_update_query = text("""
            UPDATE images
            SET status = 'REJECTED'
            WHERE image = :image_name
            """)
           
            # Update all prompts status for this image
            prompts_update_query = text("""
            UPDATE prompts
            SET status = 'REJECTED'
            WHERE sno = :image_number
            """)
           
            with engine.connect() as conn:
                conn.execute(image_update_query, {"image_name": image_name})
                conn.execute(prompts_update_query, {"image_number": st.session_state.image_number})
                conn.commit()
            st.warning("Image and associated prompts status updated to Rejected in the database.")
        except Exception as e:
            st.error(f"Failed to update status to Rejected: {e}")


# Navigation buttons
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("← Back", key="back_button", on_click=go_back):
        pass

with col3:
    if st.button("Next →", key="next_button", on_click=go_next):
        pass

# Reset navigation_clicked state at the end of the script
if st.session_state.navigation_clicked:
    st.session_state.navigation_clicked = False




