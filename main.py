
import sqlite3
import datetime


# ==========================================================
# DATABASE MANAGEMENT
# ==========================================================

class Database:
    def __init__(self, db_name="security.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS visitors (
                visitor_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT,
                host_name TEXT,
                purpose TEXT,
                status TEXT DEFAULT 'Pending',
                check_in_time TEXT DEFAULT 'N/A',
                check_out_time TEXT DEFAULT 'N/A'
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS gate_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                vehicle_no TEXT NOT NULL,
                entry_time TEXT NOT NULL
            )
        """)

        self.conn.commit()

    def insert_visitor(self, v_id, name, phone, host, purpose):
        try:
            self.cursor.execute("""
                INSERT INTO visitors
                (visitor_id, name, phone, host_name, purpose,
                 status, check_in_time, check_out_time)
                VALUES (?, ?, ?, ?, ?, 'Pending', 'N/A', 'N/A')
            """, (v_id, name, phone, host, purpose))

            self.conn.commit()
            return True

        except sqlite3.IntegrityError:
            return False

    def update_status(self, v_id, status):
        self.cursor.execute(
            "UPDATE visitors SET status = ? WHERE visitor_id = ?",
            (status, v_id)
        )
        self.conn.commit()

    def update_check_in(self, v_id, time_str):
        self.cursor.execute("""
            UPDATE visitors
            SET check_in_time = ?, check_out_time = 'N/A',
                status = 'Checked-In'
            WHERE visitor_id = ?
        """, (time_str, v_id))
        self.conn.commit()

    def update_check_out(self, v_id, time_str):
        self.cursor.execute("""
            UPDATE visitors
            SET check_out_time = ?, status = 'Checked-Out'
            WHERE visitor_id = ?
        """, (time_str, v_id))
        self.conn.commit()

    def log_gate_entry(self, vehicle_no, time_str):
        self.cursor.execute("""
            INSERT INTO gate_logs (vehicle_no, entry_time)
            VALUES (?, ?)
        """, (vehicle_no, time_str))
        self.conn.commit()

    def restore_visitor(self, visitor):
        """Restore a visitor's complete state after undo."""
        self.cursor.execute("""
            UPDATE visitors
            SET status = ?, check_in_time = ?, check_out_time = ?
            WHERE visitor_id = ?
        """, (
            visitor.status,
            visitor.check_in_time,
            visitor.check_out_time,
            visitor.visitor_id
        ))
        self.conn.commit()

    def get_all_visitors(self):
        self.cursor.execute("""
            SELECT visitor_id, name, phone, host_name, purpose,
                   status, check_in_time, check_out_time
            FROM visitors
            ORDER BY visitor_id
        """)
        return self.cursor.fetchall()

    def get_visitor(self, v_id):
        self.cursor.execute("""
            SELECT visitor_id, name, phone, host_name, purpose,
                   status, check_in_time, check_out_time
            FROM visitors WHERE visitor_id = ?
        """, (v_id,))
        return self.cursor.fetchone()

    def get_statistics(self):
        self.cursor.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status = 'Approved' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status = 'Rejected' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status = 'Checked-In' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN status = 'Checked-Out' THEN 1 ELSE 0 END)
            FROM visitors
        """)
        result = self.cursor.fetchone()
        return tuple(value or 0 for value in result)

    def get_gate_logs(self):
        self.cursor.execute("""
            SELECT log_id, vehicle_no, entry_time
            FROM gate_logs ORDER BY log_id DESC
        """)
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()


# ==========================================================
# VISITOR NODE
# ==========================================================

class VisitorNode:
    def __init__(
        self, visitor_id, name, phone, host_name, purpose,
        status="Pending", check_in_time="N/A", check_out_time="N/A"
    ):
        self.visitor_id = visitor_id
        self.name = name
        self.phone = phone
        self.host_name = host_name
        self.purpose = purpose
        self.status = status
        self.check_in_time = check_in_time
        self.check_out_time = check_out_time
        self.next = None


# ==========================================================
# VISITOR LINKED LIST
# ==========================================================

class VisitorLinkedList:
    def __init__(self):
        self.head = None
        self.total_count = 0

    def find_node(self, visitor_id):
        current = self.head

        while current is not None:
            if current.visitor_id == visitor_id:
                return current
            current = current.next

        return None

    def load_from_database(self):
        """Load saved visitors when the application starts."""
        for row in db.get_all_visitors():
            node = VisitorNode(*row)
            node.next = self.head
            self.head = node
            self.total_count += 1

    def add_visitor(self, visitor_id, name, phone, host_name, purpose):
        if self.find_node(visitor_id):
            print("\n[ERROR] This Visitor ID already exists.")
            return False

        saved = db.insert_visitor(
            visitor_id, name, phone, host_name, purpose
        )

        if not saved:
            print("\n[ERROR] Visitor ID already exists in the database.")
            return False

        new_node = VisitorNode(
            visitor_id, name, phone, host_name, purpose
        )
        new_node.next = self.head
        self.head = new_node
        self.total_count += 1

        print(
            f"\n[SUCCESS] Pass request created. "
            f"Assigned Visitor ID: {visitor_id}"
        )
        return True

    def update_status(self, visitor_id, new_status):
        current = self.find_node(visitor_id)

        if current is None:
            print("\n[ERROR] Visitor ID not found.")
            return False

        if current.status in ("Checked-In", "Checked-Out"):
            print("\n[ERROR] Cannot change the approval decision "
                  "after visitor entry processing.")
            return False

        if current.status != "Pending":
            print("\n[ERROR] Only pending requests can be processed.")
            return False

        current.status = new_status
        db.update_status(visitor_id, new_status)

        print(
            f"\n[SUCCESS] Visitor ID {visitor_id} "
            f"status updated to '{new_status}'."
        )
        return True

    def check_in(self, visitor_id):
        visitor = self.find_node(visitor_id)

        if visitor is None:
            print("\n[ERROR] Visitor not found.")
            return False

        if visitor.status != "Approved":
            print("\n[ERROR] Only approved visitors can check in.")
            return False

        previous_state = {
            "status": visitor.status,
            "check_in_time": visitor.check_in_time,
            "check_out_time": visitor.check_out_time
        }

        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        visitor.status = "Checked-In"
        visitor.check_in_time = time_str
        visitor.check_out_time = "N/A"

        db.update_check_in(visitor_id, time_str)

        guard_stack.push({
            "visitor_id": visitor_id,
            "previous": previous_state,
            "action": "Check-In"
        })

        print(f"\n[SUCCESS] {visitor.name} checked in at {time_str}.")
        return True

    def check_out(self, visitor_id):
        visitor = self.find_node(visitor_id)

        if visitor is None:
            print("\n[ERROR] Visitor not found.")
            return False

        if visitor.status != "Checked-In":
            print("\n[ERROR] Visitor is not currently checked in.")
            return False

        previous_state = {
            "status": visitor.status,
            "check_in_time": visitor.check_in_time,
            "check_out_time": visitor.check_out_time
        }

        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        visitor.status = "Checked-Out"
        visitor.check_out_time = time_str

        db.update_check_out(visitor_id, time_str)

        guard_stack.push({
            "visitor_id": visitor_id,
            "previous": previous_state,
            "action": "Check-Out"
        })

        print(f"\n[SUCCESS] {visitor.name} checked out at {time_str}.")
        return True

    def undo_action(self, action_data):
        visitor = self.find_node(action_data["visitor_id"])

        if visitor is None:
            print("\n[ERROR] Visitor record not found.")
            return False

        previous = action_data["previous"]

        visitor.status = previous["status"]
        visitor.check_in_time = previous["check_in_time"]
        visitor.check_out_time = previous["check_out_time"]

        db.restore_visitor(visitor)

        print(
            f"\n[SUCCESS] Undid {action_data['action']} "
            f"for Visitor ID {visitor.visitor_id}."
        )
        print(f"Restored status: {visitor.status}")
        return True

    def search_visitor(self, visitor_id):
        visitor = self.find_node(visitor_id)

        if visitor is None:
            print("\n[ERROR] Visitor ID not found.")
            return None

        self.print_visitor(visitor)
        return visitor

    @staticmethod
    def print_visitor(visitor):
        print("\n------------- VISITOR DETAILS -------------")
        print(f"Visitor ID     : {visitor.visitor_id}")
        print(f"Name           : {visitor.name}")
        print(f"Phone          : {visitor.phone}")
        print(f"Host           : {visitor.host_name}")
        print(f"Purpose        : {visitor.purpose}")
        print(f"Status         : {visitor.status}")
        print(f"Check-In Time  : {visitor.check_in_time}")
        print(f"Check-Out Time : {visitor.check_out_time}")
        print("--------------------------------------------")

    def display_all_visitors(self, filter_status=None):
        current = self.head
        count = 0

        while current is not None:
            if (
                filter_status is None
                or current.status == filter_status
            ):
                self.print_visitor(current)
                count += 1

            current = current.next

        if count == 0:
            print("\nNo matching visitor records found.")
        else:
            print(f"\nTotal matching records: {count}")


# ==========================================================
# ACTION STACK
# ==========================================================

class ActionStack:
    def __init__(self):
        self.stack = []

    def push(self, action_data):
        self.stack.append(action_data)

    def pop(self):
        if self.is_empty():
            print("\n[ERROR] No guard action available to undo.")
            return None

        return self.stack.pop()

    def is_empty(self):
        return len(self.stack) == 0


# ==========================================================
# GATE CIRCULAR QUEUE
# ==========================================================

class GateCircularQueue:
    def __init__(self, capacity=5):
        if capacity <= 0:
            raise ValueError("Queue capacity must be positive.")

        self.capacity = capacity
        self.queue = [None] * capacity
        self.head = 0
        self.tail = 0
        self.size = 0

    def enqueue(self, vehicle_no):
        vehicle_no = vehicle_no.strip()

        if not vehicle_no:
            print("\n[ERROR] Vehicle number cannot be empty.")
            return False

        if self.size == self.capacity:
            print("\n[ERROR] Gate queue is full!")
            return False

        self.queue[self.tail] = vehicle_no
        self.tail = (self.tail + 1) % self.capacity
        self.size += 1

        print(f"\n[SUCCESS] Vehicle {vehicle_no} added to gate queue.")
        return True

    def dequeue(self):
        if self.size == 0:
            print("\n[ERROR] Gate queue is empty.")
            return None

        vehicle_no = self.queue[self.head]
        self.queue[self.head] = None

        self.head = (self.head + 1) % self.capacity
        self.size -= 1

        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.log_gate_entry(vehicle_no, time_str)

        print(f"\n[SUCCESS] Vehicle {vehicle_no} processed at {time_str}.")
        return vehicle_no

    def display_queue(self):
        if self.size == 0:
            print("\nGate queue is empty.")
            return

        print("\n--------- GATE VEHICLE QUEUE ---------")

        for i in range(self.size):
            index = (self.head + i) % self.capacity
            print(f"{i + 1}. {self.queue[index]}")

        print(f"Vehicles waiting: {self.size}/{self.capacity}")


# ==========================================================
# GLOBAL OBJECTS
# ==========================================================

db = Database()
visitor_system = VisitorLinkedList()
guard_stack = ActionStack()
gate_queue = GateCircularQueue(capacity=5)

# Restore existing records from SQLite.
visitor_system.load_from_database()


# ==========================================================
# INPUT VALIDATION
# ==========================================================

def get_integer(prompt):
    while True:
        try:
            return int(input(prompt).strip())
        except ValueError:
            print("[ERROR] Please enter a valid whole number.")


# ==========================================================
# VISITOR PORTAL
# ==========================================================

def visitor_screen():
    while True:
        print("\n=== VISITOR PORTAL ===")
        print("1. Request Entry Pass")
        print("2. Check Pass Status")
        print("3. Return to Main Menu")

        choice = input("Select Option (1-3): ").strip()

        if choice == "1":
            v_id = get_integer("Enter Desired Visitor ID: ")

            name = input("Enter Full Name: ").strip()
            phone = input("Enter Phone Number: ").strip()
            host = input("Enter Resident/Host Name: ").strip()
            purpose = input("Enter Purpose of Visit: ").strip()

            if not name or not host or not purpose:
                print("[ERROR] Name, host, and purpose are required.")
                continue

            visitor_system.add_visitor(
                v_id, name, phone, host, purpose
            )

        elif choice == "2":
            v_id = get_integer("Enter Visitor ID: ")
            visitor_system.search_visitor(v_id)

        elif choice == "3":
            break

        else:
            print("Invalid input. Enter 1, 2, or 3.")


# ==========================================================
# RESIDENT / HOST PORTAL
# ==========================================================

def resident_screen():
    while True:
        print("\n=== RESIDENT / HOST PORTAL ===")
        print("1. View Pending Entry Requests")
        print("2. Approve or Reject Entry Pass")
        print("3. Return to Main Menu")

        choice = input("Select Option (1-3): ").strip()

        if choice == "1":
            visitor_system.display_all_visitors("Pending")

        elif choice == "2":
            v_id = get_integer("Enter Visitor ID to Process: ")
            decision = input("Action (A = Approve / R = Reject): ")
            decision = decision.strip().upper()

            if decision == "A":
                visitor_system.update_status(v_id, "Approved")
            elif decision == "R":
                visitor_system.update_status(v_id, "Rejected")
            else:
                print("[ERROR] Choose A or R.")

        elif choice == "3":
            break

        else:
            print("Invalid input. Enter 1, 2, or 3.")


# ==========================================================
# SECURITY GUARD DASHBOARD
# ==========================================================

def security_guard_screen():
    while True:
        print("\n=== SECURITY GUARD DASHBOARD ===")
        print("1. Check-In Approved Visitor")
        print("2. Check-Out Visitor")
        print("3. Undo Last Guard Action (Stack)")
        print("4. Add Vehicle to Gate Queue")
        print("5. Process Next Vehicle in Queue")
        print("6. Display Gate Queue")
        print("7. View Currently Checked-In Visitors")
        print("8. Return to Main Menu")

        choice = input("Select Option (1-8): ").strip()

        if choice == "1":
            v_id = get_integer("Enter Approved Visitor ID: ")
            visitor_system.check_in(v_id)

        elif choice == "2":
            v_id = get_integer("Enter Visitor ID for Check-Out: ")
            visitor_system.check_out(v_id)

        elif choice == "3":
            action = guard_stack.pop()

            if action is not None:
                visitor_system.undo_action(action)

        elif choice == "4":
            v_no = input("Enter Vehicle Number: ")
            gate_queue.enqueue(v_no)

        elif choice == "5":
            gate_queue.dequeue()

        elif choice == "6":
            gate_queue.display_queue()

        elif choice == "7":
            visitor_system.display_all_visitors("Checked-In")

        elif choice == "8":
            break

        else:
            print("Invalid input. Enter a number from 1 to 8.")


# ==========================================================
# ADMIN DASHBOARD
# ==========================================================

def admin_screen():
    while True:
        print("\n=== SYSTEM ADMIN DASHBOARD ===")
        print("1. View All Visitor Records")
        print("2. View System Summary Statistics")
        print("3. View Vehicle Gate Logs")
        print("4. Return to Main Menu")

        choice = input("Select Option (1-4): ").strip()

        if choice == "1":
            visitor_system.display_all_visitors()

        elif choice == "2":
            (
                total, pending, approved, rejected,
                checked_in, checked_out
            ) = db.get_statistics()

            print("\n--------- SYSTEM STATISTICS ---------")
            print(f"Total Visitors      : {total}")
            print(f"Pending Requests    : {pending}")
            print(f"Approved            : {approved}")
            print(f"Rejected            : {rejected}")
            print(f"Currently Inside    : {checked_in}")
            print(f"Checked Out         : {checked_out}")
            print("-------------------------------------")

        elif choice == "3":
            logs = db.get_gate_logs()

            if not logs:
                print("\nNo vehicle gate logs found.")
            else:
                print("\n--------- VEHICLE GATE LOGS ---------")

                for log_id, vehicle_no, entry_time in logs:
                    print(
                        f"Log ID: {log_id} | "
                        f"Vehicle: {vehicle_no} | "
                        f"Time: {entry_time}"
                    )

        elif choice == "4":
            break

        else:
            print("Invalid input. Enter 1, 2, 3, or 4.")


# ==========================================================
# MAIN MENU
# ==========================================================

def main():
    try:
        while True:
            print("\n==================================================")
            print("       SECURITY MANAGEMENT SYSTEM")
            print("==================================================")
            print("1. Visitor Portal")
            print("2. Resident / Host Portal")
            print("3. Security Guard Dashboard")
            print("4. Admin Dashboard")
            print("5. Exit Application")

            role_choice = input("Select Portal (1-5): ").strip()

            if role_choice == "1":
                visitor_screen()

            elif role_choice == "2":
                resident_screen()

            elif role_choice == "3":
                security_guard_screen()

            elif role_choice == "4":
                admin_screen()

            elif role_choice == "5":
                print("\nExiting Security Management System.")
                break

            else:
                print("Invalid input. Select a number from 1 to 5.")

    except (KeyboardInterrupt, EOFError):
        print("\nApplication interrupted.")

    finally:
        db.close()
        print("Database connection closed.")


if __name__ == "__main__":
    main()
