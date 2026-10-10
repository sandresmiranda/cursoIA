"""Lógica de tareas. Puro: no importa Streamlit ni toca estado global.

Esta capa existe separada de la interfaz por una razón concreta — los tests
corren sin Streamlit instalado, sin navegador y sin servidor, en milisegundos.
Si algo aquí necesitara la UI, esa separación estaría rota.

Las funciones no mutan la lista que reciben: devuelven una lista nueva. Es la
razón por la que la UI puede guardar el resultado en st.session_state sin
preocuparse de efectos alias.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "Task",
    "Filter",
    "TaskError",
    "EmptyTaskError",
    "TaskNotFoundError",
    "add_task",
    "toggle_task",
    "filter_tasks",
    "delete_task",
    "edit_task",
    "MAX_LENGTH",
]


# Longitud maxima del texto. No es capricho: sin tope, alguien pega un
# log de 10 MB y la interfaz queda inutilizable. Es un limite holgado
# para un titulo de tarea y holgado a proposito — no queremos que el
# usuario研究发现 que "no cabe" por 20 caracteres.
MAX_LENGTH = 500


# ----- Errores de dominio -----
# Excepciones en vez de tuplas (tasks, error): la UI las captura con un
# try/except y los tests usan pytest.raises, que falla con un mensaje claro.


class TaskError(Exception):
    """Base de todos los errores de esta capa."""


class EmptyTaskError(TaskError):
    """El texto viene vacío o compuesto solo por espacios."""


class TaskNotFoundError(TaskError):
    """No existe ninguna tarea con el id pedido."""


class TaskTooLongError(TaskError):
    """El texto supera MAX_LENGTH."""


# ----- Modelo -----


@dataclass(frozen=True)
class Task:
    """Una tarea.

    frozen=True a propósito: si una función devolviera la misma instancia
    mutada, el estado viejo de la UI apuntaría al objeto nuevo y no se vería
    ningún cambio en pantalla. Congelada, cada cambio genera un objeto nuevo.
    """

    id: str
    text: str
    completed: bool = False


class Filter(str, Enum):
    """Los tres modos de filtro. str para que st.radio los muestre sin adapts."""

    ALL = "todas"
    PENDING = "pendientes"
    COMPLETED = "completadas"


# ----- Operaciones -----


def _validar(text: str) -> str:
    """Normaliza y valida el texto. La usan add_task y edit_task.

    Que la validacion este en un solo lugar es lo que hace imposible que
    agregar acepte un texto que editar rechazaria.
    """
    if not isinstance(text, str):
        raise EmptyTaskError("El texto de una tarea debe ser una cadena.")

    clean = text.strip()
    if not clean:
        raise EmptyTaskError("No puedes agregar una tarea vacía.")
    if len(clean) > MAX_LENGTH:
        raise TaskTooLongError(
            f"La tarea es demasiado larga (máximo {MAX_LENGTH} caracteres)."
        )
    return clean


def add_task(tasks: Iterable[Task], text: str) -> list[Task]:
    """Devuelve `tasks` más una tarea nueva al final.

    Lanza EmptyTaskError si el texto está vacío o es solo espacio en blanco
    (incluidos tabuladores y saltos de línea).

    El texto se guarda normalizado con strip(), para que "  comprar pan  " y
    "comprar pan" no se guarden como dos tareas distintas que se ven iguales.
    """
    return [*tasks, Task(id=uuid.uuid4().hex, text=_validar(text), completed=False)]


def toggle_task(tasks: Iterable[Task], task_id: str) -> list[Task]:
    """Invierte `completed` de la tarea con ese id.

    Lanza TaskNotFoundError si no existe. Un id desconocido casi siempre es un
    bug — una lista desactualizada en la UI — y dejarlo pasar en silencio
    devolvería una lista igual, que parece que el clic no hizo nada.
    """
    tasks = list(tasks)
    if not any(task.id == task_id for task in tasks):
        raise TaskNotFoundError(f"No existe una tarea con id {task_id!r}.")

    return [
        Task(id=task.id, text=task.text, completed=not task.completed)
        if task.id == task_id
        else task
        for task in tasks
    ]


def delete_task(tasks: Iterable[Task], task_id: str) -> list[Task]:
    """Devuelve la lista sin la tarea indicada.

    Lanza TaskNotFoundError si no existe, por el mismo motivo que
    toggle_task: borrar algo que no está es un bug, no un no-op.
    """
    tareas = list(tasks)
    if not any(t.id == task_id for t in tareas):
        raise TaskNotFoundError(f"No existe una tarea con id {task_id!r}.")
    return [t for t in tareas if t.id != task_id]


def edit_task(tasks: Iterable[Task], task_id: str, text: str) -> list[Task]:
    """Devuelve la lista con el texto de esa tarea reemplazado.

    Editar conserva id y completed: cambiar el texto no debe des-completar
    una tarea, porque seria perder informacion que el usuario no pidio
    tocar. Aplica la misma validacion que add_task.
    """
    tareas = list(tasks)
    if not any(t.id == task_id for t in tareas):
        raise TaskNotFoundError(f"No existe una tarea con id {task_id!r}.")

    limpio = _validar(text)
    return [
        Task(id=t.id, text=limpio, completed=t.completed) if t.id == task_id else t
        for t in tareas
    ]


_PREDICATES = {
    Filter.ALL: lambda task: True,
    Filter.PENDING: lambda task: not task.completed,
    Filter.COMPLETED: lambda task: task.completed,
}


def filter_tasks(tasks: Iterable[Task], criteria: Filter = Filter.ALL) -> list[Task]:
    """Devuelve las tareas que cumplen `criteria`, en el orden original.

    Lanza ValueError si `criteria` no es un Filter conocido. Devolver todo sin
    avisar sería el peor fallo posible: un typo en el filtro rompería la vista
    sin ningún síntoma visible.
    """
    try:
        predicate = _PREDICATES[criteria]
    except KeyError:
        raise ValueError(f"Filtro desconocido: {criteria!r}.") from None

    return [task for task in tasks if predicate(task)]

