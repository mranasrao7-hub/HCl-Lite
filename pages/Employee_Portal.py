
import hashlib
import hmac
import json
import secrets
from datetime import date, datetime, time, timedelta
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EMP_FILE = DATA_DIR / "employees.json"
ATT_FILE = DATA_DIR / "attendance.json"
LEAVE_FILE = DATA_DIR / "leaves.json"
SETTINGS_FILE = DATA_DIR / "company_settings.json"


def load_json(path, default=None):
    if default is None:
        default = []

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not path.exists():
        return default.copy()

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, type(default)) else default.copy()
    except (json.JSONDecodeError, OSError):
        st.error(f"{path.name} file read nahi ho saki.")
        return default.copy()


def save_json(path, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = path.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    temp_file.replace(path)


def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,
    ).hex()


def id_matches(saved_id, entered_id):
    return str(saved_id).strip() == str(entered_id).strip()


def next_employee_id(employees):
    ids = []

    for employee in employees:
        try:
            ids.append(int(employee.get("id", 0)))
        except (ValueError, TypeError):
            continue

    return max(ids, default=0) + 1


def register_employee():
    st.subheader("Create Employee Account")
    st.caption(
        "Naye employees registration ke baad Admin approval ka intezar karein. "
        "Existing employee apni ID se password set kar sakta hai."
    )

    with st.form("employee_self_registration"):
        name = st.text_input("Full Name")
        email = st.text_input("Email Address")
        department = st.text_input("Department")
        job_title = st.text_input("Job Title")

        employee_id = st.text_input(
            "Existing Employee ID (sirf existing employee ke liye)"
        )

        password = st.text_input("Create Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")

        submitted = st.form_submit_button(
            "Register / Set Password",
            use_container_width=True,
        )

    if not submitted:
        return

    email = email.strip().lower()
    name = name.strip()
    department = department.strip()
    job_title = job_title.strip()
    employee_id = employee_id.strip()

    if not email or "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        st.error("Valid email address enter karo.")
        return

    if len(password) < 8:
        st.error("Password kam az kam 8 characters ka hona chahiye.")
        return

    if password != confirm:
        st.error("Passwords match nahi karte.")
        return

    employees = load_json(EMP_FILE, [])

    existing = next(
        (
            employee for employee in employees
            if str(employee.get("email", "")).strip().lower() == email
        ),
        None,
    )

    if existing:
        status = str(existing.get("status", "")).strip().lower()

        if status == "pending approval":
            st.warning("Tumhara account abhi Admin approval ka intezar kar raha hai.")
            return

        if status != "active":
            st.error("Yeh account active nahi hai. Admin se contact karo.")
            return

        if existing.get("password_hash") and existing.get("password_salt"):
            st.error(
                "Is email par password pehle se set hai. "
                "Login tab use karo."
            )
            return

        if not employee_id or not id_matches(
            existing.get("id"), employee_id
        ):
            st.error(
                "Existing account verify karne ke liye sahi Employee ID enter karo."
            )
            return

        salt = secrets.token_hex(16)
        existing["password_salt"] = salt
        existing["password_hash"] = hash_password(password, salt)

        save_json(EMP_FILE, employees)

        st.success(
            "Password successfully set ho gaya! Ab Login tab se login karo."
        )
        return

    if not all([name, department, job_title]):
        st.error("Naye account ke liye name, department aur job title required hain.")
        return

    salt = secrets.token_hex(16)

    employees.append({
        "id": next_employee_id(employees),
        "name": name,
        "email": email,
        "department": department,
        "job_title": job_title,
        "monthly_salary": 0,
        "joining_date": date.today().isoformat(),
        "status": "Pending Approval",
        "password_salt": salt,
        "password_hash": hash_password(password, salt),
        "registered_at": datetime.now().isoformat(timespec="seconds"),
    })

    save_json(EMP_FILE, employees)

    st.success(
        "Registration successful! Admin approval ke baad login kar sakte ho."
    )


def employee_login():
    st.subheader("Employee Login")

    with st.form("employee_login_form"):
        email = st.text_input("Email Address").strip().lower()
        password = st.text_input("Password", type="password")

        submitted = st.form_submit_button(
            "Login",
            use_container_width=True,
        )

    if not submitted:
        return

    employees = load_json(EMP_FILE, [])

    employee = next(
        (
            item for item in employees
            if str(item.get("email", "")).strip().lower() == email
        ),
        None,
    )

    if employee is None:
        st.error("Is email ka account nahi mila.")
        return

    status = str(employee.get("status", "")).strip().lower()

    if status == "pending approval":
        st.warning("Tumhara account abhi Admin approval ka intezar kar raha hai.")
        return

    if status != "active":
        st.error("Account active nahi hai. Admin se contact karo.")
        return

    salt = employee.get("password_salt", "")
    saved_hash = employee.get("password_hash", "")

    if not salt or not saved_hash:
        st.error(
            "Is account ka password abhi set nahi hua. "
            "Register tab mein Employee ID se password set karo."
        )
        return

    entered_hash = hash_password(password, salt)

    if not hmac.compare_digest(entered_hash, saved_hash):
        st.error("Email ya password incorrect hai.")
        return

    st.session_state["employee_email"] = email
    st.rerun()


def show_attendance(employee):
    st.subheader("🕒 My Attendance")

    attendance = load_json(ATT_FILE, [])
    today = date.today().isoformat()

    today_record = next(
        (
            record for record in attendance
            if id_matches(record.get("employee_id"), employee.get("id"))
            and record.get("date") == today
        ),
        None,
    )

    if today_record:
        st.write("**Check-in:**", today_record.get("check_in", "—"))
        st.write(
            "**Check-out:**",
            today_record.get("check_out") or "Not checked out",
        )
        st.write("**Status:**", today_record.get("status", "Present"))
    else:
        st.info("Aaj ki attendance abhi record nahi hui.")

    left, right = st.columns(2)

    with left:
        if st.button(
            "Check In",
            use_container_width=True,
            disabled=today_record is not None,
        ):
            settings = load_json(SETTINGS_FILE, {})
            office_start_text = settings.get("office_start", "09:00")

            try:
                office_start = time.fromisoformat(office_start_text)
            except (ValueError, TypeError):
                office_start = time(9, 0)

            try:
                grace = max(0, int(settings.get("grace_minutes", 15)))
            except (ValueError, TypeError):
                grace = 15

            now = datetime.now()
            scheduled = office_start.hour * 60 + office_start.minute
            current = now.hour * 60 + now.minute
            status = "Late" if current > scheduled + grace else "Present"

            attendance.append({
                "employee_id": employee.get("id"),
                "employee_name": employee.get("name"),
                "date": today,
                "check_in": now.strftime("%H:%M:%S"),
                "check_out": None,
                "status": status,
            })

            save_json(ATT_FILE, attendance)
            st.success(f"Check-in record ho gaya: {status}")
            st.rerun()

    with right:
        can_checkout = (
            today_record is not None
            and not today_record.get("check_out")
        )

        if st.button(
            "Check Out",
            use_container_width=True,
            disabled=not can_checkout,
        ):
            for record in attendance:
                if (
                    id_matches(record.get("employee_id"), employee.get("id"))
                    and record.get("date") == today
                    and not record.get("check_out")
                ):
                    record["check_out"] = datetime.now().strftime("%H:%M:%S")
                    break

            save_json(ATT_FILE, attendance)
            st.success("Check-out record ho gaya.")
            st.rerun()

    my_records = [
        record for record in attendance
        if id_matches(record.get("employee_id"), employee.get("id"))
    ]

    st.subheader("Attendance History")

    if my_records:
        st.dataframe(
            sorted(
                my_records,
                key=lambda item: item.get("date", ""),
                reverse=True,
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Attendance history abhi empty hai.")


def count_working_days(start, end, working_days):
    day_numbers = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }

    allowed = {
        day_numbers[name]
        for name in working_days
        if name in day_numbers
    }

    total = 0
    current = start

    while current <= end:
        if current.weekday() in allowed:
            total += 1
        current += timedelta(days=1)

    return total


def show_leave_requests(employee):
    st.subheader("🌴 Apply for Leave")

    leaves = load_json(LEAVE_FILE, [])
    settings = load_json(SETTINGS_FILE, {})

    working_days = settings.get(
        "working_days",
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    )

    with st.form("employee_leave_request"):
        leave_type = st.selectbox(
            "Leave Type",
            ["Annual Leave", "Sick Leave", "Personal Leave", "Other"],
        )

        start_date = st.date_input(
            "Start Date",
            value=date.today(),
            min_value=date.today(),
        )

        end_date = st.date_input(
            "End Date",
            value=date.today(),
            min_value=date.today(),
        )

        reason = st.text_area("Reason")
        submitted = st.form_submit_button("Submit Leave Request")

    if submitted:
        if end_date < start_date:
            st.error("End Date, Start Date se pehle nahi ho sakti.")
            return

        if not reason.strip():
            st.error("Leave ki reason enter karo.")
            return

        days = count_working_days(start_date, end_date, working_days)

        if days == 0:
            st.error("Selected dates mein koi company working day nahi.")
            return

        overlap = False

        for leave in leaves:
            if (
                str(leave.get("employee_id")) == str(employee.get("id"))
                and leave.get("status") in ("Pending", "Approved")
            ):
                old_start = leave.get("from_date", leave.get("start_date"))
                old_end = leave.get("to_date", leave.get("end_date"))

                try:
                    old_start = date.fromisoformat(old_start)
                    old_end = date.fromisoformat(old_end)
                except (ValueError, TypeError):
                    continue

                if old_start <= end_date and old_end >= start_date:
                    overlap = True
                    break

        if overlap:
            st.error("In dates par pending ya approved leave pehle se hai.")
            return

        if leave_type == "Annual Leave":
            try:
                quota = int(settings.get("annual_leave_quota", 20))
            except (ValueError, TypeError):
                quota = 20

            annual_used = 0

            for leave in leaves:
                if (
                    str(leave.get("employee_id")) == str(employee.get("id"))
                    and leave.get("status") == "Approved"
                    and leave.get("leave_type") == "Annual Leave"
                ):
                    old_start = leave.get("from_date", leave.get("start_date"))
                    old_end = leave.get("to_date", leave.get("end_date"))

                    try:
                        old_start = date.fromisoformat(old_start)
                        old_end = date.fromisoformat(old_end)
                    except (ValueError, TypeError):
                        continue

                    if old_start.year == start_date.year:
                        annual_used += count_working_days(
                            old_start, old_end, working_days
                        )

            if annual_used + days > quota:
                st.error(
                    f"Annual leave quota exceed hoga. "
                    f"Used: {annual_used}/{quota} working days."
                )
                return

        numeric_ids = []

        for item in leaves:
            try:
                numeric_ids.append(int(item.get("id", 0)))
            except (ValueError, TypeError):
                continue

        next_id = max(numeric_ids, default=0) + 1

        leaves.append({
            "id": next_id,
            "request_id": str(next_id),
            "employee_id": employee.get("id"),
            "employee_name": employee.get("name"),
            "employee_email": employee.get("email"),
            "leave_type": leave_type,
            "from_date": start_date.isoformat(),
            "to_date": end_date.isoformat(),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": days,
            "reason": reason.strip(),
            "status": "Pending",
            "admin_comment": "",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })

        save_json(LEAVE_FILE, leaves)
        st.success("Leave request Admin ko bhej di gayi.")
        st.rerun()

    my_leaves = [
        item for item in leaves
        if str(item.get("employee_id")) == str(employee.get("id"))
    ]

    st.subheader("My Leave Requests")

    if my_leaves:
        st.dataframe(
            my_leaves,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Abhi koi leave request nahi hai.")


def show_employee_dashboard():
    email = st.session_state.get("employee_email", "")
    employee = next(
        (
            item for item in load_json(EMP_FILE, [])
            if str(item.get("email", "")).strip().lower() == email.lower()
            and str(item.get("status", "")).strip().lower() == "active"
        ),
        None,
    )

    if not employee:
        st.session_state["employee_email"] = None
        st.rerun()
        return

    st.title("👨‍💼 Employee Portal")
    st.success(f'Welcome, {employee.get("name", "Employee")}!')

    if st.button("Logout", key="employee_logout"):
        st.session_state["employee_email"] = None
        st.rerun()

    left, middle, right = st.columns(3)
    left.metric("Employee ID", employee.get("id", "—"))
    middle.metric("Department", employee.get("department", "—"))
    right.metric("Job Title", employee.get("job_title", "—"))

    with st.expander("My Profile", expanded=True):
        st.write("**Name:**", employee.get("name", "—"))
        st.write("**Email:**", employee.get("email", "—"))
        st.write("**Joining Date:**", employee.get("joining_date", "—"))
        st.write("**Status:**", employee.get("status", "—"))

    st.divider()
    show_attendance(employee)

    st.divider()
    show_leave_requests(employee)


def show_employee_portal():
    if "employee_email" not in st.session_state:
        st.session_state["employee_email"] = None

    if st.session_state["employee_email"]:
        show_employee_dashboard()
        return

    st.title("👨‍💼 Employee Portal")

    login_tab, register_tab = st.tabs(["🔐 Login", "📝 Register / Set Password"])

    with login_tab:
        employee_login()

    with register_tab:
        register_employee()


show_employee_portal()
