# Diagrama de Entidad-Relación (MER)

```mermaid
erDiagram
    Usuario ||--|| Cliente : "usuario (PK)"
    Cliente ||--o{ Pedido : "pedidos"
    Pedido ||--o{ DetallePedido : "detalles"
    Pedido ||--o{ Entrega : "entregas"
    Pedido ||--o| Factura : "factura"
    Factura ||--o{ Pago : "pagos"
    Usuario ||--o{ Pedido : "pedidos"
    Usuario ||--o{ Pago : "registrado_por"
    Usuario ||--o{ Entrega : "conductor"
    MaterialConstruccion ||--o{ DetallePedido : "material"
    Vehiculo ||--o{ Entrega : "vehiculo"
    MetodoPago ||--o{ Pago : "codigo_metodo_pago"

    Usuario {
        int id PK
        string username
        string email
        string nombres
        string apellidos
        string documento
        string rol
    }

    Cliente {
        int usuario PK FK
        string direccion_principal
        string tipo_cliente
    }

    Pedido {
        int codigo_pedido PK
        int usuario FK
        int cliente FK
        decimal total
        string estado
    }

    DetallePedido {
        int id_detalle_pedido PK
        int pedido FK
        int material FK
        int cantidad
        decimal precio_unitario
    }

    Entrega {
        int id_entrega PK
        int pedido FK
        int conductor FK
        int vehiculo FK
        string estado
    }

    Factura {
        int id_factura PK
        int pedido FK
        int cliente FK
        decimal total
        string estado
    }

    Pago {
        int id_pago PK
        int factura FK
        decimal monto
    }
```
