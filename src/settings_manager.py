
import json
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_FILE = BASE_DIR / "data" / "company_settings.json"

DEFAULT_SETTINGS = {
    "company_name": "My Company",
    "office_start": "09:00",
    "grace_minutes": 15,
    "annual_leave_quota": 20,
    "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
}


def load_settings():
    if not SETTINGS_FILE.exists():
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
            saved = json.load(file)

        return {**DEFAULT_SETTINGS, **saved}
    except (json.JSONDecodeError, OSError):
        return DEFAULT_SETTINGS.copy()


def save_settings(settings):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(settings, file, indent=4)


def show_settings_manager():
    user = st.session_state.get("user")

    if not user:
        st.warning("Please log in first.")
        st.stop()

    if user.get("role") != "Admin":
        st.error("Only Admin can change company settings.")
        st.stop()

    st.title("⚙️ Company Settings")
    st.caption("Configure company information and HR policies.")

    settings = load_settings()
    days = [
        "Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"
    ]

    with st.form("company_settings_form"):
        company_name = st.text_input(
            "Company Name",
            value=settings["company_name"]
        )

        office_start = st.time_input(
            "Office Start Time",
            value=__import__("datetime").time.fromisoformat(
                settings["office_start"]
            )
        )

        grace_minutes = st.number_input(
            "Late Grace Period (minutes)",
            min_value=0,
            max_value=120,
            value=int(settings["grace_minutes"])
        )

        annual_quota = st.number_input(
            "Annual Leave Quota (working days)",
            min_value=0,
            max_value=365,
            value=int(settings["annual_leave_quota"])
        )

        working_days_selected = st.multiselect(
            "Company Working Days",
            options=days,
            default=settings["working_days"]
        )

        submitted = st.form_submit_button("Save Settings")

        if submitted:
            if not company_name.strip():
                st.error("Company name required hai.")
            elif not working_days_selected:
                st.error("Kam az kam ek working day select karo.")
            else:
                updated_settings = {
                    "company_name": company_name.strip(),
                    "office_start": office_start.strftime("%H:%M"),
                    "grace_minutes": int(grace_minutes),
                    "annual_leave_quota": int(annual_quota),
                    "working_days": working_days_selected
                }

                save_settings(updated_settings)
                st.success("Company settings save ho gayi!")
                st.rerun()


# Called from the Streamlit page.
