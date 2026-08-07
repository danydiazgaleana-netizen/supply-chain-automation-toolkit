from infrastructure.db.session import init_db
from gui.views.main_window import MainWindow

if __name__ == "__main__":
    print("🚀 Inicializando base de datos...")
    init_db()
    print("✅ Base de datos lista.")
    print("🪟 Abriendo ventana principal...")
    app = MainWindow()
    print("🔄 Ejecutando bucle principal...")
    app.mainloop()