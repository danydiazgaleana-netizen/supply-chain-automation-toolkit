# WMS · Sistema de Conciliación Logística-Embarques

Aplicación de escritorio (Python + CustomTkinter + SQLAlchemy) que centraliza
la captura de datos entre dos áreas operativas de una cadena de suministro
—Logística y Embarques— y detecta automáticamente discrepancias entre lo que
cada una declara, antes de que un pedido salga a reparto.

> **Contexto:** este proyecto nació como propuesta de mejora continua durante
> mi estancia como becaria de Logística, a partir de entrevistas de campo con
> el personal de Embarques y Logística. Todos los datos de ejemplo en este
> repositorio son ficticios.

## El problema que resuelve

En muchas operaciones logísticas sin un WMS/ERP, la comunicación entre quien
genera el pedido y quien lo despacha ocurre por correo o chat, sin
trazabilidad. Esto genera:

- Números de pedido o cantidades que no coinciden entre lo declarado y lo
  recibido, detectados hasta que ya es tarde para corregir.
- Nadie sabe, en tiempo real, cuáles pedidos ya están confirmados por ambas
  áreas y cuáles siguen pendientes.
- La corrección de errores depende de revisión manual, pedido por pedido.

## Cómo lo resuelve este sistema

1. **Embarques** captura el pedido inicial (cliente, OV, cajas, bolsas) desde
   su fuente de datos.
2. **Logística** completa después los datos operativos del mismo pedido
   (número de guía, fechas, paquetería, cantidad propia).
3. El sistema **compara automáticamente** ambas capturas. Si no coinciden,
   marca el pedido como discrepancia y **bloquea el despacho** hasta que se
   corrija — sin intervención manual para detectarlo.
4. Control de acceso por rol (Administrador, Supervisor, Operador, Consulta),
   con permisos validados en la capa de negocio, no solo ocultos en la
   interfaz.

## Decisiones de arquitectura

Documentadas con su razonamiento en [`docs/decisiones_arquitectura.md`](docs/decisiones_arquitectura.md):

- **Separación en capas** (modelos / servicios / controladores / vistas), para
  que la lógica de negocio no dependa de CustomTkinter y sea portable a un
  backend web en el futuro.
- **SQLite en desarrollo, Postgres en producción** — decisión explícita por
  el problema real que resuelve (condiciones de carrera en la captura
  concurrente), no por preferencia arbitraria.
- **Canales logísticos como dato maestro** (tabla `channels` con llave
  foránea), no strings sueltos validados solo en la aplicación.
- **Autenticación con bcrypt**, mensajes de error idénticos en login fallido
  (anti-enumeración de usuarios), y control de concurrencia optimista
  (versión por registro) para evitar que dos operadores se pisen los cambios
  sin darse cuenta.

## Pruebas automatizadas

El proyecto incluye una suite de `pytest` que cubre autenticación, permisos
por rol, la máquina de estados de un embarque, y el motor de detección de
discrepancias — incluyendo casos de regresión reales encontrados durante el
desarrollo (por ejemplo, un bug donde SQLite no aplicaba llaves foráneas por
default, silenciosamente).

```bash
python -m pytest
```

## Stack técnico

- **Python 3.12+**
- **CustomTkinter** — interfaz de escritorio
- **SQLAlchemy 2.0** — ORM
- **SQLite** (desarrollo) / **PostgreSQL** (producción, vía Docker Compose)
- **Pydantic** — validación de datos de entrada
- **bcrypt** — hashing de contraseñas
- **pytest** — pruebas automatizadas
- **openpyxl** — generación de reportes ejecutivos en Excel

## Cómo correrlo localmente

```bash
# 1. Clonar y crear entorno virtual
git clone <url-del-repo>
cd wms-embarques
python -m venv .venv
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # macOS/Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Base de datos local (SQLite, sin necesidad de instalar nada más)
$env:WMS_DB_URL = "sqlite:///wms.db"      # PowerShell
export WMS_DB_URL="sqlite:///wms.db"       # bash

# 4. Inicializar datos base
python -m scripts.seed_admin
python -m scripts.seed_channels

# 5. Correr la aplicación
python run.py
```

## Estado del proyecto

Prototipo funcional, validado con datos ficticios y presentado como
propuesta de mejora continua. Próximo paso: piloto controlado de un mes en
un entorno operativo real, para medir tiempo de revisión manual evitado.

## Roadmap

- [ ] Selector de fecha en captura (en vez de texto libre)
- [ ] Reportes ejecutivos con detalle de discrepancias
- [ ] Notificaciones en tiempo real entre áreas
- [ ] Migración de validación a Postgres en ambiente de piloto
- [ ] Exploración de escaneo de código de barras para validación física
      de guías (fase posterior, requiere su propio desarrollo)

## Autora

Proyecto desarrollado por [Tu nombre] como parte de mi trabajo en mejora
continua de procesos de cadena de suministro. Construido con apoyo de
herramientas de IA para el desarrollo, bajo dirección propia del diseño,
las reglas de negocio y las decisiones de producto.
