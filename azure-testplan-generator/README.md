# Azure Test Plan Generator

Aplicación en **Python 3.11+** para crear de forma idempotente **Test Plans** y **Test Suites** en Azure DevOps usando exclusivamente la **REST API 7.1** (sin SDK oficial).

## Características

- Lee configuración desde `.env` (sin valores fijos en código).
- Recibe Sprint por CLI: `python main.py --sprint 11`.
- Construye automáticamente:
  - Iteration Path: `BASE_ITERATION\Sprint X`
  - Test Plan: `Atendido 2.0_Sprint X`
- Consulta Historias de Usuario (`Historia de Usuario`) vía WIQL.
- Crea Test Plan solo si no existe.
- Reutiliza Suite raíz del plan.
- Crea únicamente suites faltantes con formato exacto `ID : Título`.
- Idempotente: no duplica, no elimina, no modifica suites existentes.
- Genera:
  - Log por ejecución en `logs/`
  - Reporte CSV por ejecución en `reports/`
- Resumen en consola con Rich + barra de progreso.

## Estructura del proyecto

```text
azure-testplan-generator/
├── .env
├── .gitignore
├── README.md
├── requirements.txt
├── main.py
├── config/
│   ├── __init__.py
│   └── settings.py
├── models/
│   ├── __init__.py
│   └── entities.py
├── services/
│   ├── __init__.py
│   ├── azure_connection.py
│   ├── boards.py
│   ├── testplans.py
│   └── suites.py
├── utils/
│   ├── __init__.py
│   ├── logger.py
│   └── helpers.py
├── logs/
│   └── .gitkeep
└── reports/
    └── .gitkeep
```

## Requisitos

- Python 3.11 o superior
- PAT con permisos en Azure DevOps:
  - **Work Items (Read)**
  - **Test Management (Read & write)**
  - **Project and Team (Read)** (recomendado para validación)

## Instalación

```bash
pip install -r requirements.txt
```

## Configuración (`.env`)

El archivo debe contener solo variables de entorno:

```env
AZURE_ORGANIZATION=grupo-exito
AZURE_PROJECT=GCIT-Agile
AZURE_PAT=tu_pat_aqui
AREA_PATH=GCIT-Agile\Dirección de Soluciones\Soluciones digitales\Atendido 2.0
BASE_ITERATION=GCIT-Agile\Dirección de Soluciones\Soluciones digitales\Atendido 2.0
API_VERSION=7.1
```

## Crear PAT en Azure DevOps

1. Entra a Azure DevOps.
2. Perfil de usuario > **Personal access tokens**.
3. Crea un token con expiración y permisos mínimos requeridos.
4. Copia el token y pégalo en `AZURE_PAT`.

## Ejecución

```bash
python main.py --sprint 11
```

## Flujo funcional

1. Carga `.env` y valida configuración.
2. Valida conexión con Azure DevOps.
3. Construye Iteration Path y nombre del plan.
4. Consulta Historias de Usuario del Sprint por WIQL.
5. Busca o crea Test Plan.
6. Obtiene Suite raíz y suites existentes.
7. Crea solo suites faltantes en formato `ID : Título`.
8. Imprime resumen, guarda log y genera CSV.

## Reporte CSV

Se genera en `reports/` con columnas:

- ID
- Título
- Suite creada
- Resultado
- Fecha
- Mensaje

## Solución de problemas

- **401/403**: PAT inválido o sin permisos suficientes.
- **404**: organización/proyecto/ruta no existe o endpoint no accesible.
- **Sin historias**: Sprint sin historias de tipo `Historia de Usuario` o Iteration Path incorrecto.
- **No encuentra Suite raíz**: plan inconsistente o falta acceso al módulo de Test Plans.
- **Timeout/conexión**: validar red, proxy, VPN o disponibilidad de Azure DevOps.

## Escalabilidad futura

La arquitectura separada por capas deja preparada la integración de:

- Creación automática de Test Cases.
- Sincronización con Excel.
- Actualización de resultados de ejecución.
- Creación de Test Runs.
- Asociación de Test Cases a Historias.
- Ejecución desde Azure Pipelines.
- Interfaz gráfica.

