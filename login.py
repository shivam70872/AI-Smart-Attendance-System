
import customtkinter as ctk
from tkinter import messagebox

from main import create_db_connection


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class LoginPage:

    def __init__(self):

        self.root = ctk.CTk()

        self.root.title("AI Smart Attendance System")

        self.root.geometry("1000x600")

        self.root.resizable(False, False)

        self.create_ui()

        self.root.mainloop()

    def create_ui(self):

        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True)

        # ============================================
        # LEFT PANEL
        # ============================================

        left_frame = ctk.CTkFrame(
            main_frame,
            width=450,
            fg_color="#1E1E1E",
            corner_radius=0
        )

        left_frame.pack(side="left", fill="both")
        left_frame.pack_propagate(False)

        title = ctk.CTkLabel(
            left_frame,
            text="AI SMART\nATTENDANCE SYSTEM",
            font=("Arial", 34, "bold")
        )

        title.place(relx=0.5, rely=0.35, anchor="center")

        subtitle = ctk.CTkLabel(
            left_frame,
            text="Multi-Class Attendance System",
            font=("Arial", 18)
        )

        subtitle.place(relx=0.5, rely=0.48, anchor="center")

        # ============================================
        # RIGHT PANEL
        # ============================================

        right_frame = ctk.CTkFrame(
            main_frame,
            fg_color="#252526",
            corner_radius=0
        )

        right_frame.pack(side="right", fill="both", expand=True)

        login_box = ctk.CTkFrame(
            right_frame,
            width=420,
            height=350,
            corner_radius=20,
            fg_color="#2B2B2B"
        )

        login_box.place(relx=0.5, rely=0.5, anchor="center")

        login_box.pack_propagate(False)

        login_label = ctk.CTkLabel(
            login_box,
            text="Teacher Login",
            font=("Arial", 30, "bold")
        )

        login_label.pack(pady=(35, 30))

        # ============================================
        # USERNAME
        # ============================================

        self.username_entry = ctk.CTkEntry(
            login_box,
            placeholder_text="Enter Username",
            width=320,
            height=50,
            corner_radius=12,
            font=("Arial", 16)
        )

        self.username_entry.pack(pady=10)

        # ============================================
        # PASSWORD
        # ============================================

        self.password_entry = ctk.CTkEntry(
            login_box,
            placeholder_text="Enter Password",
            show="*",
            width=320,
            height=50,
            corner_radius=12,
            font=("Arial", 16)
        )

        self.password_entry.pack(pady=10)

        # ============================================
        # LOGIN BUTTON
        # ============================================

        login_btn = ctk.CTkButton(
            login_box,
            text="Login",
            width=320,
            height=50,
            corner_radius=12,
            font=("Arial", 18, "bold"),
            command=self.login
        )

        login_btn.pack(pady=25)

        self.root.bind("<Return>", lambda event: self.login())

    # ================================================
    # LOGIN FUNCTION
    # ================================================

    def login(self):

        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        try:

            conn = create_db_connection()

            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT * FROM teachers
                WHERE username=%s
                AND password=%s
                """,
                (username, password)
            )

            teacher = cursor.fetchone()

            cursor.close()
            conn.close()

            if teacher:

                self.root.destroy()

                from dashboard import Dashboard

                Dashboard(teacher)

            else:

                messagebox.showerror(
                    "Login Failed",
                    "Invalid Username or Password"
                )

        except Exception as e:

            print("Login Error:", e)


if __name__ == "__main__":
    LoginPage()


