
import streamlit as st
import pandas as pd
import plotly.express as px
from src.data_loader import load_data

st.set_page_config(
    page_title="HR Analytics | Executive Dashboard",
    page_icon="📊",
    layout="wide"
)

from src.auth import load_users, create_admin, authenticate

# Login session
if "user" not in st.session_state:
    st.session_state.user = None

users = load_users()
admin_exists = any(user.get("role") == "Admin" for user in users)

st.sidebar.title("HCM Lite")

if st.session_state.user is None:
    st.title("HCM Lite — HR Management System")

    if not admin_exists:
        st.subheader("First-Time Company Setup")

        with st.form("admin_setup"):
            company = st.text_input("Company Name")
            name = st.text_input("Admin Full Name")
            email = st.text_input("Admin Email")
            password = st.text_input("Password", type="password")
            confirm = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Create Admin Account")

            if submitted:
                if not all([company.strip(), name.strip(), email.strip(),
                            password, confirm]):
                    st.error("Saari fields fill karo.")
                elif password != confirm:
                    st.error("Passwords match nahi karte.")
                elif len(password) < 8:
                    st.error("Password kam az kam 8 characters ka rakho.")
                else:
                    success, message = create_admin(
                        company, name, email, password
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

    else:
        st.subheader("Admin Login")

        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                user = authenticate(email, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Email ya password ghalat hai.")

    st.stop()

user = st.session_state.user

st.sidebar.write(f"Logged in: **{user['name']}**")
st.sidebar.write(f"Role: **{user['role']}**")

if st.sidebar.button("Logout"):
    st.session_state.user = None
    st.rerun()

if user["role"] != "Admin":
    st.warning("Employee dashboard abhi setup nahi hua.")
    st.stop()

st.markdown("""
<style>
.stApp {
    background: #0B1220;
    color: #E5EDF8;
}

[data-testid="stSidebar"] {
    background: #111C2F;
    border-right: 1px solid #26364D;
}

h1, h2, h3 {
    color: #38BDF8;
}

[data-testid="stMetric"] {
    background: #111C2F;
    border: 1px solid #26364D;
    border-radius: 14px;
    padding: 18px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
}

[data-testid="stMetricLabel"] {
    color: #A8B8CC;
}

[data-testid="stMetricValue"] {
    color: #FFFFFF;
    font-weight: 700;
}

.stButton > button {
    background: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
}

.stButton > button:hover {
    background: #1D4ED8;
    color: #FFFFFF;
    border: 1px solid #60A5FA;
}

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    border: 1px solid #26364D;
    border-radius: 10px;
}

hr {
    border-color: #26364D;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def get_data():
    return load_data()


st.title("📊 HR Analytics")
st.caption("Executive Overview | Workforce • Salary • Retention")

try:
    data = get_data().copy()
except Exception as e:
    st.error(f"Dataset load nahi hua: {e}")
    st.stop()

# Sidebar filters
st.sidebar.title("🎛️ Dashboard Filters")

filtered = data.copy()

if "Department" in filtered.columns:
    departments = sorted(filtered["Department"].dropna().unique())
    selected_departments = st.sidebar.multiselect(
        "Department",
        departments,
        default=departments
    )
    filtered = filtered[
        filtered["Department"].isin(selected_departments)
    ]

if "Gender" in filtered.columns:
    genders = sorted(filtered["Gender"].dropna().unique())
    selected_genders = st.sidebar.multiselect(
        "Gender",
        genders,
        default=genders
    )
    filtered = filtered[filtered["Gender"].isin(selected_genders)]

if "Attrition" in filtered.columns:
    statuses = sorted(filtered["Attrition"].dropna().unique())
    selected_statuses = st.sidebar.multiselect(
        "Attrition Status",
        statuses,
        default=statuses
    )
    filtered = filtered[
        filtered["Attrition"].isin(selected_statuses)
    ]

if filtered.empty:
    st.warning("In filters ke mutabiq koi employee record nahi mila.")
    st.stop()

# KPI calculations
employee_count = len(filtered)

avg_age = (
    filtered["Age"].mean()
    if "Age" in filtered.columns else None
)

avg_salary = (
    pd.to_numeric(filtered["MonthlyIncome"], errors="coerce").mean()
    if "MonthlyIncome" in filtered.columns else None
)

left_rate = (
    filtered["Attrition"]
    .astype(str).str.strip().str.lower().eq("yes").mean() * 100
    if "Attrition" in filtered.columns else None
)

# KPI cards
k1, k2, k3, k4 = st.columns(4)

k1.metric("👥 Employees", f"{employee_count:,}")
k2.metric(
    "🎂 Average Age",
    f"{avg_age:.1f}" if avg_age is not None else "N/A"
)
k3.metric(
    "💰 Average Monthly Income",
    f"{avg_salary:,.0f}" if avg_salary is not None else "N/A"
)
k4.metric(
    "📉 Attrition Rate",
    f"{left_rate:.1f}%" if left_rate is not None else "N/A"
)

st.divider()

# Main charts
st.subheader("📈 Workforce Insights")

left, right = st.columns(2)

with left:
    if "Department" in filtered.columns:
        dept_counts = (
            filtered["Department"]
            .value_counts()
            .rename_axis("Department")
            .reset_index(name="Employees")
        )

        fig = px.bar(
            dept_counts,
            x="Department",
            y="Employees",
            color="Department",
            text="Employees",
            title="Workforce by Department",
            template="plotly_dark"
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

with right:
    if "Attrition" in filtered.columns:
        attrition_counts = (
            filtered["Attrition"]
            .value_counts()
            .rename_axis("Status")
            .reset_index(name="Employees")
        )

        fig = px.pie(
            attrition_counts,
            names="Status",
            values="Employees",
            hole=0.5,
            title="Employee Retention Overview",
            color="Status",
            color_discrete_map={
                "Yes": "#ef4444",
                "No": "#22c55e"
            },
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)

# Salary and overtime
st.divider()
st.subheader("💼 Salary & Work Patterns")

left, right = st.columns(2)

with left:
    if "Department" in filtered.columns and "MonthlyIncome" in filtered.columns:
        salary_data = filtered.copy()
        salary_data["MonthlyIncome"] = pd.to_numeric(
            salary_data["MonthlyIncome"], errors="coerce"
        )

        salary_summary = (
            salary_data.groupby("Department")["MonthlyIncome"]
            .mean()
            .reset_index()
        )

        fig = px.bar(
            salary_summary,
            x="Department",
            y="MonthlyIncome",
            color="Department",
            text_auto=".0f",
            title="Average Monthly Income by Department",
            template="plotly_dark"
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

with right:
    if "OverTime" in filtered.columns:
        overtime_data = (
            filtered["OverTime"]
            .value_counts()
            .rename_axis("Overtime")
            .reset_index(name="Employees")
        )

        fig = px.pie(
            overtime_data,
            names="Overtime",
            values="Employees",
            hole=0.45,
            title="Overtime Distribution",
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)

# Important insights
st.divider()
st.subheader("💡 Key Insights")

if "Department" in filtered.columns:
    largest_department = filtered["Department"].value_counts()

    if not largest_department.empty:
        st.info(
            f"Largest workforce department: **{largest_department.index[0]}** "
            f"({largest_department.iloc[0]} employees in the current selection)."
        )

if "Attrition" in filtered.columns and "Department" in filtered.columns:
    temp = filtered.copy()
    temp["_left"] = (
        temp["Attrition"].astype(str).str.lower().eq("yes")
    )

    department_attrition = (
        temp.groupby("Department")["_left"]
        .mean()
        .mul(100)
        .sort_values(ascending=False)
    )

    if not department_attrition.empty:
        st.info(
            f"Highest department attrition rate in this selection: "
            f"**{department_attrition.index[0]}** "
            f"({department_attrition.iloc[0]:.1f}%)."
        )

if "OverTime" in filtered.columns and "Attrition" in filtered.columns:
    overtime_rate = (
        filtered.groupby("OverTime")["Attrition"]
        .apply(
            lambda values:
            values.astype(str).str.lower().eq("yes").mean() * 100
        )
    )

    if "Yes" in overtime_rate.index and "No" in overtime_rate.index:
        st.info(
            f"Attrition among employees with overtime: "
            f"**{overtime_rate['Yes']:.1f}%**. "
            f"Without overtime: **{overtime_rate['No']:.1f}%**. "
            "This is an association in the dataset, not proof that overtime causes attrition."
        )

# Dataset preview
st.divider()
st.subheader("📋 Employee Dataset")

search = st.text_input(
    "🔎 Search employee records",
    placeholder="Search by department, job role, gender..."
)

table = filtered.copy()

if search.strip():
    matches = table.astype(str).apply(
        lambda col: col.str.contains(
            search.strip(), case=False, regex=False, na=False
        )
    ).any(axis=1)
    table = table[matches]

st.caption(f"{len(table):,} records found")

st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
    height=450
)

st.caption(
    "Built with Python, Pandas, Streamlit and Plotly | HR Analytics Hackathon Project"
)
