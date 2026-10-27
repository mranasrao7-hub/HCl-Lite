
import json
from pathlib import Path
from datetime import datetime, time

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EMPLOYEE_FILE = DATA_DIR / "employees.json"
ATTENDANCE_FILE = DATA_DIR / "attendance.json"
SETTINGS_FILE = DATA_DIR / "company_settings.json"

DEFAULT_SETTINGS = {
    "office_start": "09:00",
    "grace_minutes": 15,
}


def load_json(path, default=None):
    if default is None:
        default = []

    if not path.exists():
        return default.copy()

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, type(default)) else default.copy()

    except (json.JSONDecodeError, OSError):
        st.error(f"{path.name} file read nahi ho saki.")
        return default.copy()


def save_attendance(records):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = ATTENDANCE_FILE.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=4, ensure_ascii=False)

    temp_file.replace(ATTENDANCE_FILE)


def load_settings():
    saved = load_json(SETTINGS_FILE, {})
    settings = {**DEFAULT_SETTINGS, **saved}

    try:
        time.fromisoformat(settings["office_start"])
    except (ValueError, TypeError):
        settings["office_start"] = DEFAULT_SETTINGS["office_start"]

    try:
        settings["grace_minutes"] = max(
            0, int(settings["grace_minutes"])
        )
    except (ValueError, TypeError):
        settings["grace_minutes"] = DEFAULT_SETTINGS["grace_minutes"]

    return settings


def same_employee(first_id, second_id):
    return str(first_id).strip() == str(second_id).strip()


def calculate_status(check_in, office_start, grace_minutes):
    check_in_minutes = check_in.hour * 60 + check_in.minute
    office_minutes = office_start.hour * 60 + office_start.minute

    return (
        "Late"
        if check_in_minutes > office_minutes + grace_minutes
        else "Present"
    )


def show_attendance_manager():
    user = st.session_state.get("user")

    if not isinstance(user, dict):
        st.warning("Please Admin account se login karo.")
        st.stop()

    if str(user.get("role", "")).strip().lower() != "admin":
        st.error("Sirf Admin attendance manage kar sakta hai.")
        st.stop()

    st.title("📅 Attendance Management")
    st.caption("Employee aur Admin attendance records ek hi jagah manage karein.")

    employees = [
        employee
        for employee in load_json(EMPLOYEE_FILE, [])
        if isinstance(employee, dict)
        and str(employee.get("status", "Active")).strip().lower() == "active"
    ]

    records = [
        record
        for record in load_json(ATTENDANCE_FILE, [])
        if isinstance(record, dict)
    ]

    settings = load_settings()
    today = datetime.now().date().isoformat()

    if not employees:
        st.info("Abhi koi active employee available nahi hai.")
        return

    employee_map = {
        f'{employee.get("name", "Unknown")} — {employee.get("email", "")}': employee
        for employee in employees
    }

    today_records = [
        record for record in records
        if record.get("date") == today
    ]

    present_ids = {
        str(record.get("employee_id"))
        for record in today_records
        if record.get("check_in")
    }

    late_count = sum(
        record.get("status") == "Late"
        for record in today_records
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Active Employees", len(employees))
    col2.metric("Checked In Today", len(present_ids))
    col3.metric("Late Today", late_count)

    st.divider()
    st.subheader("Record Attendance")

    try:
        default_office_time = time.fromisoformat(settings["office_start"])
    except (ValueError, TypeError):
        default_office_time = time(9, 0)

    with st.form("attendance_record_form"):
        selected_label = st.selectbox(
            "Select Employee",
            list(employee_map.keys()),
        )

        check_in = st.time_input(
            "Check-in Time",
            value=datetime.now().time().replace(second=0, microsecond=0),
        )

        st.caption(
            f'Company office start: {default_office_time.strftime("%H:%M")} '
            f'| Grace period: {settings["grace_minutes"]} minutes'
        )

        submitted = st.form_submit_button("Save Attendance")

    if submitted:
        employee = employee_map[selected_label]

        already_recorded = any(
            same_employee(record.get("employee_id"), employee.get("id"))
            and record.get("date") == today
            for record in records
        )

        if already_recorded:
            st.error("Is employee ki attendance aaj already recorded hai.")
        else:
            status = calculate_status(
                check_in,
                default_office_time,
                settings["grace_minutes"],
            )

            records.append({
                "employee_id": employee.get("id"),
                "employee_name": employee.get("name", ""),
                "date": today,
                "check_in": check_in.strftime("%H:%M:%S"),
                "check_out": None,
                "status": status,
            })

            save_attendance(records)
            st.success(f"Attendance save ho gayi: {status}")
            st.rerun()

    st.divider()
    st.subheader("Attendance Records")

    if not records:
        st.info("Abhi koi attendance record nahi hai.")
        return

    search = st.text_input(
        "Search by employee name or ID",
        placeholder="Employee name ya ID likho...",
    )

    filtered_records = records

    if search.strip():
        query = search.strip().lower()
        filtered_records = [
            record for record in records
            if query in str(record.get("employee_name", "")).lower()
            or query in str(record.get("employee_id", "")).lower()
        ]

    df = pd.DataFrame(filtered_records)

    preferred_columns = [
        "employee_id",
        "employee_name",
        "date",
        "check_in",
        "check_out",
        "status",
    ]

    available_columns = [
        column for column in preferred_columns if column in df.columns
    ]

    if not df.empty:
        df = df[available_columns].sort_values(
            "date", ascending=False
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download Attendance CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="attendance_records.csv",
            mime="text/csv",
        )
    else:
        st.info("Search se koi matching attendance record nahi mila.")
