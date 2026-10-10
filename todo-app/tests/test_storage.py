"""Tests de la capa de persistencia.

Cada test usa su propio archivo SQLite temporal, así que corren en paralelo,
no se pisan entre sí y dejan cero residuos. Sin Streamlit y sin la UI.
"""

import sqlite3

import pytest

from storage import TaskStore
from tasks import Task, add_task, edit_task, toggle_task


@pytest.fixture
def store(tmp_path) -> TaskStore:
    return TaskStore(tmp_path / "test.db")


@pytest.fixture
def dos_tareas() -> list[Task]:
    lista = add_task([], "comprar pan")
    return add_task(lista, "llamar al dentista")


class TestCicloCompleto:
    def test_agregar_y_cargar(self, store, dos_tareas):
        for tarea in dos_tareas:
            store.insert(tarea)
        assert store.load() == dos_tareas

    def test_orden_de_insercion(self, store):
        for texto in ["primera", "segunda", "tercera"]:
            store.insert(add_task([], texto)[0])
        assert [t.text for t in store.load()] == ["primera", "segunda", "tercera"]

    def test_completar_persiste(self, store, dos_tareas):
        for tarea in dos_tareas:
            store.insert(tarea)
        actualizada = toggle_task(dos_tareas, dos_tareas[0].id)
        store.update(actualizada[0])

        recargada = store.load()
        assert recargada[0].completed is True
        assert recargada[1].completed is False

    def test_editar_persiste(self, store, dos_tareas):
        for tarea in dos_tareas:
            store.insert(tarea)
        editada = edit_task(dos_tareas, dos_tareas[0].id, "comprar pan y leche")
        store.update(editada[0])
        assert store.load()[0].text == "comprar pan y leche"

    def test_borrar_persiste(self, store, dos_tareas):
        for tarea in dos_tareas:
            store.insert(tarea)
        store.delete(dos_tareas[0].id)
        assert [t.id for t in store.load()] == [dos_tareas[1].id]

    def test_sobrevive_a_reabrir(self, store, dos_tareas, tmp_path):
        for tarea in dos_tareas:
            store.insert(tarea)
        # Store nuevo sobre el mismo archivo: es lo que pasa al recargar.
        assert TaskStore(tmp_path / "test.db").load() == dos_tareas


class TestCasosLimite:
    def test_base_vacia(self, store):
        assert store.load() == []
        assert store.count() == 0

    def test_borrar_todo(self, store, dos_tareas):
        for tarea in dos_tareas:
            store.insert(tarea)
        for tarea in dos_tareas:
            store.delete(tarea.id)
        assert store.load() == []

    def test_el_orden_no_se_rompe_al_borrar_la_ultima(self, store):
        # El motivo de existir de la columna seq: si el orden dependiera del
        # rowid de SQLite, borrar la ultima fila y agregar otra podria
        # descolocar la nueva al principio de la lista.
        a, b, c = (add_task([], t)[0] for t in "abc")
        for tarea in (a, b, c):
            store.insert(tarea)
        store.delete(c.id)          # borra la ultima
        d = add_task([], "d")[0]
        store.insert(d)

        assert [t.text for t in store.load()] == ["a", "b", "d"]

    def test_texto_con_comillas_y_unicode(self, store):
        texto = "comprar pan; DROP TABLE tasks; -- 🛒 naïve café"
        store.insert(add_task([], texto)[0])
        assert store.load()[0].text == texto
        assert store.count() == 1  # la tabla sigue existiendo

    def test_texto_largo(self, store):
        texto = "x" * 500
        store.insert(add_task([], texto)[0])
        assert store.load()[0].text == texto

    def test_update_de_id_inexistente_no_crea_nada(self, store):
        store.update(Task(id="fantasma", text="x", completed=True))
        assert store.load() == []

    def test_delete_de_id_inexistente_no_falla(self, store):
        store.delete("fantasma")  # no debe levantar
        assert store.load() == []

    def test_id_duplicado_rechazado(self, store, dos_tareas):
        store.insert(dos_tareas[0])
        # sqlite3.IntegrityError puntual, no Exception: un test que acepta
        # cualquier excepcion no verifica nada.
        with pytest.raises(sqlite3.IntegrityError):
            store.insert(dos_tareas[0])
