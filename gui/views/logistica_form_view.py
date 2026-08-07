"""
Vista de Captura Logística - Grupo REV
Versión profesional con arquitectura de servicios.
"""
from __future__ import annotations
import customtkinter as ctk
from tkinter import filedialog
import os
import shutil

from gui.controllers.sales_order_controller import SalesOrderController
from core.services.shipment_service import ShipmentService
from infrastructure.db.session import get_session


class LogisticaFormView(ctk.CTkFrame):
    def __init__(self, master, controller: SalesOrderController, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.controller = controller
        self.grid_columnconfigure(0, weight=1)

        # Título
        ctk.CTkLabel(
            self, text="📦 Captura Logística",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 16))

        # Formulario scrollable
        form = ctk.CTkScrollableFrame(self, label_text=" Ingreso Logístico Exclusivo ")
        form.grid(row=1, column=0, sticky="nswe", pady=(0, 10))
        form.grid_columnconfigure(0, weight=0)
        form.grid_columnconfigure(1, weight=1)

        # --- Campos del formulario ---
        self.fields = {}

        # Canal
        self._add_label(form, "Canal / Bitácora:", 0)
        self.fields['canal'] = ctk.CTkComboBox(
            form, values=self.controller.list_active_channel_codes(),
            width=350, state="readonly"
        )
        self.fields['canal'].grid(row=0, column=1, sticky="w", padx=20, pady=8)

        # OV
        self._add_label(form, "Orden de Venta (OV):", 1)
        self.fields['ov'] = ctk.CTkEntry(form, width=350, placeholder_text="Ej. OV-9923")
        self.fields['ov'].grid(row=1, column=1, sticky="w", padx=20, pady=8)

        # Número de pedido
        self._add_label(form, "Número de pedido:", 2)
        self.fields['pedido'] = ctk.CTkEntry(form, width=350, placeholder_text="Ej. 54892")
        self.fields['pedido'].grid(row=2, column=1, sticky="w", padx=20, pady=8)

        # Cliente
        self._add_label(form, "Nombre del cliente:", 3)
        self.fields['cliente'] = ctk.CTkEntry(form, width=350, placeholder_text="Razón social")
        self.fields['cliente'].grid(row=3, column=1, sticky="w", padx=20, pady=8)

        # Cajas
        self._add_label(form, "Cajas:", 4)
        self.fields['cajas'] = ctk.CTkEntry(form, width=350, placeholder_text="0")
        self.fields['cajas'].grid(row=4, column=1, sticky="w", padx=20, pady=8)

        # Bolsas
        self._add_label(form, "Bolsas:", 5)
        self.fields['bolsas'] = ctk.CTkEntry(form, width=350, placeholder_text="0")
        self.fields['bolsas'].grid(row=5, column=1, sticky="w", padx=20, pady=8)

        # Fecha de envío
        self._add_label(form, "Fecha de Envío:", 6)
        self.fields['f_envio'] = ctk.CTkEntry(form, width=350, placeholder_text="AAAA-MM-DD")
        self.fields['f_envio'].grid(row=6, column=1, sticky="w", padx=20, pady=8)

        # Fecha de entrega
        self._add_label(form, "Fecha de Entrega:", 7)
        self.fields['f_entrega'] = ctk.CTkEntry(form, width=350, placeholder_text="AAAA-MM-DD")
        self.fields['f_entrega'].grid(row=7, column=1, sticky="w", padx=20, pady=8)

        # Ubicación
        self._add_label(form, "Ubicación:", 8)
        self.fields['ubicacion'] = ctk.CTkEntry(form, width=350, placeholder_text="Ciudad / Destino")
        self.fields['ubicacion'].grid(row=8, column=1, sticky="w", padx=20, pady=8)

        # Paquetería
        self._add_label(form, "Paquetería:", 9)
        self.fields['paqueteria'] = ctk.CTkEntry(form, width=350, placeholder_text="Empresa de envío")
        self.fields['paqueteria'].grid(row=9, column=1, sticky="w", padx=20, pady=8)

        # Valor MXN
        self._add_label(form, "Valor ($MXN):", 10)
        self.fields['valor'] = ctk.CTkEntry(form, width=350, placeholder_text="0.00")
        self.fields['valor'].grid(row=10, column=1, sticky="w", padx=20, pady=8)

        # Número de guía
        self._add_label(form, "Número de Guía:", 11)
        self.fields['num_guia'] = ctk.CTkEntry(form, width=350, placeholder_text="Guía de transporte")
        self.fields['num_guia'].grid(row=11, column=1, sticky="w", padx=20, pady=8)

        # Archivo de guía PDF
        self._add_label(form, "Archivo de Guía (PDF):", 12)
        frame_btn = ctk.CTkFrame(form, fg_color="transparent")
        frame_btn.grid(row=12, column=1, sticky="w", padx=20, pady=8)
        ctk.CTkButton(
            frame_btn, text="📂 Seleccionar PDF", width=140,
            command=self._seleccionar_pdf, fg_color="#334155"
        ).pack(side=ctk.LEFT, padx=(0, 10))
        self.lbl_pdf = ctk.CTkLabel(frame_btn, text="Ningún archivo", text_color="gray", font=ctk.CTkFont(slant="italic"))
        self.lbl_pdf.pack(side=ctk.LEFT)

        # Feedback
        self.feedback = ctk.CTkLabel(form, text="", text_color="gray60")
        self.feedback.grid(row=13, column=0, columnspan=2, sticky="w", padx=25, pady=(10, 0))

        # Botón guardar
        ctk.CTkButton(
            form, text="💾 Registrar en Base de Datos",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0284c7", hover_color="#0369a1",
            height=40, command=self._guardar
        ).grid(row=14, column=0, columnspan=2, pady=25)

        # Variables internas
        self._archivo_pdf_temp = ""

    def _add_label(self, parent, texto, row):
        ctk.CTkLabel(
            parent, text=texto,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        ).grid(row=row, column=0, sticky="w", padx=25, pady=8)

    def _seleccionar_pdf(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar Guía PDF",
            filetypes=[("Archivos PDF", "*.pdf")]
        )
        if archivo:
            self._archivo_pdf_temp = archivo
            self.lbl_pdf.configure(text=os.path.basename(archivo), text_color="green")

    def _guardar(self):
        # Recoger datos
        canal = self.fields['canal'].get().strip()
        ov = self.fields['ov'].get().strip()
        pedido = self.fields['pedido'].get().strip()
        cliente = self.fields['cliente'].get().strip()
        cajas = self.fields['cajas'].get().strip()
        bolsas = self.fields['bolsas'].get().strip()
        f_envio = self.fields['f_envio'].get().strip()
        f_entrega = self.fields['f_entrega'].get().strip()
        ubicacion = self.fields['ubicacion'].get().strip()
        paqueteria = self.fields['paqueteria'].get().strip()
        valor = self.fields['valor'].get().strip()
        num_guia = self.fields['num_guia'].get().strip()

        # Validación de obligatorios
        if not ov or not cliente or not pedido or not canal:
            self.feedback.configure(text="❌ Faltan datos obligatorios (OV, Cliente, Pedido, Canal).", text_color="#ff5c5c")
            return

        try:
            # Guardar usando el servicio (a través del controller)
            result = self.controller.create_order(
                order_number=ov,
                customer_name=cliente,
                channel=canal,
                # Pasamos los campos extra como kwargs
                cajas=cajas,
                bolsas=bolsas,
                fecha_envio=f_envio,
                fecha_entrega=f_entrega,
                ubicacion=ubicacion,
                paqueteria=paqueteria,
                valor_mxn=valor,
                numero_guia=num_guia
            )

            if result.ok:
                # Si hay archivo PDF, copiarlo
                if self._archivo_pdf_temp and os.path.exists(self._archivo_pdf_temp):
                    self._guardar_pdf(ov, self._archivo_pdf_temp)

                self.feedback.configure(text=f"✅ {result.message}", text_color="#3ddc84")
                # Limpiar campos
                self.fields['ov'].delete(0, ctk.END)
                self.fields['pedido'].delete(0, ctk.END)
                self.fields['cliente'].delete(0, ctk.END)
                self.fields['cajas'].delete(0, ctk.END)
                self.fields['bolsas'].delete(0, ctk.END)
                self.fields['f_envio'].delete(0, ctk.END)
                self.fields['f_entrega'].delete(0, ctk.END)
                self.fields['ubicacion'].delete(0, ctk.END)
                self.fields['paqueteria'].delete(0, ctk.END)
                self.fields['valor'].delete(0, ctk.END)
                self.fields['num_guia'].delete(0, ctk.END)
                self._archivo_pdf_temp = ""
                self.lbl_pdf.configure(text="Ningún archivo", text_color="gray")
            else:
                self.feedback.configure(text=f"❌ {result.message}", text_color="#ff5c5c")
        except Exception as e:
            self.feedback.configure(text=f"❌ Error inesperado: {e}", text_color="#ff5c5c")

    def _guardar_pdf(self, ov: str, ruta_origen: str):
        """Copia el PDF a la carpeta de guías."""
        try:
            carpeta_guias = "./guias_maestras"
            os.makedirs(carpeta_guias, exist_ok=True)
            nombre_destino = f"{ov}_{os.path.basename(ruta_origen)}"
            ruta_destino = os.path.join(carpeta_guias, nombre_destino)
            shutil.copy2(ruta_origen, ruta_destino)
            # Aquí podrías guardar la ruta en la base de datos si quieres
            # (ya se guarda en `archivo_guia` a través del controller)
        except Exception as e:
            print(f"Error al copiar PDF: {e}")