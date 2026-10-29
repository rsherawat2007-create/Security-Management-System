# Security Management System with Real-Time Visual Analytics

A modular, terminal-driven campus access control and visitor management system written in Python. The project integrates custom in-memory data structures (Singly Linked List, Action Stack, Circular Queue) with persistent SQLite storage and an event-driven, non-blocking Matplotlib analytics dashboard.

---

## Architecture Overview

```
                      +------------------------------------------+
                      |         CLI Multi-Portal Engine          |
                      +------------------------------------------+
                                     |           |
            +------------------------+           +-----------------------+
            v                                                            v
+-----------------------+                                    +-----------------------+
| In-Memory Data Layers |                                    | Persistent Storage    |
| - Singly Linked List  | <------- Bidirectional Sync ------> | - SQLite (security.db)|
| - Guard Action Stack  |                                    |   * visitors table    |
| - Gate Circular Queue |                                    |   * gate_logs table   |
+-----------------------+                                    +-----------------------+
            |
            v
+------------------------------------------+
|  Real-Time Visual Analytics Dashboard    |
|  (Matplotlib Non-Blocking plt.ion())    |
|  - Visitor Status Breakdown              |
|  - Clearance & Rejection Donut           |
|  - Visit Purpose Horizontal Ranking      |
|  - 24-Hour Peak Influx Curve             |
+------------------------------------------+

```

---

## Core Data Structures

| Data Structure | Implementation Class | Operational Purpose | Complexity |
| --- | --- | --- | --- |
| **Singly Linked List** | `VisitorLinkedList` | Stores dynamic visitor records in memory; handles fast node insertion, status tracking, and traversal. | Insertion: $\mathcal{O}(1)$<br>

<br>Search: $\mathcal{O}(n)$ |
| **LIFO Stack** | `ActionStack` | Records sequential guard check-in/check-out events to enable single-step undo operations. | Push: $\mathcal{O}(1)$<br>

<br>Pop: $\mathcal{O}(1)$ |
| **Circular Queue** | `GateCircularQueue` | Manages vehicle entrance buffers at physical security barriers with fixed capacity (5 slots). | Enqueue: $\mathcal{O}(1)$<br>

<br>Dequeue: $\mathcal{O}(1)$ |
| **Relational Database** | `Database` (SQLite3) | Ensures ACID compliance, multi-session state persistence, and audit logging for vehicles and visitors. | Indexed Query: $\mathcal{O}(\log n)$ |

---

## Key Features

* **Multi-Portal Role Architecture:**
* **Visitor Portal:** Self-service entry pass creation and pass validation lookup.
* **Resident / Host Portal:** Approval and rejection gatekeeping for incoming visitor requests.
* **Security Guard Dashboard:** Check-in processing, checkout management, stack-based action undo, and circular queue vehicle logging.
* **System Admin Dashboard:** High-level summary metrics, full audit logs, and database cleanup controls.


* **Non-Blocking Live Analytics:** Interactive 4-panel dashboard that updates synchronously alongside terminal inputs without freezing user interaction:
* **Visitor Status Breakdown:** Colored bar chart indicating Pending, Approved, Inside, Checked-Out, and Rejected visitors.
* **Pass Clearance Ratio:** Donut chart illustrating approval vs. rejection vs. pending percentage distributions.
* **Classification by Purpose:** Ranked horizontal bars categorizing foot-traffic reasons (Meeting, Delivery, Maintenance, Guest, Interview).
* **Hourly Peak Influx:** 24-hour time-series tracking rush hours and entry volumes.


* **Console Security Reporting:** Formatted ASCII audit report displaying current inside occupants, waiting gate vehicles, recent logs, and percentage distributions directly in the terminal.

---

## Project Structure

```
├── security_management_live_analytics.py   # Main application source code
├── security.db                             # SQLite database (auto-generated)
└── README.md                               # System documentation

```

---

## Prerequisites & Installation

### Requirements

* **Python:** Version 3.10 or higher
* **Operating System:** macOS, Linux, or Windows

### Dependencies

Install the required visualization library:

```bash
pip install matplotlib

```

*(SQLite3, datetime, and collections are part of Python's standard library).*

---

## Usage Guide

### 1. Launching the System

Run the main application file from your terminal:

```bash
python3 security_management_live_analytics.py

```

### 2. Main Menu Navigation

```text
==================================================
       SECURITY MANAGEMENT SYSTEM
==================================================
1. Visitor Portal
2. Resident / Host Portal
3. Security Guard Dashboard
4. System Admin Dashboard
5. Open Live Visual Analytics Dashboard (Graphs)
6. Display Complete Security System Report (Terminal)
7. Exit Application

```

* **Option 1 (Visitor Portal):** Create a pass request with Visitor ID, Name, Phone, Host, and Purpose.
* **Option 2 (Resident Portal):** View pending requests and approve (`A`) or reject (`R`) them.
* **Option 3 (Guard Dashboard):** Check-in approved visitors, check them out, enqueue/dequeue vehicles at the gate, or undo the last guard action.
* **Option 4 (Admin Dashboard):** View system-wide stats, check full vehicle gate logs, or clear the database.
* **Option 5 (Live Analytics):** Launches the 4-panel visual window. Once open, it automatically recalculates and redraws whenever any action occurs.
* **Option 6 (Terminal Report):** Prints the comprehensive security audit report directly in your terminal.

---

### 3. Resetting / Clearing the Database

* **Via the In-App Admin Menu:** Launch the program, navigate to `4. System Admin Dashboard` > `4. Clear / Reset Entire Database`, and type `yes`.
* **Via Command Line:** Delete the generated database file:
```bash
rm security.db

```



---

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS visitors (
    visitor_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT,
    host_name TEXT,
    purpose TEXT,
    status TEXT DEFAULT 'Pending',
    check_in_time TEXT DEFAULT 'N/A',
    check_out_time TEXT DEFAULT 'N/A'
);

CREATE TABLE IF NOT EXISTS gate_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_no TEXT NOT NULL,
    entry_time TEXT NOT NULL
);

```
