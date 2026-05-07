
import customtkinter as ctk

from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

from PIL import Image, ImageTk

import cv2
import pandas as pd

from datetime import datetime

from main import recognize_faces, create_db_connection


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class Dashboard:

    def __init__(self, teacher_data):

        self.teacher_data = teacher_data

        self.teacher_name = teacher_data['teacher_name']
        self.class_name = teacher_data['class_name']
        self.department = teacher_data['department']

        self.root = ctk.CTk()

        self.root.title("AI Smart Attendance Dashboard")

        self.root.geometry("1500x850")

        self.cap = None

        self.camera_running = False

        self.current_mode = "CHECK-IN"

        self.create_layout()

        self.start_camera()

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

        self.root.mainloop()

    # ================================================
    # UI
    # ================================================

    def create_layout(self):

        header = ctk.CTkFrame(
            self.root,
            height=90,
            fg_color="#1E1E1E"
        )

        header.pack(fill="x")

        header.pack_propagate(False)

        title = ctk.CTkLabel(
            header,
            text="AI SMART ATTENDANCE MANAGEMENT SYSTEM",
            font=("Arial", 30, "bold")
        )

        title.pack(pady=25)

        main_frame = ctk.CTkFrame(
            self.root,
            fg_color="#121212"
        )

        main_frame.pack(fill="both", expand=True)

        # ============================================
        # SIDEBAR
        # ============================================

        sidebar = ctk.CTkFrame(
            main_frame,
            width=260,
            fg_color="#252526",
            corner_radius=15
        )

        sidebar.pack(
            side="left",
            fill="y",
            padx=15,
            pady=15
        )

        sidebar.pack_propagate(False)

        sidebar_title = ctk.CTkLabel(
            sidebar,
            text="CONTROL PANEL",
            font=("Arial", 24, "bold")
        )

        sidebar_title.pack(pady=20)

        teacher_label = ctk.CTkLabel(
            sidebar,
            text=f"Teacher: {self.teacher_name}",
            font=("Arial", 16, "bold")
        )

        teacher_label.pack(pady=5)

        class_label = ctk.CTkLabel(
            sidebar,
            text=f"Class: {self.class_name}",
            font=("Arial", 16)
        )

        class_label.pack(pady=5)

        dept_label = ctk.CTkLabel(
            sidebar,
            text=f"Department: {self.department}",
            font=("Arial", 16)
        )

        dept_label.pack(pady=5)

        self.checkin_btn = ctk.CTkButton(
            sidebar,
            text="Check-In",
            fg_color="green",
            hover_color="#006400",
            height=50,
            font=("Arial", 16, "bold"),
            command=self.set_checkin
        )

        self.checkin_btn.pack(
            pady=15,
            padx=20,
            fill="x"
        )

        self.checkout_btn = ctk.CTkButton(
            sidebar,
            text="Check-Out",
            fg_color="red",
            hover_color="#8B0000",
            height=50,
            font=("Arial", 16, "bold"),
            command=self.set_checkout
        )

        self.checkout_btn.pack(
            pady=10,
            padx=20,
            fill="x"
        )

        export_btn = ctk.CTkButton(
            sidebar,
            text="Export Report",
            height=50,
            font=("Arial", 16, "bold"),
            command=self.export_report
        )

        export_btn.pack(
            pady=10,
            padx=20,
            fill="x"
        )

        self.mode_label = ctk.CTkLabel(
            sidebar,
            text="Current Mode: CHECK-IN",
            font=("Arial", 18, "bold"),
            text_color="green"
        )

        self.mode_label.pack(pady=30)

        # ============================================
        # CENTER FRAME
        # ============================================

        center_frame = ctk.CTkFrame(
            main_frame,
            fg_color="#1E1E1E",
            corner_radius=15
        )

        center_frame.pack(
            side="left",
            fill="both",
            expand=True,
            padx=10,
            pady=15
        )

        camera_title = ctk.CTkLabel(
            center_frame,
            text="LIVE CAMERA PREVIEW",
            font=("Arial", 24, "bold")
        )

        camera_title.pack(pady=15)

        self.camera_label = ctk.CTkLabel(
            center_frame,
            text="Starting Camera...",
            width=700,
            height=400
        )

        self.camera_label.pack(pady=10)

        table_title = ctk.CTkLabel(
            center_frame,
            text="ATTENDANCE RECORDS",
            font=("Arial", 24, "bold")
        )

        table_title.pack(pady=15)

        columns = (
            "Roll No",
            "Name",
            "Status",
            "Time"
        )

        self.tree = ttk.Treeview(
            center_frame,
            columns=columns,
            show="headings",
            height=10
        )

        for col in columns:

            self.tree.heading(col, text=col)

            self.tree.column(
                col,
                width=180,
                anchor="center"
            )

        self.tree.pack(
            fill="x",
            padx=20,
            pady=10
        )

        self.refresh_table()

        # ============================================
        # RIGHT PANEL
        # ============================================

        right_panel = ctk.CTkFrame(
            main_frame,
            width=300,
            fg_color="#252526",
            corner_radius=15
        )

        right_panel.pack(
            side="right",
            fill="y",
            padx=15,
            pady=15
        )

        right_panel.pack_propagate(False)

        details_title = ctk.CTkLabel(
            right_panel,
            text="STUDENT DETAILS",
            font=("Arial", 24, "bold")
        )

        details_title.pack(pady=25)

        self.name_label = ctk.CTkLabel(
            right_panel,
            text="Name: ---",
            font=("Arial", 18)
        )

        self.name_label.pack(pady=12)

        self.confidence_label = ctk.CTkLabel(
            right_panel,
            text="Confidence: ---",
            font=("Arial", 18)
        )

        self.confidence_label.pack(pady=12)

        self.time_label = ctk.CTkLabel(
            right_panel,
            text="Time: ---",
            font=("Arial", 18)
        )

        self.time_label.pack(pady=12)

        # ============================================
        # LOGOUT BUTTON
        # ============================================

        logout_btn = ctk.CTkButton(
            right_panel,
            text="Logout",
            fg_color="#8B0000",
            hover_color="#5C0000",
            height=50,
            font=("Arial", 16, "bold"),
            command=self.logout
        )

        logout_btn.pack(
            side="bottom",
            pady=30,
            padx=20,
            fill="x"
        )

    # ================================================
    # START CAMERA
    # ================================================

    def start_camera(self):

        if self.camera_running:
            return

        self.cap = cv2.VideoCapture(
            0,
            cv2.CAP_AVFOUNDATION
        )

        if not self.cap.isOpened():

            messagebox.showerror(
                "Camera Error",
                "Could not access webcam"
            )

            return

        self.camera_running = True

        self.update_camera()

    # ================================================
    # CAMERA LOOP
    # ================================================

    def update_camera(self):

        if not self.camera_running:
            return

        ret, frame = self.cap.read()

        if ret:

            frame, detected_name, confidence = recognize_faces(
                frame,
                self.current_mode,
                self.teacher_name,
                self.class_name
            )

            self.refresh_table()

            current_time = datetime.now().strftime(
                "%H:%M:%S"
            )

            self.name_label.configure(
                text=f"Name: {detected_name}"
            )

            self.confidence_label.configure(
                text=f"Confidence: {confidence}%"
            )

            self.time_label.configure(
                text=f"Time: {current_time}"
            )

            frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            img = Image.fromarray(frame)

            img = img.resize((700, 400))

            imgtk = ImageTk.PhotoImage(image=img)

            self.camera_label.imgtk = imgtk

            self.camera_label.configure(
                image=imgtk,
                text=""
            )

        self.root.after(
            30,
            self.update_camera
        )

    # ================================================
    # MODES
    # ================================================

    def set_checkin(self):

        self.current_mode = "CHECK-IN"

        self.mode_label.configure(
            text="Current Mode: CHECK-IN",
            text_color="green"
        )

    def set_checkout(self):

        self.current_mode = "CHECK-OUT"

        self.mode_label.configure(
            text="Current Mode: CHECK-OUT",
            text_color="red"
        )

    # ================================================
    # REFRESH TABLE
    # ================================================

    def refresh_table(self):

        for item in self.tree.get_children():
            self.tree.delete(item)

        try:

            conn = create_db_connection()

            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    roll_no,
                    name,
                    status,
                    timestamp
                FROM attendance
                WHERE class_name=%s
                ORDER BY timestamp DESC
                """,
                (self.class_name,)
            )

            rows = cursor.fetchall()

            for row in rows:

                self.tree.insert(
                    "",
                    "end",
                    values=row
                )

            cursor.close()
            conn.close()

        except Exception as e:

            print("Refresh Error:", e)

    # ================================================
    # EXPORT REPORT
    # ================================================

    def export_report(self):

        try:

            conn = create_db_connection()

            query = """
            SELECT
                roll_no,
                name,
                class_name,
                teacher_name,
                status,
                timestamp
            FROM attendance
            WHERE class_name=%s
            ORDER BY timestamp DESC
            """

            df = pd.read_sql(
                query,
                conn,
                params=[self.class_name]
            )

            if df.empty:

                messagebox.showwarning(
                    "No Data",
                    "No attendance records found"
                )

                conn.close()

                return

            current_date = datetime.now().strftime(
                "%Y-%m-%d"
            )

            filename = filedialog.asksaveasfilename(
                initialfile=f"{self.class_name}_Attendance_{current_date}.xlsx",
                defaultextension=".xlsx",
                filetypes=[
                    ("Excel files", "*.xlsx")
                ]
            )

            if not filename:
                return

            df.to_excel(
                filename,
                index=False
            )

            messagebox.showinfo(
                "Export Successful",
                "Attendance report exported successfully"
            )

            conn.close()

        except Exception as e:

            print("Export Error:", e)

    # ================================================
    # LOGOUT
    # ================================================

    def logout(self):

        self.camera_running = False

        if self.cap:
            self.cap.release()

        self.root.destroy()

        from login import LoginPage

        LoginPage()

    # ================================================
    # CLOSE APP
    # ================================================

    def on_close(self):

        self.camera_running = False

        if self.cap:
            self.cap.release()

        self.root.destroy()


if __name__ == "__main__":
    Dashboard()
