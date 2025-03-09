import matplotlib.pyplot as plt
import pandas as pd
import datetime

# Define project tasks
tasks = [
    ["Project Scope & Objectives", "2024-09-03", "2024-09-15", "Planning"],
    ["Resource Allocation", "2024-09-16", "2024-09-30", "Planning"],
    ["Market Research", "2024-10-01", "2024-10-14", "Research"],
    ["UI Wireframes & System Design", "2024-10-15", "2024-11-15", "Design"],
    ["User Authentication & Profiles", "2024-11-16", "2024-12-31", "Development"],
    ["Auction Listing & Bidding System", "2025-01-01", "2025-01-14", "Development"],
    ["Real-Time Updates & Price Prediction", "2025-01-15", "2025-02-28", "Development"],
    ["Functional & User Testing", "2025-03-01", "2025-03-20", "Testing"],
    ["Bug Fixing & Performance Optimization", "2025-03-21", "2025-04-06", "Testing"],
    ["Final Content & Marketing Preparation", "2025-04-07", "2025-04-16", "Deployment"],
    ["Cloud Deployment (AWS/DigitalOcean)", "2025-04-10", "2025-04-16", "Deployment"]
]

# Convert to DataFrame
df = pd.DataFrame(tasks, columns=["Task", "Start Date", "End Date", "Category"])
df["Start Date"] = pd.to_datetime(df["Start Date"])
df["End Date"] = pd.to_datetime(df["End Date"])
df["Duration"] = (df["End Date"] - df["Start Date"]).dt.days

# Define color mapping for categories
colors = {
    "Planning": "skyblue",
    "Research": "orange",
    "Design": "purple",
    "Development": "green",
    "Testing": "red",
    "Deployment": "brown"
}

# Create figure
fig, ax = plt.subplots(figsize=(10, 6))

# Plot each task
for i, row in df.iterrows():
    ax.barh(row["Task"], row["Duration"], left=row["Start Date"], color=colors[row["Category"]])

# Format chart
ax.set_xlabel("Date")
ax.set_ylabel("Task")
ax.set_title("Project Gantt Chart")
plt.xticks(rotation=45)
plt.grid(axis='x', linestyle="--", alpha=0.7)

# Show chart
plt.show()
