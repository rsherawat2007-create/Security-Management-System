import sqlite3
import datetime
from collections import Counter
import matplotlib.pyplot as plt


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

    def clear_all_data(self):
        """Wipes all visitor records, gate logs, and resets autoincrement sequences."""
        self.cursor.execute("DELETE FROM visitors")
        self.cursor.execute("DELETE FROM gate_logs")
        try:
            self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='gate_logs'")
        except sqlite3.OperationalError:
            pass  # Sequence table is created only after the first autoincrement insert
        self.conn.commit()
        self.cursor.execute("VACUUM")

    def get_all_visitors(self):
        self.cursor.execute("""
            SELECT visitor_id, name, phone, host_name, purpose,
                   status, check_in_time, check_out_time
            FROM visitors
            ORDER BY visitor_id DESC
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

    def get_purpose_data(self):
        self.cursor.execute("""
            SELECT purpose, COUNT(*)
            FROM visitors
            GROUP BY purpose
            ORDER BY COUNT(*) DESC
        """)
        return self.cursor.fetchall()

    def get_hourly_checkin_data(self):
        self.cursor.execute("""
            SELECT check_in_time
            FROM visitors
            WHERE check_in_time != 'N/A'
        """)
        return [row[0] for row in self.cursor.fetchall()]

    def get_gate_logs_count(self):
        self.cursor.execute("SELECT COUNT(*) FROM gate_logs")
        return self.cursor.fetchone()[0]

    def get_gate_logs(self, limit=10):
        self.cursor.execute("""
            SELECT log_id, vehicle_no, entry_time
            FROM gate_logs ORDER BY log_id DESC LIMIT ?
        """, (limit,))
        return self.cursor.fetchall()

    def close(self):
        self.conn.close()


# ==========================================================
# VISITOR MANAGEMENT
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


class VisitorLinkedList:
    def __init__(self, db_ref):
        self.head = None
        self.total_count = 0
        self.db = db_ref

    def find_node(self, visitor_id):
        current = self.head
        while current is not None:
            if current.visitor_id == visitor_id:
                return current
            current = current.next
        return None

    def load_from_database(self):
        self.head = None
        self.total_count = 0
        for row in self.db.get_all_visitors():
            node = VisitorNode(*row)
            node.next = self.head
            self.head = node
            self.total_count += 1

    def add_visitor(self, visitor_id, name, phone, host_name, purpose):
        if self.find_node(visitor_id):
            print("\n[ERROR] This Visitor ID already exists.")
            return False

        saved = self.db.insert_visitor(visitor_id, name, phone, host_name, purpose)
        if not saved:
            print("\n[ERROR] Visitor ID already exists in the database.")
            return False

        new_node = VisitorNode(visitor_id, name, phone, host_name, purpose)
        new_node.next = self.head
        self.head = new_node
        self.total_count += 1

        print(f"\n[SUCCESS] Pass request created. Assigned Visitor ID: {visitor_id}")
        return True

    def update_status(self, visitor_id, new_status):
        current = self.find_node(visitor_id)
        if current is None:
            print("\n[ERROR] Visitor ID not found.")
            return False

        if current.status in ("Checked-In", "Checked-Out"):
            print("\n[ERROR] Cannot change approval decision after visitor entry processing.")
            return False
        elif current.status != "Pending":
            print("\n[ERROR] Only pending requests can be processed.")
            return False

        current.status = new_status
        self.db.update_status(visitor_id, new_status)
        print(f"\n[SUCCESS] Visitor ID {visitor_id} status updated to '{new_status}'.")
        return True

    def check_in(self, visitor_id, stack_ref):
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

        self.db.update_check_in(visitor_id, time_str)
        stack_ref.push({
            "visitor_id": visitor_id,
            "previous": previous_state,
            "action": "Check-In"
        })

        print(f"\n[SUCCESS] {visitor.name} checked in at {time_str}.")
        return True

    def check_out(self, visitor_id, stack_ref):
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

        self.db.update_check_out(visitor_id, time_str)
        stack_ref.push({
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

        self.db.restore_visitor(visitor)
        print(f"\n[SUCCESS] Undid {action_data['action']} for Visitor ID {visitor.visitor_id}.")
        print(f"Restored status: {visitor.status}")
        return True

    def get_active_on_campus(self):
        """Returns all visitors currently checked-in inside the premises."""
        active = []
        curr = self.head
        while curr:
            if curr.status == "Checked-In":
                active.append(curr)
            curr = curr.next
        return active

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
            if filter_status is None or current.status == filter_status:
                self.print_visitor(current)
                count += 1
            current = current.next

        if count == 0:
            print("\nNo matching visitor records found.")
        else:
            print(f"\nTotal matching records: {count}")


# ==========================================================
# ACTION STACK & GATE QUEUE
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


class GateCircularQueue:
    def __init__(self, db_ref, capacity=5):
        if capacity <= 0:
            raise ValueError("Queue capacity must be positive.")
        self.capacity = capacity
        self.queue = [None] * capacity
        self.head = 0
        self.tail = 0
        self.size = 0
        self.db = db_ref

    def enqueue(self, vehicle_no):
        vehicle_no = vehicle_no.strip().upper()
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
        self.db.log_gate_entry(vehicle_no, time_str)
        print(f"\n[SUCCESS] Vehicle {vehicle_no} processed at {time_str}.")
        return vehicle_no

    def get_waiting_vehicles(self):
        """Returns the list of vehicle plates currently waiting in queue order."""
        waiting = []
        for i in range(self.size):
            idx = (self.head + i) % self.capacity
            waiting.append(self.queue[idx])
        return waiting

    def display_queue(self):
        if self.size == 0:
            print("\nGate queue is empty.")
            return

        print("\n--------- GATE VEHICLE QUEUE ---------")
        for i, v_no in enumerate(self.get_waiting_vehicles()):
            print(f"{i + 1}. Vehicle No: {v_no}")
        print(f"Vehicles waiting: {self.size}/{self.capacity}")


# ==========================================================
# VISUAL ANALYTICS DASHBOARD (SECURITY METRICS ONLY)
# ==========================================================

class SecurityVisualDashboard:
    def __init__(self, db_ref, queue_ref):
        self.db = db_ref
        self.queue = queue_ref
        self.fig = None
        self.axes = None
        self.is_active = False

    def show_dashboard(self):
        """Opens or brings the 4-panel visual dashboard into view."""
        if self.fig is None or not plt.fignum_exists(self.fig.number):
            plt.ion()
            self.fig, self.axes = plt.subplots(2, 2, figsize=(12.5, 7.5))
            self.fig.canvas.manager.set_window_title(
                "Security Management System - Live Visual Analytics"
            )

        self.is_active = True
        self.refresh()
        print("\n[SUCCESS] Live visual dashboard opened on screen.")

    def refresh(self):
        """Redraws the graphs in real-time when any system data changes."""
        if not self.is_active or self.fig is None:
            return

        if not plt.fignum_exists(self.fig.number):
            self.is_active = False
            self.fig = None
            self.axes = None
            return

        ax1 = self.axes[0, 0]
        ax2 = self.axes[0, 1]
        ax3 = self.axes[1, 0]
        ax4 = self.axes[1, 1]

        for ax in (ax1, ax2, ax3, ax4):
            ax.clear()

        # 1. Visitor Workflow Breakdown (Bar Chart)
        _, pending, approved, rejected, checked_in, checked_out = self.db.get_statistics()
        categories = ["Pending", "Approved", "Inside", "Checked-Out", "Rejected"]
        counts = [pending, approved, checked_in, checked_out, rejected]
        colors = ["#f39c12", "#3498db", "#2ecc71", "#95a5a6", "#e74c3c"]

        bars = ax1.bar(categories, counts, color=colors, width=0.55)
        ax1.set_title("Current Visitor Statuses", fontsize=11, fontweight="bold")
        ax1.set_ylabel("Number of Visitors", fontsize=9)
        ax1.set_ylim(0, max(max(counts) + 2, 5))
        ax1.grid(axis="y", linestyle="--", alpha=0.35)

        for bar in bars:
            h = bar.get_height()
            ax1.annotate(
                f"{h}",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 3), textcoords="offset points",
                ha="center", va="bottom", fontsize=9, fontweight="bold"
            )

        # 2. Clearance & Approval Decisions (Donut Chart)
        total = sum(counts)
        processed_approved = approved + checked_in + checked_out
        labels = ["Approved", "Rejected", "Pending"]
        values = [processed_approved, rejected, pending]
        donut_colors = ["#2ecc71", "#e74c3c", "#f39c12"]

        if total == 0:
            ax2.text(0.5, 0.5, "No visitor requests recorded yet", ha="center", va="center", color="#7f8c8d")
            ax2.set_axis_off()
        else:
            ax2.pie(
                values,
                labels=labels,
                autopct=lambda p: f"{p:.1f}%\n({int(round(p * sum(values) / 100))})" if p > 0 else "",
                colors=donut_colors,
                startangle=140,
                wedgeprops=dict(width=0.45, edgecolor='white')
            )
            ax2.set_title(f"Pass Clearance Rate (Total Requests: {total})", fontsize=11, fontweight="bold")

        # 3. Purpose of Visit Breakdown (Horizontal Bar)
        purpose_data = self.db.get_purpose_data()
        if not purpose_data:
            ax3.text(0.5, 0.5, "No visit purposes logged yet", ha="center", va="center", color="#7f8c8d")
            ax3.set_axis_off()
        else:
            purposes = [item[0] for item in purpose_data]
            p_counts = [item[1] for item in purpose_data]
            y_pos = range(len(purposes))

            h_bars = ax3.barh(y_pos, p_counts, color="#1abc9c", height=0.5)
            ax3.set_yticks(y_pos)
            ax3.set_yticklabels(purposes, fontsize=9)
            ax3.invert_yaxis()
            ax3.set_xlabel("Visitors", fontweight="bold", fontsize=9)
            ax3.set_title("Visitor Classification by Purpose", fontsize=11, fontweight="bold")
            ax3.grid(axis="x", linestyle="--", alpha=0.35)

            for bar in h_bars:
                w = bar.get_width()
                ax3.annotate(
                    f"{w}",
                    xy=(w, bar.get_y() + bar.get_height() / 2),
                    xytext=(4, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=9, fontweight="bold"
                )

        # 4. Hourly Peak Influx Trend (Time-Series)
        raw_times = self.db.get_hourly_checkin_data()
        hours = [int(t.split(" ")[1].split(":")[0]) for t in raw_times if " " in t]
        hour_counts = Counter(hours)
        x_hours = list(range(24))
        y_traffic = [hour_counts.get(h, 0) for h in x_hours]

        ax4.plot(x_hours, y_traffic, marker="o", color="#8e44ad", linewidth=2, markersize=4)
        ax4.fill_between(x_hours, y_traffic, color="#8e44ad", alpha=0.2)
        ax4.set_xticks(range(0, 24, 3))
        ax4.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 3)], rotation=25, fontsize=8)
        ax4.set_ylabel("Check-In Volume", fontweight="bold", fontsize=9)
        ax4.set_ylim(0, max(max(y_traffic) + 2, 4))
        ax4.grid(True, linestyle="--", alpha=0.35)

        waiting = self.queue.size
        cap = self.queue.capacity
        ax4.set_title(
            f"Peak Entry Hours | Gate Queue: {waiting}/{cap} Vehicles Waiting",
            fontsize=11, fontweight="bold"
        )

        self.fig.tight_layout()
        self.fig.canvas.draw_idle()
        plt.pause(0.01)

    def close(self):
        if self.fig is not None and plt.fignum_exists(self.fig.number):
            plt.close(self.fig)


# ==========================================================
# TERMINAL COMPREHENSIVE REPORT
# ==========================================================

def print_terminal_comprehensive_report(db_ref, v_list, queue_ref):
    """Outputs a complete, structured security report directly in the console."""
    total, pending, approved, rejected, checked_in, checked_out = db_ref.get_statistics()
    active_visitors = v_list.get_active_on_campus()
    waiting_vehicles = queue_ref.get_waiting_vehicles()
    recent_logs = db_ref.get_gate_logs(limit=5)
    purposes = db_ref.get_purpose_data()

    print("\n" + "=" * 65)
    print("      COMPREHENSIVE SECURITY MANAGEMENT SYSTEM REPORT")
    print(f"      Report Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    # 1. Executive Summary
    print("\n[1] CAMPUS SECURITY SUMMARY")
    print("-" * 65)
    print(f"  Total Visitor Records  : {total:<6} | Currently Inside Campus : {checked_in}")
    print(f"  Pending Approvals      : {pending:<6} | Successfully Completed : {checked_out}")
    print(f"  Approved (Not Entered) : {approved:<6} | Rejected Pass Requests : {rejected}")
    if total > 0:
        clearance_rate = ((approved + checked_in + checked_out) / total) * 100
        print(f"  Overall Clearance Rate : {clearance_rate:.1f}%")

    # 2. Currently Inside Campus
    print("\n[2] VISITORS CURRENTLY INSIDE PREMISES")
    print("-" * 65)
    if not active_visitors:
        print("  >> No visitors are currently checked in inside the campus.")
    else:
        print(f"  {'ID':<6} {'Name':<16} {'Host':<14} {'Purpose':<14} {'Entry Time'}")
        print("  " + "-" * 63)
        for v in active_visitors:
            entry_clock = v.check_in_time.split(" ")[1] if " " in v.check_in_time else v.check_in_time
            print(f"  #{v.visitor_id:<5} {v.name:<16} {v.host_name:<14} {v.purpose:<14} {entry_clock}")

    # 3. Gate Status
    print("\n[3] VEHICLE GATE MONITORING")
    print("-" * 65)
    print(f"  Gate Queue Capacity    : {queue_ref.size}/{queue_ref.capacity} slots filled")
    if not waiting_vehicles:
        print("  >> Queue is clear. No vehicles currently waiting at the gate.")
    else:
        print("  Vehicles in Line       : " + " -> ".join(waiting_vehicles))

    print(f"\n  Recent Gate Entries (Total Logs: {db_ref.get_gate_logs_count()}):")
    if not recent_logs:
        print("  >> No gate logs recorded.")
    else:
        for log_id, v_no, e_time in recent_logs:
            print(f"    * Log #{log_id:<4} | Vehicle: {v_no:<10} | Time: {e_time}")

    # 4. Visit Reasons Breakdown
    print("\n[4] VISIT PURPOSE DISTRIBUTION")
    print("-" * 65)
    if not purposes:
        print("  >> No visitor purpose data available.")
    else:
        for purpose, count in purposes:
            pct = (count / total * 100) if total > 0 else 0
            bar = "#" * int(pct // 5)
            print(f"  {purpose:<18} : {count:>2} visitor(s) ({pct:>5.1f}%) | {bar}")

    print("\n" + "=" * 65)
    print("                 END OF REPORT")
    print("=" * 65)


# ==========================================================
# GLOBAL OBJECTS
# ==========================================================

db = Database()
guard_stack = ActionStack()
gate_queue = GateCircularQueue(db_ref=db, capacity=5)
visitor_system = VisitorLinkedList(db_ref=db)

# Restore records; visual dashboard stays closed until requested
visitor_system.load_from_database()
visualizer = SecurityVisualDashboard(db_ref=db, queue_ref=gate_queue)


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
# MENUS & PORTALS
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

            if visitor_system.add_visitor(v_id, name, phone, host, purpose):
                visualizer.refresh()

        elif choice == "2":
            v_id = get_integer("Enter Visitor ID: ")
            visitor_system.search_visitor(v_id)

        elif choice == "3":
            break
        else:
            print("Invalid input. Enter 1, 2, or 3.")


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
            decision = input("Action (A = Approve / R = Reject): ").strip().upper()

            updated = False
            if decision == "A":
                updated = visitor_system.update_status(v_id, "Approved")
            elif decision == "R":
                updated = visitor_system.update_status(v_id, "Rejected")
            else:
                print("[ERROR] Choose A or R.")

            if updated:
                visualizer.refresh()

        elif choice == "3":
            break
        else:
            print("Invalid input. Enter 1, 2, or 3.")


def security_guard_screen():
    while True:
        print("\n=== SECURITY GUARD DASHBOARD ===")
        print("1. Check-In Approved Visitor")
        print("2. Check-Out Visitor")
        print("3. Undo Last Guard Action")
        print("4. Add Vehicle to Gate Queue")
        print("5. Process Next Vehicle in Queue")
        print("6. Display Gate Queue")
        print("7. View Currently Checked-In Visitors")
        print("8. Return to Main Menu")

        choice = input("Select Option (1-8): ").strip()

        if choice == "1":
            v_id = get_integer("Enter Approved Visitor ID: ")
            if visitor_system.check_in(v_id, guard_stack):
                visualizer.refresh()

        elif choice == "2":
            v_id = get_integer("Enter Visitor ID for Check-Out: ")
            if visitor_system.check_out(v_id, guard_stack):
                visualizer.refresh()

        elif choice == "3":
            action = guard_stack.pop()
            if action is not None:
                if visitor_system.undo_action(action):
                    visualizer.refresh()

        elif choice == "4":
            v_no = input("Enter Vehicle Number: ")
            if gate_queue.enqueue(v_no):
                visualizer.refresh()

        elif choice == "5":
            if gate_queue.dequeue() is not None:
                visualizer.refresh()

        elif choice == "6":
            gate_queue.display_queue()

        elif choice == "7":
            visitor_system.display_all_visitors("Checked-In")

        elif choice == "8":
            break
        else:
            print("Invalid input. Enter a number from 1 to 8.")


def admin_screen():
    while True:
        print("\n=== SYSTEM ADMIN DASHBOARD ===")
        print("1. View All Visitor Records")
        print("2. View System Summary Statistics")
        print("3. View Vehicle Gate Logs")
        print("4. Clear / Reset Entire Database")
        print("5. Return to Main Menu")

        choice = input("Select Option (1-5): ").strip()

        if choice == "1":
            visitor_system.display_all_visitors()

        elif choice == "2":
            total, pending, approved, rejected, checked_in, checked_out = db.get_statistics()
            print("\n--------- SYSTEM STATISTICS ---------")
            print(f"Total Visitors      : {total}")
            print(f"Pending Requests    : {pending}")
            print(f"Approved            : {approved}")
            print(f"Rejected            : {rejected}")
            print(f"Currently Inside    : {checked_in}")
            print(f"Checked Out         : {checked_out}")
            print("-------------------------------------")

        elif choice == "3":
            logs = db.get_gate_logs(limit=20)
            if not logs:
                print("\nNo vehicle gate logs found.")
            else:
                print("\n--------- VEHICLE GATE LOGS ---------")
                for log_id, vehicle_no, entry_time in logs:
                    print(f"Log ID: {log_id} | Vehicle: {vehicle_no} | Time: {entry_time}")

        elif choice == "4":
            confirm = input("\n[WARNING] Are you sure you want to delete ALL records? (yes/no): ").strip().lower()
            if confirm == "yes":
                # Wipe persistent SQLite records
                db.clear_all_data()

                # Reset in-memory data structures
                visitor_system.head = None
                visitor_system.total_count = 0
                guard_stack.stack.clear()
                gate_queue.queue = [None] * gate_queue.capacity
                gate_queue.head = 0
                gate_queue.tail = 0
                gate_queue.size = 0

                # Synchronize visual window if open
                visualizer.refresh()
                print("\n[SUCCESS] Entire database wiped and data structures reset to clean state.")
            else:
                print("\nDatabase reset cancelled.")

        elif choice == "5":
            break
        else:
            print("Invalid input. Enter 1, 2, 3, 4, or 5.")


def main():
    try:
        while True:
            print("\n==================================================")
            print("       SECURITY MANAGEMENT SYSTEM")
            print("==================================================")
            print("1. Visitor Portal")
            print("2. Resident / Host Portal")
            print("3. Security Guard Dashboard")
            print("4. System Admin Dashboard")
            print("5. Open Live Visual Analytics Dashboard (Graphs)")
            print("6. Display Complete Security System Report (Terminal)")
            print("7. Exit Application")

            role_choice = input("Select Option (1-7): ").strip()

            if role_choice == "1":
                visitor_screen()
            elif role_choice == "2":
                resident_screen()
            elif role_choice == "3":
                security_guard_screen()
            elif role_choice == "4":
                admin_screen()
            elif role_choice == "5":
                visualizer.show_dashboard()
            elif role_choice == "6":
                print_terminal_comprehensive_report(db, visitor_system, gate_queue)
            elif role_choice == "7":
                print("\nExiting Security Management System.")
                break
            else:
                print("Invalid input. Select a number from 1 to 7.")

    except (KeyboardInterrupt, EOFError):
        print("\nApplication interrupted.")

    finally:
        visualizer.close()
        db.close()
        print("Database connection closed.")


if __name__ == "__main__":
    main()
