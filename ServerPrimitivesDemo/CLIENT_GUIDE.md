# MCP Console Client — Run & Observe Guide

## How it works

```
client.py  ──stdio──►  main.py (MCP Server)  ──►  institute.db
    ▲
  You type
```

`client.py` launches `main.py` as a subprocess and communicates with it
over stdio using the MCP protocol. No network, no ports — pure local.

---

## Run

Make sure you are inside the project folder and the venv is active:

```bash
cd 5.1-institute-mcp
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

python client.py
```

You will see:
```
════════════════════════════════════════════════════════════
  Deccansoft Institute — MCP Console Client
════════════════════════════════════════════════════════════
  Connecting to MCP server (main.py) via stdio...
  Connected successfully!
```

---

## Menu

```
──────────────────────────────────────────────────────────
  MAIN MENU
──────────────────────────────────────────────────────────
  1. Tools          — call add_student, enroll, search, etc.
  2. Resources      — browse courses, faculty, students, batches
  3. Prompts        — render progress report, announcement, etc.
  0. Exit
```

---

## What to observe — step by step

### Observe 1 — List & call a Tool

Choose `1` → Tools

You will see all 6 tools listed with descriptions.
Pick `search_students` and enter:
```
query: arjun
```

**What to observe:**
- The client sends a `tools/call` MCP message to the server
- The server queries SQLite and returns JSON
- The client prints the result

---

### Observe 2 — Static Resource

Choose `2` → Resources

You will see Static Resources and Resource Templates listed separately.
Pick `institute://courses`

**What to observe:**
- The client sends a `resources/read` MCP message
- The server returns all 4 courses as JSON
- Notice: no arguments needed — it's a fixed URI

---

### Observe 3 — Resource Template

Choose `2` → Resources

Pick `institute://courses/{course_id}` from the Resource Templates section.
You will be prompted:
```
Enter full URI (replace {param} with actual value): institute://courses/1
```

**What to observe:**
- Same `resources/read` MCP message but with a specific URI
- Returns course details + all its batches
- Compare with the static resource — same mechanism, dynamic address

---

### Observe 4 — Prompt

Choose `3` → Prompts

Pick `student_progress_report` and enter:
```
student_name  : Arjun Mehta
course_title  : Python Full Stack
batch_schedule: Mon/Wed/Fri 10am-1pm
progress_notes: Completed modules 1-4, strong in OOP, needs work on Django REST
```

**What to observe:**
- The client sends a `prompts/get` MCP message
- The server substitutes all arguments into the template
- You see the **fully rendered prompt** printed — this is exactly what an LLM would receive
- Notice the tone instructions, structure rules, and word count guidance are baked in

---

### Observe 5 — Tool with write action

Choose `1` → Tools → `add_student`
```
name  : Vikram Shah
email : vikram@gmail.com
phone : 9000000001
```

Then choose `enroll_student`:
```
student_id : 6        ← the ID returned from add_student
batch_id   : 2
```

**What to observe:**
- Two sequential Tool calls
- First creates a record, second links it — this is the LLM agent pattern
- The server validates both IDs before enrolling

---

## Key differences to observe

| Action | MCP Message sent | Server does |
|--------|-----------------|-------------|
| Pick a Tool and call it | `tools/call` | Executes function, writes/reads DB |
| Pick a static Resource | `resources/read` | Returns fixed dataset |
| Pick a Resource Template | `resources/read` with full URI | Looks up by ID |
| Pick a Prompt | `prompts/get` | Substitutes args, returns rendered text |

---

## Tip — watch both sides

Open two terminals side by side:

- **Terminal 1:** run `python client.py` — this is what you interact with
- **Terminal 2:** run `python -c "import sqlite3; ..."` or any DB viewer

After calling `add_student`, check the DB in Terminal 2 to confirm the record was written — this makes the Tool vs Resource distinction tangible.
