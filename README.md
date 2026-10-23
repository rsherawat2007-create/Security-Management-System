# Security Management System

A Python-based Security Management System developed as a Data Structures and Algorithms mini project.

## Features

- Visitor registration and entry-pass requests
- Resident/host approval and rejection
- Visitor check-in and check-out
- Undo recent guard actions using a stack
- Vehicle management using a circular queue
- Visitor search and status filtering
- SQLite database for persistent visitor records
- Admin dashboard with visitor statistics and gate logs

## Technologies Used

- Python 3
- SQLite
- Object-Oriented Programming
- Data Structures and Algorithms

## Data Structures

- **Singly Linked List:** Manages visitor records.
- **Stack:** Supports undoing recent guard actions.
- **Circular Queue:** Manages vehicles in FIFO order.

## How to Run

1. Install Python 3.
2. Clone or download this repository.
3. Open a terminal in the project directory.
4. Run:

```bash
python3 security_management.py
```

The SQLite database is created automatically when the application starts.

## Project Purpose

This project demonstrates the practical implementation of data structures, database operations, and role-based menu workflows in Python.

## Limitations

This is an academic console-based prototype. It does not yet implement secure user authentication or production-grade access controls.
