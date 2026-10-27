import streamlit as st
import pandas as pd
import plotly.express as px
from src.data_loader import load_data

st.set_page_config(
    page_title="Employee Analysis",
    page_icon="👥",
    layout="wide"
)

st.title("👥 Employee Analysis")
st.caption("Explore employee demographics, job roles and attrition.")

# Load dataset
@st.cache_data
def get_data():
    return load_data()

try:
    df = get_data().copy()
except Exception as e:
    st.error(f"Dataset load nahi hua: {e}")
    st.stop()

# Sidebar filters
st.sidebar.subheader("Employee Filters")

if "Department" in df.columns:
    departments = sorted(df["Department"].dropna().unique())
    selected_departments = st.sidebar.multiselect(
        "Department",
        departments,
        default=departments
    )
    df = df[df["Department"].isin(selected_departments)]

if "Gender" in df.columns:
    genders = sorted(df["Gender"].dropna().unique())
    selected_genders = st.sidebar.multiselect(
        "Gender",
        genders,
        default=genders
    )
    df = df[df["Gender"].isin(selected_genders)]

if "Age" in df.columns and not df.empty:
    min_age = int(df["Age"].min())
    max_age = int(df["Age"].max())

    if min_age < max_age:
        age_range = st.sidebar.slider(
            "Age Range",
            min_value=min_age,
            max_value=max_age,
            value=(min_age, max_age)
        )
        df = df[df["Age"].between(*age_range)]

# KPI cards
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Employees", f"{len(df):,}")

if "Age" in df.columns and not df.empty:
    c2.metric("Average Age", f"{df['Age'].mean():.1f}")
else:
    c2.metric("Average Age", "N/A")

if "Gender" in df.columns:
    c3.metric(
        "Gender Categories",
        df["Gender"].nunique()
    )
else:
    c3.metric("Gender Categories", "N/A")

if "Attrition" in df.columns and not df.empty:
    rate = (
        df["Attrition"].astype(str).str.lower().eq("yes").mean()
        * 100
    )
    c4.metric("Attrition Rate", f"{rate:.1f}%")
else:
    c4.metric("Attrition Rate", "N/A")

st.divider()

if df.empty:
    st.warning("Selected filters ke liye koi employee record nahi mila.")
    st.stop()

# Charts
left, right = st.columns(2)

with left:
    if "Age" in df.columns:
        fig_age = px.histogram(
            df,
            x="Age",
            nbins=15,
            title="Employee Age Distribution",
            color_discrete_sequence=["#38bdf8"],
            template="plotly_dark"
        )
        fig_age.update_layout(
            xaxis_title="Age",
            yaxis_title="Number of Employees"
        )
        st.plotly_chart(fig_age, use_container_width=True)

with right:
    if "Gender" in df.columns:
        gender_data = (
            df["Gender"].value_counts()
            .rename_axis("Gender")
            .reset_index(name="Employees")
        )

        fig_gender = px.pie(
            gender_data,
            names="Gender",
            values="Employees",
            title="Employees by Gender",
            hole=0.45,
            template="plotly_dark"
        )
        st.plotly_chart(fig_gender, use_container_width=True)

left, right = st.columns(2)

with left:
    if "JobRole" in df.columns:
        role_data = (
            df["JobRole"].value_counts()
            .reset_index()
        )
        role_data.columns = ["Job Role", "Employees"]

        fig_roles = px.bar(
            role_data,
            x="Employees",
            y="Job Role",
            orientation="h",
            title="Employees by Job Role",
            color="Employees",
            color_continuous_scale="Blues",
            template="plotly_dark"
        )
        fig_roles.update_layout(
            yaxis={"categoryorder": "total ascending"}
        )
        st.plotly_chart(fig_roles, use_container_width=True)

with right:
    if "Attrition" in df.columns:
        attrition_data = (
            df["Attrition"].value_counts()
            .rename_axis("Attrition")
            .reset_index(name="Employees")
        )

        fig_attrition = px.pie(
            attrition_data,
            names="Attrition",
            values="Employees",
            title="Employee Attrition",
            color="Attrition",
            color_discrete_map={
                "Yes": "#ef4444",
                "No": "#22c55e"
            },
            template="plotly_dark"
        )
        st.plotly_chart(fig_attrition, use_container_width=True)

# Employee records
st.divider()
st.subheader("📋 Employee Records")

search = st.text_input(
    "🔎 Search employee",
    placeholder="Search by department, job role, gender..."
)

table = df.copy()

if search.strip():
    matches = table.astype(str).apply(
        lambda col: col.str.contains(
            search.strip(),
            case=False,
            regex=False,
            na=False
        )
    ).any(axis=1)

    table = table[matches]

preferred = [
    "EmployeeNumber",
    "Age",
    "Gender",
    "Department",
    "JobRole",
    "MonthlyIncome",
    "Attrition",
    "YearsAtCompany"
]

first = [col for col in preferred if col in table.columns]
other = [col for col in table.columns if col not in first]
table = table[first + other]

st.caption(f"{len(table):,} employee records found")

st.dataframe(
    table,
    use_container_width=True,
    hide_index=True,
    height=450
)

st.caption("HR Analytics Dashboard | Employee Analysis")
