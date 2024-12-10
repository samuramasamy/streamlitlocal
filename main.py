import hmac
import streamlit as st


def check_password():
    """Returns `True` if the user had a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["username"] in st.secrets[
            "passwords"
        ] and hmac.compare_digest(
            st.session_state["password"],
            st.secrets.passwords[st.session_state["username"]],
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the username or password.
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # Return True if the username + password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show inputs for username + password.
    login_form()
    if "password_correct" in st.session_state:
        st.error("😕 User not known or password incorrect")
    return False


if not check_password():
    st.stop()

# Main Streamlit app starts here
#st.write("Here goes your normal Streamlit app...")
#st.button("Click me")

#simport streamlit as st

about_page = st.Page(
    page="views/about.py",
    title="About",
    icon=":material/account_circle:",
    default=True,
)
moodboard_page = st.Page(
    page = "views/moodboard.py",
    title="Moodboard",
    icon=":material/image:",
)
upload_prompts_page = st.Page(
    page = "views/upload_prompts.py",
    title="upload_prompts",
    icon=":material/image:",
)
upload_images_page = st.Page(
    page = "views/upload_images.py",
    title="upload_images",
    icon=":material/image:",
)
image_prompt_page = st.Page(
    page="views/image_prompt.py",
    title="image_prompt",
    icon=":material/image:"
)
fashion_tech_page = st.Page(
    page="views/fashion_tech.py",
    title="fashion_tech",
    icon=":material/image:"
)
pg = st.navigation(
    {
        "Info": [about_page],
        "Project": [moodboard_page, upload_prompts_page,upload_images_page,image_prompt_page,fashion_tech_page],
    }
)
pg.run()


