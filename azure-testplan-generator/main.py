"""CLI entrypoint for Azure Test Plan and Suite generation."""

from __future__ import annotations

import argparse
import time

from colorama import just_fix_windows_console
from rich.console import Console
from rich.progress import track
from rich.table import Table

from config.settings import ConfigurationError, Settings
from models.entities import ReportRecord, UserStory
from services.azure_connection import (
    AzureApiError,
    AzureAuthError,
    AzureNetworkError,
    AzureNotFoundError,
    AzureServerError,
    AzureConnection,
)
from services.boards import BoardsService
from services.suites import SuitesService
from services.testplans import TestPlansService
from utils.helpers import (
    build_iteration_path,
    build_test_plan_name,
    ensure_directories,
    export_csv_report,
)
from utils.logger import setup_logger


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Generador automático de Test Plans y Test Suites en Azure DevOps."
    )
    parser.add_argument(
        "--sprint",
        type=int,
        required=True,
        help="Número del Sprint (ejemplo: --sprint 11).",
    )
    return parser.parse_args()


def _log_and_capture_error(
    logger,
    errors: list[str],
    message: str,
) -> None:
    logger.error(message)
    errors.append(message)


def _process_stories(
    stories: list[UserStory],
    plan_id: int,
    root_suite_id: int,
    suites_service: SuitesService,
    existing_names: set[str],
    logger,
    console: Console,
    records: list[ReportRecord],
) -> tuple[int, int]:
    created_count = 0
    duplicated_count = 0

    for story in track(stories, description="Procesando historias...", console=console):
        suite_name = story.suite_name
        normalized_name = suites_service.normalize_name(suite_name)
        if normalized_name in existing_names:
            duplicated_count += 1
            records.append(
                ReportRecord.from_outcome(
                    work_item_id=story.id,
                    title=story.title,
                    suite_created=False,
                    result="Existente",
                    message="La suite ya existía y no fue creada nuevamente.",
                )
            )
            continue

        try:
            suites_service.create_static_suite(plan_id, root_suite_id, suite_name)
            existing_names.add(normalized_name)
            created_count += 1
            records.append(
                ReportRecord.from_outcome(
                    work_item_id=story.id,
                    title=story.title,
                    suite_created=True,
                    result="Creada",
                    message="Suite creada correctamente.",
                )
            )
            logger.info("Suite creada: %s", suite_name)
        except AzureApiError as exc:
            error_message = (
                f"No se pudo crear la suite '{suite_name}'. "
                f"Detalle: {str(exc)}"
            )
            logger.error(error_message)
            records.append(
                ReportRecord.from_outcome(
                    work_item_id=story.id,
                    title=story.title,
                    suite_created=False,
                    result="Error",
                    message=error_message,
                )
            )
    return created_count, duplicated_count


def _print_summary(
    console: Console,
    project: str,
    sprint: int,
    stories_count: int,
    suites_existing_count: int,
    suites_created_count: int,
    errors_count: int,
    elapsed_seconds: float,
) -> None:
    summary = Table(title="Resumen de ejecución")
    summary.add_column("Campo", style="cyan", no_wrap=True)
    summary.add_column("Valor", style="white")

    summary.add_row("Proyecto", project)
    summary.add_row("Sprint", str(sprint))
    summary.add_row("Historias encontradas", str(stories_count))
    summary.add_row("Suites existentes", str(suites_existing_count))
    summary.add_row("Suites creadas", str(suites_created_count))
    summary.add_row("Errores", str(errors_count))
    summary.add_row("Tiempo total (s)", f"{elapsed_seconds:.2f}")

    console.print(summary)


def main() -> int:
    """Run the CLI workflow."""
    just_fix_windows_console()
    console = Console()
    ensure_directories(["logs", "reports"])
    logger, log_file = setup_logger("logs")
    records: list[ReportRecord] = []
    errors: list[str] = []

    start_time = time.perf_counter()

    try:
        args = parse_args()
        settings = Settings.from_env(".env")
        sprint = args.sprint
        if sprint <= 0:
            raise ConfigurationError("El número de Sprint debe ser mayor que cero.")

        plan_name = build_test_plan_name(sprint)
        iteration_path = build_iteration_path(settings.base_iteration, sprint)

        connection = AzureConnection(settings)
        boards_service = BoardsService(connection, settings.azure_project, settings.area_path)
        testplans_service = TestPlansService(connection)
        suites_service = SuitesService(connection)

        connection.validate_connection()
        logger.info("Conexión validada con Azure DevOps.")

        stories = boards_service.get_user_stories_for_iteration(iteration_path)
        if not stories:
            message = (
                f"No se encontraron historias de usuario para el Sprint {sprint} "
                f"en la iteración '{iteration_path}'."
            )
            _log_and_capture_error(logger, errors, message)

        plan, created_plan = testplans_service.get_or_create_plan(
            plan_name=plan_name,
            area_path=settings.area_path,
            iteration_path=iteration_path,
        )
        plan_id = int(plan["id"])
        logger.info(
            "Test Plan %s: %s (ID: %s)",
            "creado" if created_plan else "encontrado",
            plan_name,
            plan_id,
        )

        suites = suites_service.list_suites(plan_id)

        plan_details = testplans_service.get_plan(plan_id)
        root_suite_id = suites_service.get_root_suite_id(plan_details, suites)
        if root_suite_id is None:
            message = (
                f"No se encontró Suite raíz para el Test Plan ID {plan_id}. "
                "No se crearán suites para evitar inconsistencias."
            )
            _log_and_capture_error(logger, errors, message)
            root_suite_id = -1

        if root_suite_id > 0:
            existing_names = suites_service.get_child_suite_names(plan_id, root_suite_id)
        else:
            existing_names = set()
        suites_existing_count = len(existing_names)

        suites_created_count = 0
        if stories and root_suite_id > 0:
            created, _ = _process_stories(
                stories=stories,
                plan_id=plan_id,
                root_suite_id=root_suite_id,
                suites_service=suites_service,
                existing_names=existing_names,
                logger=logger,
                console=console,
                records=records,
            )
            suites_created_count = created

        report_path = export_csv_report(records, "reports")
        logger.info("Reporte generado: %s", report_path)
        elapsed_seconds = time.perf_counter() - start_time

        _print_summary(
            console=console,
            project=settings.azure_project,
            sprint=sprint,
            stories_count=len(stories),
            suites_existing_count=suites_existing_count,
            suites_created_count=suites_created_count,
            errors_count=len(errors),
            elapsed_seconds=elapsed_seconds,
        )
        console.print(f"[bold green]Log:[/bold green] {log_file}")
        console.print(f"[bold green]Reporte:[/bold green] {report_path}")
        return 0

    except ConfigurationError as exc:
        message = f"Error de configuración: {str(exc)}"
        _log_and_capture_error(logger, errors, message)
        console.print(f"[bold red]{message}[/bold red]")
    except AzureAuthError as exc:
        message = f"Error de autenticación/autorización ({exc.status_code}): {str(exc)}"
        _log_and_capture_error(logger, errors, message)
        console.print(f"[bold red]{message}[/bold red]")
    except AzureNotFoundError as exc:
        message = f"Recurso no encontrado ({exc.status_code}): {str(exc)}"
        _log_and_capture_error(logger, errors, message)
        console.print(f"[bold red]{message}[/bold red]")
    except AzureServerError as exc:
        message = f"Error del servidor Azure DevOps ({exc.status_code}): {str(exc)}"
        _log_and_capture_error(logger, errors, message)
        console.print(f"[bold red]{message}[/bold red]")
    except AzureNetworkError as exc:
        message = f"Error de conectividad: {str(exc)}"
        _log_and_capture_error(logger, errors, message)
        console.print(f"[bold red]{message}[/bold red]")
    except AzureApiError as exc:
        message = f"Error de API Azure DevOps: {str(exc)}"
        _log_and_capture_error(logger, errors, message)
        console.print(f"[bold red]{message}[/bold red]")
    except Exception as exc:
        message = f"Error inesperado: {str(exc)}"
        _log_and_capture_error(logger, errors, message)
        console.print(f"[bold red]{message}[/bold red]")

    elapsed_seconds = time.perf_counter() - start_time
    _print_summary(
        console=console,
        project="N/A",
        sprint=0,
        stories_count=0,
        suites_existing_count=0,
        suites_created_count=0,
        errors_count=len(errors),
        elapsed_seconds=elapsed_seconds,
    )
    console.print(f"[bold yellow]Log:[/bold yellow] {log_file}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

