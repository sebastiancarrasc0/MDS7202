# Datos del Laboratorio 14

Todo lo que hay en esta carpeta es **ficticio**. Mar y Huerta SpA, sus bodegas, sus
cifras y sus políticas se inventaron para el laboratorio y no describen a ninguna
empresa real. Son insumos inmutables: no se editan durante el trabajo.

## `politicas/`

Diez documentos de políticas internas de reposición, en Markdown. Cada regla vive en
su propia sección (`##` o `###`), porque el agente las recupera de a una. Los seis
documentos de producto traen tres secciones con las cifras que usa el sistema:
**Cobertura mínima**, **Urgencia** y **Cobertura objetivo**.

| Documento | Productos o tema |
| --- | --- |
| `pescado.md` | Merluza austral y salmón atlántico |
| `tomate_y_palta.md` | Tomate larga vida y palta hass |
| `lechuga.md`, `pollo.md`, `huevos.md`, `leche_uht.md` | Un producto cada uno |
| `cadena_de_frio.md` | Temperaturas y qué hacer si se corta el frío |
| `proveedores_y_compras.md` | Proveedor aprobado, cotizaciones y monto de visación |
| `sustitucion.md` | Qué ofrecer cuando falta un producto |
| `urgencias.md` | Reposición necesaria frente a urgente |

## Datos de las bodegas

El servidor de bodegas (`src/reposicion/servidor/`) entrega las mismas cifras cada vez.
**Cobertura** es el número de días que alcanza el stock de una bodega: `stock / consumo diario`.

| Campo | Significado |
| --- | --- |
| `cantidad` | Stock actual de ese producto en esa bodega |
| `unidad` | `kg`, `unidades`, `bandejas` (de 30 huevos) o `litros` |
| `consumo_diario` | Cuánto sale de esa bodega por día |
| `dias_cobertura` | `cantidad / consumo_diario` |
