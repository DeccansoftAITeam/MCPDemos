# Institute MCP Server — Setup & Testing Guide

## Project Structure

```
institute-mcp/
├── main.py           ← FastMCP server (Tools, Resources, Prompts)
├── database.py       ← SQLAlchemy models
├── seed_data.py      ← Sample data for the DB
├── requirements.txt
└── institute.db      ← SQLite DB (auto-created on first run)
```

---

## Step 1 — Create a Virtual Environment

```bash
cd institute-mcp
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

---

## Step 2 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Step 3 — Seed the Database

```bash
python seed_data.py
```

Expected output:
```
Database seeded successfully!
```

This creates `institute.db` with:
- 4 Courses
- 4 Faculty members
- 5 Batches
- 5 Students
- 6 Enrollments

---

## Step 4 — Run with MCP Inspector

MCP Inspector is a browser-based UI to test your MCP server interactively.

```bash
npx @modelcontextprotocol/inspector python main.py
```

First run will prompt to install `@modelcontextprotocol/inspector` — press **y** to confirm.

It will open: **http://localhost:5173**

---

## Step 5 — Test in MCP Inspector

### Testing Tools

Go to the **Tools** tab and test each tool:

| Tool | Sample Input |
|------|-------------|
| `add_student` | name: "Vikram Shah", email: "vikram@gmail.com", phone: "9000000001" |
| `enroll_student` | student_id: 6, batch_id: 2 |
| `add_batch` | course_id: 2, faculty_id: 2, start_date: "2026-08-01", end_date: "2026-10-24", schedule: "Mon/Wed 6pm-9pm" |
| `search_students` | query: "arjun" |
| `get_batch_students` | batch_id: 1 |

---

### Testing Resources

Go to the **Resources** tab — you will see all static resources listed:

| URI | Returns |
|-----|---------|
| `institute://courses` | All courses |
| `institute://faculty` | All faculty |
| `institute://students` | All students |
| `institute://batches/active` | All active batches |

Click any resource to fetch and view its content.

---

### Testing Resource Templates

In the **Resources** tab, you will also see Resource Templates listed separately:

| URI Template | Example URI to fetch |
|---|---|
| `institute://courses/{course_id}` | `institute://courses/1` |
| `institute://students/{student_id}` | `institute://students/1` |
| `institute://faculty/{faculty_id}` | `institute://faculty/2` |
| `institute://batches/{batch_id}` | `institute://batches/1` |

Enter the full URI with the ID substituted to fetch the resource.

---

### Testing Prompts

Go to the **Prompts** tab and test each prompt:

**student_progress_report**
```
student_name  : Arjun Mehta
course_title  : Python Full Stack
batch_schedule: Mon/Wed/Fri 10am-1pm
progress_notes: Completed modules 1-4, strong in OOP, needs improvement in Django REST framework
```

**batch_announcement**
```
course_title: Data Science with Python
start_date  : 2026-08-01
faculty_name: Priya Sharma
schedule    : Tue/Thu 2pm-5pm
fees        : ₹20,000
```

**course_recommendation**
```
background    : BCA graduate with basic knowledge of programming
interest_area : Machine learning and data analysis
available_days: Weekends only
```

The prompt tab shows you the final rendered prompt that gets sent to the model.

---

## Later — Switching to Remote Hosting

When you are ready to host remotely, change just **one line** in `main.py`:

```python
# Local (stdio) — current
mcp.run(transport="stdio")

# Remote option 1: SSE
mcp.run(transport="sse", host="0.0.0.0", port=8000)

# Remote option 2: Streamable HTTP (recommended for production)
mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
```

No changes needed to tools, resources, or prompts — only the transport line changes.
