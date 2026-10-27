
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EMPLOYEE_FILE = DATA_DIR / "employees.json"
LEAVE_FILE = DATA_DIR / "leaves.json"
SETTINGS_FILE = DATA_DIR / "company_settings.json"

DEFAULT_WORKING_DAYS = [
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"
]


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
        st.error(f"File read nahi ho saki: {path.name}")
        return default.copy()


def save_json(path, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_file = path.with_suffix(".tmp")

    with open(temp_file, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    temp_file.replace(path)


def load_employees():
    return load_json(EMPLOYEE_FILE, [])


def load_settings():
    settings = load_json(SETTINGS_FILE, {})

    if not isinstance(settings, dict):
        settings = {}

    return {
        "annual_leave_quota": int(
            settings.get("annual_leave_quota", 20)
        ),
        "working_days": settings.get(
            "working_days", DEFAULT_WORKING_DAYS
        ),
    }


def parse_date(value):
    if not value:
        return None

    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def normalize_leave(leave):
    """Support both old Admin and Employee Portal leave field names."""
    item = dict(leave)

    item["id"] = item.get("id", item.get("request_id", ""))
    item["request_id"] = item.get("request_id", item["id"])

    item["from_date"] = item.get(
        "from_date", item.get("start_date", "")
    )
    item["to_date"] = item.get(
        "to_date", item.get("end_date", "")
    )

    item["start_date"] = item.get("start_date", item["from_date"])
    item["end_date"] = item.get("end_date", item["to_date"])

    item.setdefault("employee_name", "Unknown")
    item.setdefault("leave_type", "Other")
    item.setdefault("reason", "")
    item.setdefault("status", "Pending")
    item.setdefault("admin_comment", "")

    return item


def load_leaves():
    raw_leaves = load_json(LEAVE_FILE, [])
    return [
        normalize_leave(item)
        for item in raw_leaves
        if isinstance(item, dict)
    ]


def save_leaves(leaves):
    # Store both field-name formats for compatibility with old records
    # and the Employee Portal.
    compatible = []

    for leave in leaves:
        item = normalize_leave(leave)
        item["start_date"] = item["from_date"]
        item["end_date"] = item["to_date"]
        compatible.append(item)

    save_json(LEAVE_FILE, compatible)


def working_days(start, end, configured_days=None):
    """Count configured company working days, inclusive."""
    configured_days = configured_days or DEFAULT_WORKING_DAYS

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
        for name in configured_days
        if name in day_numbers
    }

    total = 0
    current = start

    while current <= end:
        if current.weekday() in allowed:
            total += 1

        current += timedelta(days=1)

    return total


def next_leave_id(leaves):
    ids = []

    for leave in leaves:
        try:
            ids.append(int(leave.get("id", 0)))
        except (ValueError, TypeError):
            continue

    return max(ids, default=0) + 1


def annual_leave_used(leaves, employee_id, year, company_days):
    total = 0

    for leave in leaves:
        if (
            str(leave.get("employee_id")) != str(employee_id)
            or leave.get("status") != "Approved"
            or leave.get("leave_type") != "Annual Leave"
        ):
            continue

        start = parse_date(leave.get("from_date"))
        end = parse_date(leave.get("to_date"))

        if not start or not end or end < start:
            continue

        # Count only the days within the requested calendar year.
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)
        clipped_start = max(start, year_start)
        clipped_end = min(end, year_end)

        if clipped_start <= clipped_end:
            total += working_days(
                clipped_start, clipped_end, company_days
            )

    return total


def has_overlapping_leave(leaves, employee_id, start, end):
    for leave in leaves:
        if (
            str(leave.get("employee_id")) != str(employee_id)
            or leave.get("status") not in ("Pending", "Approved")
        ):
            continue

        old_start = parse_date(leave.get("from_date"))
        old_end = parse_date(leave.get("to_date"))

        if old_start and old_end and old_start <= end and old_end >= start:
            return True

    return False


def show_leave_manager():
    user = st.session_state.get("user")

    if not isinstance(user, dict):
        st.warning("Please Admin account se login karo.")
        st.stop()

    if str(user.get("role", "")).strip().lower() != "admin":
        st.error("Sirf Admin leave requests manage kar sakta hai.")
        st.stop()

    st.title("🏖️ Leave Management")
    st.caption("Review employee requests, approve leave and export reports.")

    employees = [
        employee for employee in load_employees()
        if str(employee.get("status", "Active")).strip().lower() == "active"
    ]

    leaves = load_leaves()
    settings = load_settings()
    company_days = settings["working_days"]
    quota = settings["annual_leave_quota"]

    pending = sum(item.get("status") == "Pending" for item in leaves)
    approved = sum(item.get("status") == "Approved" for item in leaves)
    rejected = sum(item.get("status") == "Rejected" for item in leaves)

    c1, c2, c3 = st.columns(3)
    c1.metric("Pending Requests", pending)
    c2.metric("Approved Requests", approved)
    c3.metric("Rejected Requests", rejected)

    create_tab, review_tab, summary_tab = st.tabs(
        ["➕ Create Request", "📋 Review Requests", "📊 Leave Summary"]
    )

    with create_tab:
        if not employees:
            st.info("Abhi koi active employee available nahi hai.")
        else:
            options = {
                f'{item.get("name", "Unknown")} — {item.get("email", "")}': item
                for item in employees
            }

            with st.form("admin_create_leave_form"):
                selected = st.selectbox("Employee", list(options.keys()))
                leave_type = st.selectbox(
                    "Leave Type",
                    ["Annual Leave", "Sick Leave", "Personal Leave", "Other"],
                )
                start_date = st.date_input(
                    "From Date", value=date.today(), key="admin_leave_start"
                )
                end_date = st.date_input(
                    "To Date", value=date.today(), key="admin_leave_end"
                )
                reason = st.text_area("Reason")
                submit = st.form_submit_button("Create Leave Request")

            if submit:
                employee = options[selected]

                if end_date < start_date:
                    st.error("To Date, From Date se pehle nahi ho sakti.")
                elif not reason.strip():
                    st.error("Leave ki reason enter karo.")
                else:
                    days = working_days(
                        start_date, end_date, company_days
                    )

                    if days == 0:
                        st.error("Selected dates mein working day nahi hai.")
                    elif has_overlapping_leave(
                        leaves, employee.get("id"), start_date, end_date
                    ):
                        st.error("Is employee ki dates par leave pehle se pending ya approved hai.")
                    else:
                        used = annual_leave_used(
                            leaves,
                            employee.get("id"),
                            start_date.year,
                            company_days,
                        )

                        if (
                            leave_type == "Annual Leave"
                            and used + days > quota
                        ):
                            st.error(
                                f"Annual leave quota exceed hoga. "
                                f"Used: {used}/{quota} working days."
                            )
                        else:
                            leave_id = next_leave_id(leaves)

                            leaves.append({
                                "id": leave_id,
                                "request_id": str(leave_id),
                                "employee_id": employee.get("id"),
                                "employee_name": employee.get("name", ""),
                                "employee_email": employee.get("email", ""),
                                "leave_type": leave_type,
                                "from_date": start_date.isoformat(),
                                "to_date": end_date.isoformat(),
                                "start_date": start_date.isoformat(),
                                "end_date": end_date.isoformat(),
                                "days": days,
                                "reason": reason.strip(),
                                "status": "Pending",
                                "admin_comment": "",
                                "created_at": date.today().isoformat(),
                            })

                            save_leaves(leaves)
                            st.success("Leave request create ho gayi.")
                            st.rerun()

    with review_tab:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "Pending", "Approved", "Rejected"],
            key="admin_leave_status_filter",
        )

        filtered = [
            item for item in leaves
            if status_filter == "All"
            or item.get("status") == status_filter
        ]

        if not filtered:
            st.info("Is status ke liye koi leave request nahi hai.")

        for leave in filtered:
            leave_id = leave.get("id", leave.get("request_id", ""))
            employee_id = leave.get("employee_id")
            start = leave.get("from_date", "")
            end = leave.get("to_date", "")

            with st.expander(
                f'#{leave_id} — {leave.get("employee_name", "Unknown")} '
                f'| {leave.get("leave_type", "Other")} '
                f'| {leave.get("status", "Pending")}'
            ):
                st.write("**Employee ID:**", employee_id)
                st.write("**Employee email:**", leave.get("employee_email", "—"))
                st.write(f"**Dates:** {start} to {end}")
                st.write("**Working days:**", leave.get("days", "—"))
                st.write("**Reason:**", leave.get("reason", ""))

                if leave.get("admin_comment"):
                    st.write("**Admin comment:**", leave["admin_comment"])

                if leave.get("status") == "Pending":
                    comment = st.text_input(
                        "Admin Comment",
                        key=f"leave_comment_{leave_id}",
                    )

                    approve_col, reject_col = st.columns(2)

                    with approve_col:
                        if st.button(
                            "✅ Approve",
                            key=f"approve_leave_{leave_id}",
                            use_container_width=True,
                        ):
                            latest = load_leaves()
                            target = next(
                                (
                                    item for item in latest
                                    if str(item.get("id")) == str(leave_id)
                                    or str(item.get("request_id")) == str(leave_id)
                                ),
                                None,
                            )

                            if target is None:
                                st.error("Leave request nahi mili.")
                            elif target.get("status") != "Pending":
                                st.warning("Is request par pehle action ho chuka hai.")
                            else:
                                target_start = parse_date(target.get("from_date"))
                                target_end = parse_date(target.get("to_date"))

                                if not target_start or not target_end:
                                    st.error("Leave dates invalid hain.")
                                else:
                                    used = annual_leave_used(
                                        latest,
                                        target.get("employee_id"),
                                        target_start.year,
                                        company_days,
                                    )
                                    days = working_days(
                                        target_start, target_end, company_days
                                    )

                                    if (
                                        target.get("leave_type") == "Annual Leave"
                                        and used + days > quota
                                    ):
                                        st.error(
                                            f"Quota exceed hoga. Used: {used}/{quota}."
                                        )
                                    else:
                                        target["status"] = "Approved"
                                        target["admin_comment"] = comment.strip()
                                        save_leaves(latest)
                                        st.success("Leave approve ho gayi.")
                                        st.rerun()

                    with reject_col:
                        if st.button(
                            "❌ Reject",
                            key=f"reject_leave_{leave_id}",
                            use_container_width=True,
                        ):
                            latest = load_leaves()
                            target = next(
                                (
                                    item for item in latest
                                    if str(item.get("id")) == str(leave_id)
                                    or str(item.get("request_id")) == str(leave_id)
                                ),
                                None,
                            )

                            if target is None:
                                st.error("Leave request nahi mili.")
                            elif target.get("status") != "Pending":
                                st.warning("Is request par pehle action ho chuka hai.")
                            else:
                                target["status"] = "Rejected"
                                target["admin_comment"] = comment.strip()
                                save_leaves(latest)
                                st.warning("Leave reject ho gayi.")
                                st.rerun()

    with summary_tab:
        st.caption(f"Annual leave quota configured in Company Settings: {quota} working days.")

        if leaves:
            df = pd.DataFrame(leaves)
            st.dataframe(df, use_container_width=True, hide_index=True)

            st.download_button(
                "Download Leave Report CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="leave_report.csv",
                mime="text/csv",
            )
        else:
            st.info("Leave summary ke liye abhi records nahi hain.")


# The Streamlit page should call show_leave_manager().
