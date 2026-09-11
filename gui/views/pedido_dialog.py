"""
Ventana de validación y corrección de embarque -- usa los nombres de campo
REALES de ShipmentDTO/SalesOrderDTO:
    - numero_pedido_logistica viene de la OV, no del Shipment.
    - cajas_embarque (sin 's'), no cajas_embarques.
    - chofer_recibe, no chofer.
"""
from __future__ import annotations
import os
from datetime import datetime
from tkinter import messagebox
import customtkinter as ctk


class PedidoDialog(ctk.CTkToplevel):
    def __init__(
        self, master, on_confirm, on_attach_guide, on_download_guide,
        shipment_dto, numero_pedido_logistica: str, shipment_id: int,
    ):
        super().__init__(master)
        self.title("Validacion y Correccion de Embarque")
        self.geometry("520x700")
        self.resizable(False, False)
        self.grab_set()

        self.on_confirm = on_confirm
        self.on_attach_guide = on_attach_guide
        self.on_download_guide = on_download_guide
        self.shipment_id = shipment_id
        self.current_version = shipment_dto.version

        cajas = shipment_dto.cajas_embarque
        chofer = shipment_dto.chofer_recibe or ""
        fecha_entrega = shipment_dto.fecha_entrega or ""
        archivo_guia = shipment_dto.archivo_guia or ""

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            main_frame, text="Numero de Pedido de Logistica (Referencia Fija):",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", pady=(0, 2))

        self.entry_pedido_logistica = ctk.CTkEntry(main_frame, height=35)
        self.entry_pedido_logistica.insert(0, numero_pedido_logistica or "(sin capturar por logistica)")
        self.entry_pedido_logistica.configure(state="disabled")
        self.entry_pedido_logistica.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            main_frame, text="Guia Adjunta por Logistica:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", pady=(5, 2))

        guia_frame = ctk.CTkFrame(main_frame, fg_color="#2b2b2b", corner_radius=6)
        guia_frame.pack(fill="x", pady=(0, 15))

        self.lbl_guia = ctk.CTkLabel(guia_frame, text="Ningun archivo adjunto", text_color="gray")
        self.lbl_guia.pack(side="left", padx=12, pady=10)

        self.btn_descargar = ctk.CTkButton(
            guia_frame, text="Descargar Guia", width=120, command=self._descargar_guia,
            fg_color="#2fa572", hover_color="#217651", font=ctk.CTkFont(size=11, weight="bold"),
        )
        if archivo_guia and os.path.exists(archivo_guia):
            self.btn_descargar.pack(side="right", padx=10)
            self.lbl_guia.configure(text=os.path.basename(archivo_guia), text_color="#2fa572")
        else:
            self.btn_descargar.pack_forget()

        ctk.CTkLabel(
            main_frame, text="Cajas (Corregir discrepancia):", font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", pady=(5, 2))
        self.entry_cajas = ctk.CTkEntry(main_frame, height=35)
        self.entry_cajas.insert(0, str(cajas) if cajas is not None else "0")
        self.entry_cajas.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(main_frame, text="Nombre del Chofer:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(5, 2))
        self.entry_chofer = ctk.CTkEntry(main_frame, height=35)
        self.entry_chofer.insert(0, chofer)
        self.entry_chofer.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(main_frame, text="Fecha de Entrega (AAAA-MM-DD):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(5, 2))
        self.entry_fecha = ctk.CTkEntry(main_frame, height=35)
        self.entry_fecha.insert(0, fecha_entrega)
        self.entry_fecha.pack(fill="x", pady=(0, 15))

        self.feedback = ctk.CTkLabel(main_frame, text="", text_color="gray60", wraplength=460, justify="left")
        self.feedback.pack(fill="x", pady=(0, 8))

        self.btn_guardar = ctk.CTkButton(
            main_frame, text="GUARDAR Y CONCILIAR", height=45, command=self._confirm,
            fg_color="#2fa572", hover_color="#217651", font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.btn_guardar.pack(fill="x", pady=(10, 0))

    def _descargar_guia(self):
        resultado = self.on_download_guide(self.shipment_id)
        if resultado.ok and os.path.exists(resultado.message):
            try:
                os.startfile(resultado.message)
            except AttributeError:
                messagebox.showinfo("Guia disponible", "Archivo en: " + resultado.message)
            except Exception as e:
                messagebox.showerror("Error", "No se pudo abrir el archivo: " + str(e))
        else:
            messagebox.showerror("Error", "No hay archivo de guia disponible o la ruta expiro.")

    def _confirm(self):
        try:
            cajas_val = int(self.entry_cajas.get().strip())
            if cajas_val < 0:
                raise ValueError("Las cajas no pueden ser negativas.")
        except ValueError as e:
            self.feedback.configure(text="Cantidad de cajas invalida: " + str(e), text_color="#ff5c5c")
            return

        chofer_val = self.entry_chofer.get().strip()
        fecha_val = self.entry_fecha.get().strip()

        if fecha_val:
            try:
                datetime.strptime(fecha_val, "%Y-%m-%d")
            except ValueError:
                self.feedback.configure(
                    text="La fecha debe tener formato estrictamente AAAA-MM-DD.", text_color="#ff5c5c",
                )
                return

        pedido_fijo = self.entry_pedido_logistica.get()
        resultado = self.on_confirm(self.shipment_id, pedido_fijo, cajas_val, chofer_val, fecha_val, self.current_version)

        if resultado and not resultado.ok:
            self.feedback.configure(text=resultado.message, text_color="#ff5c5c")
        else:
            self.destroy()
