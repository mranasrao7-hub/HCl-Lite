
import json
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EMP_FILE = DATA_DIR / "employees.json"


def load_employees():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not EMP_FILE.exists():
        save_employees([])
        return []

    try:
        with open(EMP_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            st.error("employees.json ka format invalid hai.")
            return []

        return data

    except (json.JSONDecodeError, OSError):
        st.error("employees.json read nahi ho rahi.")
        return []


def save_employees(employees):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = EMP_FILE.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(employees, file, indent=4, ensure_ascii=False)

    temp_file.replace(EMP_FILE)


def next_employee_id(employees):
    ids = []

    for employee in employees:
        try:
            ids.append(int(employee.get("id", 0)))
        except (ValueError, TypeError):
            continue

    return max(ids, default=0) + 1


def account_label(employee):
    if employee.get("password_hash") and employee.get("password_salt"):
        return "Registered"

    return "No login credentials"


def show_employee_list(employees=None):
    if employees is None:
        employees = load_employees()

    st.subheader("Employee Directory")

    active_employees = [
        employee for employee in employees
        if str(employee.get("status", "Active")).strip().lower() == "active"
    ]

    st.caption(f"Active employees: {len(active_employees)}")

    if not active_employees:
        st.info("Abhi koi approved/active employee nahi hai.")
        return

    rows = [
        {
            "Employee ID": employee.get("id", ""),
            "Name": employee.get("name", ""),
            "Email": employee.get("email", ""),
            "Department": employee.get("department", ""),
            "Job Title": employee.get("job_title", ""),
            "Status": employee.get("status", "Active"),
            "Account": account_label(employee),
        }
        for employee in active_employees
    ]

    search = st.text_input(
        "Search employees",
        placeholder="Name, email, department ya job title...",
        key="employee_directory_search",
    )

    department_options = sorted({
        str(employee.get("department", ""))
        for employee in active_employees
        if employee.get("department")
    })

    selected_department = st.selectbox(
        "Filter by department",
        ["All Departments"] + department_options,
        key="employee_directory_department",
    )

    table = pd.DataFrame(rows)

    if search.strip():
        searchable = table.astype(str).apply(
            lambda column: column.str.contains(
                search.strip(),
                case=False,
                regex=False,
                na=False,
            )
        ).any(axis=1)

        table = table[searchable]

    if selected_department != "All Departments":
        table = table[table["Department"] == selected_department]

    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(f"Showing {len(table)} employee(s).")


def show_employee_manager():
    user = st.session_state.get("user")

    if not isinstance(user, dict) or (
        str(user.get("role", "")).strip().lower() != "admin"
    ):
        st.error("Sirf Admin employee management access kar sakta hai.")
        st.stop()

    st.title("Employee Management")
    st.caption("Review registrations and manage employee records.")

    employees = load_employees()

    pending = [
        employee for employee in employees
        if str(employee.get("status", "")).strip().lower()
        == "pending approval"
    ]

    active = [
        employee for employee in employees
        if str(employee.get("status", "Active")).strip().lower() == "active"
    ]

    rejected = [
        employee for employee in employees
        if str(employee.get("status", "")).strip().lower() == "rejected"
    ]

    col1, col2, col3 = st.columns(3)
    col1.metric("Pending Requests", len(pending))
    col2.metric("Active Employees", len(active))
    col3.metric("Rejected Requests", len(rejected))

    st.divider()

    # Registration approval
    st.subheader("Registration Requests")

    if not pending:
        st.info("Koi pending registration request nahi hai.")
    else:
        for employee in pending:
            employee_id = employee.get("id")
            name = employee.get("name", "Unknown")
            email = employee.get("email", "")

            with st.expander(
                f"#{employee_id} — {name} ({email})",
                expanded=True,
            ):
                st.write("**Department:**", employee.get("department", "—"))
                st.write("**Job Title:**", employee.get("job_title", "—"))
                st.write("**Registered At:**", employee.get("registered_at", "—"))

                approve_col, reject_col = st.columns(2)

                with approve_col:
                    if st.button(
                        "Approve",
                        key=f"approve_employee_{employee_id}",
                        use_container_width=True,
                    ):
                        latest = load_employees()

                        target = next(
                            (
                                item for item in latest
                                if str(item.get("id")) == str(employee_id)
                            ),
                            None,
                        )

                        if target is None:
                            st.error("Employee record nahi mila.")
                        elif str(target.get("status", "")).lower() != "pending approval":
                            st.warning("Is request par pehle hi action ho chuka hai.")
                        else:
                            target["status"] = "Active"
                            target["approved_at"] = pd.Timestamp.now().isoformat()
                            save_employees(latest)
                            st.success(f"{name} ka account approve ho gaya.")
                            st.rerun()

                with reject_col:
                    if st.button(
                        "Reject",
                        key=f"reject_employee_{employee_id}",
                        use_container_width=True,
                    ):
                        latest = load_employees()

                        target = next(
                            (
                                item for item in latest
                                if str(item.get("id")) == str(employee_id)
                            ),
                            None,
                        )

                        if target is None:
                            st.error("Employee record nahi mila.")
                        elif str(target.get("status", "")).lower() != "pending approval":
                            st.warning("Is request par pehle hi action ho chuka hai.")
                        else:
                            target["status"] = "Rejected"
                            target["rejected_at"] = pd.Timestamp.now().isoformat()
                            save_employees(latest)
                            st.warning(f"{name} ki request reject ho gayi.")
                            st.rerun()

    st.divider()

    # Admin can still add an employee manually
    with st.expander("➕ Add Employee Manually", expanded=False):
        with st.form("add_employee_form_updated"):
            name = st.text_input("Full Name")
            email = st.text_input("Company Email")
            department = st.text_input("Department")
            job_title = st.text_input("Job Title")
            salary = st.number_input(
                "Monthly Salary",
                min_value=0.0,
                step=1000.0,
            )
            joining_date = st.date_input("Joining Date")
            submit = st.form_submit_button("Add Employee")

        if submit:
            name = name.strip()
            email = email.strip().lower()
            department = department.strip()
            job_title = job_title.strip()

            if not all([name, email, department, job_title]):
                st.error("Name, email, department aur job title required hain.")
            elif "@" not in email or "." not in email.rsplit("@", 1)[-1]:
                st.error("Valid email address enter karo.")
            elif any(
                str(item.get("email", "")).strip().lower() == email
                for item in load_employees()
            ):
                st.error("Ye email pehle se registered hai.")
            else:
                latest = load_employees()

                latest.append({
                    "id": next_employee_id(latest),
                    "name": name,
                    "email": email,
                    "department": department,
                    "job_title": job_title,
                    "monthly_salary": salary,
                    "joining_date": str(joining_date),
                    "status": "Active",
                })

                save_employees(latest)
                st.success("Employee record add ho gaya.")
                st.rerun()

    st.divider()

    # Active directory
    show_employee_list(load_employees())


