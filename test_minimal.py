import customtkinter as ctk

class MinimalApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Test")
        self.geometry("400x300")
        ctk.CTkLabel(self, text="Ventana mínima").pack(pady=20)

if __name__ == "__main__":
    app = MinimalApp()
    app.mainloop()