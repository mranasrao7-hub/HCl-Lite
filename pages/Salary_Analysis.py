
import streamlit as st
import pandas as pd
import plotly.express as px
from src.data_loader import load_data

st.set_page_config(
    page_title="Salary Analysis",
    page_icon="💰",
    layout="wide"
)

st.title("💰 Salary Analysis")
st.caption("Analyze employee salaries, departments and job roles.")

@st.cache_data
def get_data():
    return load_data()

try:
    data = get_data().copy()
except Exception as e:
    st.error(f"Dataset load nahi hua: {e}")
    st.stop()

# Dataset ke salary column ko identify karo
salary_col = next(
    (
        col for col in data.columns
        if col.lower() in ["monthlyincome", "monthly_income", "salary"]
    ),
    None
)

if salary_col is None:
    st.error("Dataset mein salary column nahi mila.")
    st.stop()

data[salary_col] = pd.to_numeric(data[salary_col], errors="coerce")
data = data.dropna(subset=[salary_col])

# Sidebar filters
st.sidebar.subheader("💰 Salary Filters")

if "Department" in data.columns:
    departments = sorted(data["Department"].dropna().unique())

    selected_departments = st.sidebar.multiselect(
        "Department",
        departments,
        default=departments
    )

    data = data[data["Department"].isin(selected_departments)]

if data.empty:
    st.warning("Selected filters ke liye salary records nahi mile.")
    st.stop()

min_salary = int(data[salary_col].min())
max_salary = int(data[salary_col].max())

if min_salary < max_salary:
    salary_range = st.sidebar.slider(
        "Monthly Salary Range",
        min_value=min_salary,
        max_value=max_salary,
        value=(min_salary, max_salary),
        step=100
    )

    data = data[
        data[salary_col].between(
            salary_range[0],
            salary_range[1]
        )
    ]

if data.empty:
    st.warning("Is salary range mein koi employee nahi mila.")
    st.stop()

# KPI cards
total_employees = len(data)
average_salary = data[salary_col].mean()
median_salary = data[salary_col].median()
highest_salary = data[salary_col].max()

c1, c2, c3, c4 = st.columns(4)

c1.metric("👥 Employees", f"{total_employees:,}")
c2.metric("💵 Average Salary", f"{average_salary:,.0f}")
c3.metric("📊 Median Salary", f"{median_salary:,.0f}")
c4.metric("🏆 Highest Salary", f"{highest_salary:,.0f}")

st.divider()

# Salary distribution
st.subheader("📊 Salary Distribution")

fig_distribution = px.histogram(
    data,
    x=salary_col,
    nbins=30,
    title="Distribution of Monthly Salaries",
    labels={salary_col: "Monthly Income"},
    color_discrete_sequence=["#38bdf8"],
    template="plotly_dark"
)

fig_distribution.update_layout(
    xaxis_title="Monthly Income",
    yaxis_title="Number of Employees"
)

st.plotly_chart(fig_distribution, use_container_width=True)

# Department and job role comparisons
left, right = st.columns(2)

with left:
    if "Department" in data.columns:
        department_salary = (
            data.groupby("Department")[salary_col]
            .mean()
            .reset_index()
            .sort_values(salary_col, ascending=False)
        )

        fig_department = px.bar(
            department_salary,
            x="Department",
            y=salary_col,
            color="Department",
            text_auto=".0f",
            title="Average Salary by Department",
            labels={salary_col: "Average Monthly Income"},
            template="plotly_dark"
        )

        fig_department.update_layout(showlegend=False)
        st.plotly_chart(
            fig_department,
            use_container_width=True
        )

with right:
    if "JobRole" in data.columns:
        role_salary = (
            data.groupby("JobRole")[salary_col]
            .mean()
            .reset_index()
            .sort_values(salary_col, ascending=True)
        )

        fig_role = px.bar(
            role_salary,
            x=salary_col,
            y="JobRole",
            orientation="h",
            color=salary_col,
            color_continuous_scale="Teal",
            title="Average Salary by Job Role",
            labels={
                salary_col: "Average Monthly Income",
                "JobRole": "Job Role"
            },
            template="plotly_dark"
        )

        st.plotly_chart(
            fig_role,
            use_container_width=True
        )

# Salary records
st.divider()
st.subheader("📋 Salary Records")

columns_to_show = [
    col for col in [
        "EmployeeNumber",
        "Department",
        "JobRole",
        "JobLevel",
        "MonthlyIncome",
        "YearsAtCompany",
        "Attrition"
    ]
    if col in data.columns
]

st.dataframe(
    data[columns_to_show].sort_values(
        salary_col,
        ascending=False
    ),
    use_container_width=True,
    hide_index=True,
    height=450
)

st.caption(
    "Salary figures are taken from the dataset's MonthlyIncome column."
)
