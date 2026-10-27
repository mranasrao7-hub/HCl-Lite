
import streamlit as st
import pandas as pd
import plotly.express as px
from src.data_loader import load_data

st.set_page_config(
    page_title="Department Analysis",
    page_icon="🏢",
    layout="wide"
)

st.title("🏢 Department Analysis")
st.caption("Compare workforce size, salary and attrition across departments.")

@st.cache_data
def get_data():
    return load_data()

try:
    data = get_data().copy()
except Exception as e:
    st.error(f"Dataset load nahi hua: {e}")
    st.stop()

required_columns = ["Department"]

if not all(col in data.columns for col in required_columns):
    st.error("Dataset mein Department column nahi mila.")
    st.stop()

# Sidebar filter
st.sidebar.subheader("🏢 Department Filters")

departments = sorted(data["Department"].dropna().unique().tolist())

selected_departments = st.sidebar.multiselect(
    "Select departments",
    departments,
    default=departments
)

data = data[data["Department"].isin(selected_departments)]

if data.empty:
    st.warning("Selected departments ke liye records nahi mile.")
    st.stop()

# Department summary
summary = (
    data.groupby("Department")
    .agg(Employee_Count=("Department", "size"))
    .reset_index()
)

if "MonthlyIncome" in data.columns:
    salary_summary = (
        data.groupby("Department")["MonthlyIncome"]
        .mean()
        .reset_index(name="Average_Salary")
    )
    summary = summary.merge(salary_summary, on="Department")

if "Attrition" in data.columns:
    attrition_data = data.copy()
    attrition_data["Left_Company"] = (
        attrition_data["Attrition"]
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("yes")
    )

    attrition_summary = (
        attrition_data.groupby("Department")["Left_Company"]
        .mean()
        .mul(100)
        .reset_index(name="Attrition_Rate")
    )
    summary = summary.merge(attrition_summary, on="Department")

# KPI cards
c1, c2, c3, c4 = st.columns(4)

c1.metric("🏢 Departments", summary["Department"].nunique())
c2.metric("👥 Employees", f"{len(data):,}")

if "MonthlyIncome" in data.columns:
    c3.metric(
        "💰 Overall Average Salary",
        f"{data['MonthlyIncome'].mean():,.0f}"
    )
else:
    c3.metric("💰 Average Salary", "N/A")

if "Attrition" in data.columns:
    rate = (
        data["Attrition"].astype(str).str.lower().eq("yes").mean()
        * 100
    )
    c4.metric("📉 Attrition Rate", f"{rate:.1f}%")
else:
    c4.metric("📉 Attrition Rate", "N/A")

st.divider()

# Employee count by department
left, right = st.columns(2)

with left:
    employee_chart = px.bar(
        summary.sort_values("Employee_Count", ascending=False),
        x="Department",
        y="Employee_Count",
        color="Department",
        text="Employee_Count",
        title="Employees by Department",
        template="plotly_dark"
    )
    employee_chart.update_layout(showlegend=False)
    st.plotly_chart(employee_chart, use_container_width=True)

with right:
    if "Average_Salary" in summary.columns:
        salary_chart = px.bar(
            summary.sort_values("Average_Salary", ascending=False),
            x="Department",
            y="Average_Salary",
            color="Department",
            text_auto=".0f",
            title="Average Monthly Salary by Department",
            template="plotly_dark"
        )
        salary_chart.update_layout(showlegend=False)
        st.plotly_chart(salary_chart, use_container_width=True)

# Attrition analysis
st.divider()
st.subheader("📉 Department Attrition Analysis")

if "Attrition_Rate" in summary.columns:
    attrition_chart = px.bar(
        summary.sort_values("Attrition_Rate", ascending=False),
        x="Department",
        y="Attrition_Rate",
        color="Attrition_Rate",
        text_auto=".1f",
        title="Attrition Rate by Department",
        labels={"Attrition_Rate": "Attrition Rate (%)"},
        color_continuous_scale="Reds",
        template="plotly_dark"
    )

    st.plotly_chart(attrition_chart, use_container_width=True)
else:
    st.info("Attrition column available nahi hai.")

# Job roles by department
st.divider()
st.subheader("👔 Job Role Distribution")

if "JobRole" in data.columns:
    role_data = (
        data.groupby(["Department", "JobRole"])
        .size()
        .reset_index(name="Employees")
    )

    role_chart = px.bar(
        role_data,
        x="JobRole",
        y="Employees",
        color="Department",
        barmode="group",
        title="Job Roles Across Departments",
        template="plotly_dark"
    )

    role_chart.update_layout(xaxis_title="Job Role")
    st.plotly_chart(role_chart, use_container_width=True)
else:
    st.info("JobRole column available nahi hai.")

# Summary table
st.divider()
st.subheader("📋 Department Summary")

display_summary = summary.rename(columns={
    "Employee_Count": "Employees",
    "Average_Salary": "Average Monthly Salary",
    "Attrition_Rate": "Attrition Rate (%)"
})

st.dataframe(
    display_summary,
    use_container_width=True,
    hide_index=True
)

st.caption("Department insights are calculated from the selected employee records.")
