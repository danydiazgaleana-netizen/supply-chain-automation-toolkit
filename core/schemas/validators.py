from pydantic import BaseModel, constr, Field, validator
from typing import Optional
from datetime import datetime

class ShipmentUpdateSchema(BaseModel):
    numero_pedido: constr(min_length=1, max_length=50)
    cajas: int = Field(gt=0, description="Debe ser mayor a 0")
    chofer: Optional[str] = Field(None, max_length=100)
    fecha_entrega: str
    hora_entrega: Optional[str] = Field(None, max_length=10)
    nombre_quien_entrega: Optional[str] = Field(None, max_length=120)
    comentarios: Optional[str] = Field(None, max_length=2000)
    version: int = Field(ge=1, description="Version del embarque para control de concurrencia")

    @validator('fecha_entrega')
    def validate_fecha(cls, v):
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
            except ValueError:
                raise ValueError('Fecha de entrega debe tener formato YYYY-MM-DD')
        return v

    @validator('cajas')
    def validate_cajas(cls, v):
        if v < 0:
            raise ValueError('Las cajas no pueden ser negativas')
        return v
