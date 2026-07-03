# Matriz de Validaciones

| Campo | Backend | Frontend | Mensaje | Caso Válido | Caso Inválido |
|-------|---------|----------|---------|-------------|---------------|
| `Usuario.username` | `unique=True`, `max_length=150` | `required`, `minlength=3` | "El nombre de usuario ya existe o es inválido" | `edward123` | `ed` |
| `Usuario.email` | `RegistroForm.clean_correo()` (verifica unicidad) | `type="email"`, `required` | "Este correo ya está registrado" | `usuario@correo.com` | `usuario.correo.com` |
| `Usuario.documento` | `numeric_and_space_validator` (solo nums/espacios), `RegistroForm.clean_documento()` (7-15 dígitos, único) | `pattern="[0-9\s]*"`, `required` | "Solo se admiten números y espacios. El número de documento debe tener entre 7 y 15 dígitos." | `12345678` | `ABC123` |
| `Usuario.contrasena` | `RegistroForm.clean_contrasena()` (sin espacios), `clean()` (coincide con confirmación) | `required`, `minlength=8` | "Las contraseñas no coinciden. La contraseña no puede contener espacios." | `Pass1234` | `Pass 1234` |
| `MaterialConstruccion.nombre` | `max_length=100`, `required` | `required`, `maxlength=100` | "Nombre requerido" | "Cemento Portland" | "" |
| `MaterialConstruccion.precio_referencia` | `MinValueValidator(0)`, `MaxValueValidator(9999999999.99)` | `min=0`, `type="number"`, `inputmode="decimal"` | "Precio debe ser positivo" | `50000.00` | `-100` |
| `Stock.cantidad_actual` | `MinValueValidator(0)`, `MaxValueValidator(100000)` | `min=0`, `type="number"` | "Cantidad no puede ser negativa" | `50` | `-10` |
| `Proveedor.nit` | `numeric_and_space_validator` (solo nums/espacios) | `pattern="[0-9\s]*"`, `required` | "Solo se admiten números y espacios" | `9000000000` | `900-000-000` |
| `Proveedor.correo` | `EmailField` | `type="email"`, `required` | "Correo electrónico inválido" | `proveedor@empresa.com` | `empresa.com` |
| `DetallePedido.cantidad` | `MinValueValidator(1)` | `min=1`, `type="number"` | "Cantidad debe ser al menos 1" | `5` | `0` |
| `Pago.monto` | `MinValueValidator(0.01)` | `min=0.01`, `type="number"` | "Monto debe ser mayor a 0" | `100000` | `0` |
| `Vehiculo.placa` | `unique=True`, `max_length=10` | `required`, `maxlength=10` | "Placa ya existe o es inválida" | `ABC123` | "" |

---

## Notas Importantes
- La validación de unicidad de correo y documento se hace **solo en el formulario**, no en el modelo directamente
- El validador `numeric_and_space_validator` permite números y espacios, y se usa en `documento`, `nit` y `telefono`
- Todos los campos numéricos tienen validación de valor positivo en el backend y frontend
