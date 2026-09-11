# Decisiones de Arquitectura (ADRs)

Registro de decisiones técnicas importantes, con el problema real que las
motivó — no decisiones "porque sí" o "porque es lo estándar".

---

## ADR-001: SQLite en desarrollo, PostgreSQL en producción

**Contexto:** el proceso que este sistema reemplaza es un archivo compartido
editado simultáneamente por dos áreas, lo que causaba condiciones de carrera
(datos sobreescritos, fórmulas rotas).

**Decisión:** usar SQLite como motor de desarrollo local por su costo-cero de
infraestructura, pero documentar explícitamente que **no resuelve el problema
real** — SQLite serializa escrituras a nivel de archivo completo, no a nivel
de fila. PostgreSQL sí ofrece bloqueo a nivel de fila y transacciones ACID
reales, que es lo que el problema de negocio exige.

**Consecuencia:** la capa de acceso a datos (`infrastructure/db/session.py`)
está abstraída vía SQLAlchemy para que cambiar de motor sea una variable de
entorno, no una reescritura de código.

---

## ADR-002: Canales logísticos como dato maestro, no strings sueltos

**Contexto:** originalmente el canal (VL, PEGE, AMAZON, etc.) era un string
validado únicamente en la capa de aplicación.

**Problema encontrado:** un string libre no tiene ninguna protección a nivel
de base de datos — una inserción directa o un script mal escrito podía
introducir un canal inválido sin que nada lo impidiera.

**Decisión:** tabla `channels` con llave foránea real desde `sales_orders`.
Agregar un canal nuevo pasa a ser un `INSERT`, no una migración de esquema.

**Verificación:** se comprobó que SQLite **no aplica llaves foráneas por
default** (a diferencia de PostgreSQL) — hubo que activar explícitamente
`PRAGMA foreign_keys=ON` por conexión. Este hallazgo quedó cubierto con una
prueba de regresión (`test_fk_de_canal_se_aplica_a_nivel_de_base_de_datos`)
que falla si alguien vuelve a quitar ese pragma sin darse cuenta.

---

## ADR-003: Separación de estatus visual y motivo de discrepancia

**Contexto:** el proceso original usaba tres colores (verde/amarillo/rojo)
para el estatus de un pedido, pero el color rojo combinaba tres situaciones
distintas (devolución, retraso, daño de mercancía) sin diferenciarlas.

**Decisión:** mantener el código de 3 colores que el equipo ya reconoce
visualmente, pero separar por debajo el motivo real (`ProblemType`) cuando el
estatus es rojo — sin forzar un rediseño del hábito visual del usuario.

---

## ADR-004: Permisos por rol validados en la capa de servicio, no solo en la interfaz

**Decisión:** cada acción de negocio (cambiar estatus, capturar datos,
gestionar usuarios) valida el permiso del rol dentro del `service`, no
solo deshabilitando un botón en la vista. Un botón deshabilitado no es
control de acceso real — un usuario con las herramientas correctas podría
saltárselo.

---

## ADR-005: Ownership diferenciado por flujo, no uniforme en todo el sistema

**Contexto:** un usuario con rol Operador solo debería ver lo que él mismo
capturó — pero el flujo de dos capturas (Embarques crea, Logística completa)
significa que dos áreas distintas necesitan tocar el mismo registro.

**Decisión:** el filtro de "solo veo lo mío" aplica a la vista de creación
(Embarques ve solo las OV que él capturó), pero **no** aplica a la captura de
Logística — cualquier usuario con permiso de captura puede buscar y
completar cualquier OV pendiente, sin importar qué operador de Embarques la
creó. La regla de ownership no es un valor global del sistema, depende de
qué acción de negocio se está protegiendo.

---

## ADR-006: DTOs explícitos en vez de pasar objetos ORM a la interfaz

**Problema encontrado:** un objeto de SQLAlchemy deja de ser utilizable en
cuanto la sesión de base de datos donde se creó se cierra
(`DetachedInstanceError`) — un patrón de bug fácil de introducir sin darse
cuenta al construir controladores.

**Decisión:** los controladores nunca devuelven objetos ORM directamente a
las vistas. Construyen un DTO (`dataclass` de solo datos) dentro del mismo
bloque de sesión donde el objeto ORM todavía está activo.

---

## ADR-007: Control de concurrencia optimista (versión por registro)

**Contexto:** con dos áreas editando el mismo pedido en momentos distintos,
existe riesgo de que una edición sobrescriba a otra sin que nadie se entere.

**Decisión:** cada `Shipment` lleva un campo `version` que se incrementa en
cada actualización. Si un usuario intenta guardar con una versión distinta a
la que hay en base de datos, el sistema rechaza el cambio con un mensaje
explícito en vez de sobrescribir en silencio.
