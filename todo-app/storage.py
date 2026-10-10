"""Persistencia en SQLite. Segunda capa, entre la lógica pura y la UI.

Acá vive SOLO I/O: leer y escribir filas. Ninguna regla de dominio. La
validación sigue estando en tasks.py y storage no la duplica — sivivieran en los
dos lados, "qué es una tarea válida" tendria dos respuestas y la app elegiría una.

Tampoco importa streamlit, así que se testea con un archivo temporal y sin
levantar nada.

El orden de las tareas lo fija `seq`, no el rowid de SQLite: rowid se reutiliza
cuando borrás la ultima fila, y eso puede reordenar la lista sin que nadie haya
pedido un reordenamiento.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from tasks import Task

__all__ = ["TaskStore", "DEFAULT_DB_PATH"]

# TODO_DB permite apuntar a otro archivo. Sin esto, probar la app contra una
# base temporal exigiría monkeypatchear el módulo desde afuera — que es
# justo el tipo de acoplamiento que este proyecto evita.
DEFAULT_DB_PATH = Path(os.environ.get("TODO_DB") or Path(__file__).with_name("tasks.db"))

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id        TEXT    PRIMARY KEY,
    text      TEXT    NOT NULL,
    completed INTEGER NOT NULL DEFAULT 0,
    seq       INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_seq ON tasks (seq);
"""


class TaskStore:
    """Guarda las tareas en un archivo SQLite.

    Abre y cierra una conexión por operación en vez de mantener una viva. En
    Streamlit el script se re-ejecuta en cada interacción, así que una conexión
    module-level quedaría vieja y con un file lock encima. A esta escala el
    costo de abrir es irrelevante.
    """

    def __init__(self, path: str | Path = DEFAULT_DB_PATH) -> None:
        self._path = Path(path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._path)
        try:
            conn.row_factory = sqlite3.Row
            conn.executescript(_SCHEMA)
            yield conn
            conn.commit()
        finally:
            conn.close()

    def load(self) -> list[Task]:
        """Devuelve todas las tareas en orden de inserción."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, text, completed FROM tasks ORDER BY seq ASC"
            ).fetchall()
        return [Task(id=r["id"], text=r["text"], completed=bool(r["completed"])) for r in rows]

    def insert(self, task: Task) -> None:
        """Agrega una tarea al final de la lista."""
        with self._connect() as conn:
            conn.execute(
                # MAX+1 y no COUNT: si alguna vez se borra una fila, COUNT pisa
                # tareas y el orden se mezcla.
                "INSERT INTO tasks (id, text, completed, seq) "
                "VALUES (?, ?, ?, (SELECT COALESCE(MAX(seq), 0) + 1 FROM tasks))",
                (task.id, task.text, int(task.completed)),
            )

    def update(self, task: Task) -> None:
        """Sobrescribe una tarea existente. Usada por completar y por editar."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE tasks SET text = ?, completed = ? WHERE id = ?",
                (task.text, int(task.completed), task.id),
            )

    def delete(self, task_id: str) -> None:
        """Borra una tarea por id."""
        with self._connect() as conn:
            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def count(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
