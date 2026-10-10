"""Tests de la lógica de tareas.

Ninguno de estos tests importa Streamlit. Es el criterio de aceptación 18 y la
prueba de que la separación entre capas es real y no nominal.
"""

import pytest

from tasks import (
    EmptyTaskError,
    Filter,
    Task,
    TaskError,
    TaskNotFoundError,
    add_task,
    filter_tasks,
    toggle_task,
)


@pytest.fixture
def tareas() -> list[Task]:
    """Tres tareas: dos pendientes y una completada."""
    lista = add_task([], "comprar pan")
    lista = add_task(lista, "llamar al dentista")
    lista = add_task(lista, "enviar el reporte")
    return toggle_task(lista, lista[2].id)


# ----- Agregar: criterios 1 a 7 -----


class TestAddTask:
    def test_agrega_una_tarea_pendiente(self):
        # Criterio 1
        resultado = add_task([], "comprar pan")
        assert len(resultado) == 1
        assert resultado[0].text == "comprar pan"
        assert resultado[0].completed is False

    def test_normaliza_el_texto(self):
        # Criterio 2
        resultado = add_task([], "   comprar pan   ")
        assert resultado[0].text == "comprar pan"

    def test_agrega_al_final_de_la_lista(self):
        # Criterio 3
        base = add_task([], "primera")
        resultado = add_task(base, "segunda")
        assert [t.text for t in resultado] == ["primera", "segunda"]

    @pytest.mark.parametrize(
        "texto",
        [
            "",
            "   ",
            "\t",
            "\n",
            " \t \n ",
        ],
        ids=["vacio", "espacios", "tab", "newline", "mixto"],
    )
    def test_rechaza_texto_vacio_o_solo_espacios(self, texto):
        # Criterios 4 y 5
        with pytest.raises(EmptyTaskError):
            add_task([], texto)

    def test_rechazo_no_agrega_nada(self):
        # El error no debe dejar la lista a medio camino.
        base = add_task([], "tarea real")
        with pytest.raises(EmptyTaskError):
            add_task(base, "   ")
        assert len(base) == 1

    def test_los_ids_son_unicos(self):
        # Criterio 6
        resultado = [add_task([], f"tarea {i}") for i in range(25)]
        ids = [t.id for lista in resultado for t in lista]
        assert len(ids) == len(set(ids))

    def test_no_muta_la_lista_original(self):
        # Criterio 7
        base = add_task([], "primera")
        copia = list(base)
        resultado = add_task(base, "segunda")
        assert base == copia
        assert resultado is not base

    def test_rechaza_texto_que_no_es_cadena(self):
        with pytest.raises(EmptyTaskError):
            add_task([], None)


# ----- Completar / alternar: criterios 8 a 12 -----


class TestToggleTask:
    def test_marca_como_completada(self, tareas):
        # Criterio 8
        resultado = toggle_task(tareas, tareas[0].id)
        assert resultado[0].completed is True

    def test_revierte_a_pendiente(self, tareas):
        # Criterio 9
        completada = toggle_task(tareas, tareas[0].id)
        revertida = toggle_task(completada, tareas[0].id)
        assert revertida[0].completed is False

    def test_alternar_dos_veces_conserva_el_estado(self, tareas):
        # Criterio 10
        original = tareas[0].completed
        ida_y_vuelta = toggle_task(toggle_task(tareas, tareas[0].id), tareas[0].id)
        assert ida_y_vuelta[0].completed == original

    def test_id_inexistente_lanza_error(self):
        # Criterio 11
        base = add_task([], "comprar pan")
        with pytest.raises(TaskNotFoundError):
            toggle_task(base, "no-existe")

    def test_id_inexistente_no_corrompe_la_lista(self):
        # Criterio 11
        base = add_task([], "comprar pan")
        copia = list(base)
        with pytest.raises(TaskNotFoundError):
            toggle_task(base, "no-existe")
        assert base == copia

    def test_no_altera_texto_ni_id(self, tareas):
        # Criterio 12
        resultado = toggle_task(tareas, tareas[0].id)
        assert resultado[0].text == tareas[0].text
        assert resultado[0].id == tareas[0].id

    def test_solo_cambia_la_tarea_apuntada(self, tareas):
        resultado = toggle_task(tareas, tareas[0].id)
        assert resultado[1].completed == tareas[1].completed
        assert resultado[2].completed == tareas[2].completed

    def test_no_muta_la_lista_original(self, tareas):
        copia = list(tareas)
        toggle_task(tareas, tareas[0].id)
        assert tareas == copia


# ----- Filtrar: criterios 13 a 17 -----


class TestFilterTasks:
    def test_todas_devuelve_todo(self, tareas):
        # Criterio 13
        assert len(filter_tasks(tareas, Filter.ALL)) == 3

    def test_todas_conserva_el_orden(self, tareas):
        # Criterio 13
        assert [t.id for t in filter_tasks(tareas, Filter.ALL)] == [t.id for t in tareas]

    def test_pendientes(self, tareas):
        # Criterio 14
        resultado = filter_tasks(tareas, Filter.PENDING)
        assert len(resultado) == 2
        assert all(not t.completed for t in resultado)

    def test_completadas(self, tareas):
        # Criterio 15
        resultado = filter_tasks(tareas, Filter.COMPLETED)
        assert len(resultado) == 1
        assert all(t.completed for t in resultado)

    def test_filtrar_lista_vacia(self):
        # Criterio 16
        for criterio in Filter:
            assert filter_tasks([], criterio) == []

    def test_los_filtros_son_excluyentes(self, tareas):
        # Criterio 17
        pendientes = filter_tasks(tareas, Filter.PENDING)
        completadas = filter_tasks(tareas, Filter.COMPLETED)
        assert len(pendientes) + len(completadas) == len(tareas)
        assert not ({t.id for t in pendientes} & {t.id for t in completadas})

    def test_no_muta_la_lista_original(self, tareas):
        copia = list(tareas)
        filter_tasks(tareas, Filter.PENDING)
        assert tareas == copia

    def test_filtro_desconocido_falla(self):
        # Un typo debe ser ruidoso, no devolver todo en silencio.
        with pytest.raises(ValueError):
            filter_tasks([], "pendientess")



# ----- Editar: funcionalidad nueva -----

from tasks import (  # noqa: E402  (import tardío a propósito, se agrega al final)
    MAX_LENGTH,
    TaskTooLongError,
    delete_task,
    edit_task,
)


class TestEditTask:
    def test_reemplaza_el_texto(self, tareas):
        resultado = edit_task(tareas, tareas[0].id, "otro texto")
        assert resultado[0].text == "otro texto"

    def test_normaliza_el_texto(self, tareas):
        resultado = edit_task(tareas, tareas[0].id, "  otro texto  ")
        assert resultado[0].text == "otro texto"

    def test_conserva_id_y_estado(self, tareas):
        # Editar no debe des-completar la tarea ni cambiar su identidad.
        completada = toggle_task(tareas, tareas[0].id)
        resultado = edit_task(completada, tareas[0].id, "nuevo")
        assert resultado[0].id == tareas[0].id
        assert resultado[0].completed is True

    def test_no_toca_las_demas(self, tareas):
        resultado = edit_task(tareas, tareas[0].id, "nuevo")
        assert resultado[1] == tareas[1]

    def test_rechaza_texto_vacio(self, tareas):
        with pytest.raises(EmptyTaskError):
            edit_task(tareas, tareas[0].id, "   ")

    def test_rechaza_texto_largo(self, tareas):
        with pytest.raises(TaskTooLongError):
            edit_task(tareas, tareas[0].id, "x" * (MAX_LENGTH + 1))

    def test_id_inexistente(self, tareas):
        with pytest.raises(TaskNotFoundError):
            edit_task(tareas, "no-existe", "texto")

    def test_no_muta_la_original(self, tareas):
        copia = list(tareas)
        edit_task(tareas, tareas[0].id, "nuevo")
        assert tareas == copia


# ----- Borrar: funcionalidad nueva -----

class TestDeleteTask:
    def test_borra_la_tarea(self, tareas):
        resultado = delete_task(tareas, tareas[0].id)
        assert len(resultado) == 2
        assert tareas[0].id not in {t.id for t in resultado}

    def test_conserva_el_orden_del_resto(self, tareas):
        resultado = delete_task(tareas, tareas[0].id)
        assert [t.id for t in resultado] == [t.id for t in tareas[1:]]

    def test_borrar_la_ultima(self, tareas):
        resultado = delete_task(tareas, tareas[-1].id)
        assert len(resultado) == 2

    def test_lista_vacia(self, tareas):
        for tarea in tareas:
            tareas = delete_task(tareas, tarea.id)
        assert tareas == []

    def test_id_inexistente(self, tareas):
        with pytest.raises(TaskNotFoundError):
            delete_task(tareas, "no-existe")

    def test_id_repetido_falla(self, tareas):
        # No se puede "borrar dos veces" la misma: la segunda debe ser ruidosa.
        resultado = delete_task(tareas, tareas[0].id)
        with pytest.raises(TaskNotFoundError):
            delete_task(resultado, tareas[0].id)

    def test_no_muta_la_original(self, tareas):
        copia = list(tareas)
        delete_task(tareas, tareas[0].id)
        assert tareas == copia


# ----- Límite de longitud -----

class TestMaxLength:
    def test_acepta_el_limite_exacto(self):
        assert add_task([], "x" * MAX_LENGTH)[0].text == "x" * MAX_LENGTH

    def test_rechaza_un_caracter_de_mas(self):
        with pytest.raises(TaskTooLongError):
            add_task([], "x" * (MAX_LENGTH + 1))

    def test_el_limite_mide_el_texto_normalizado(self):
        # 500 de texto + espacios no puede rechazar: el usuario no ve los
        # espacios como parte de lo que escribió.
        assert add_task([], "  " + "x" * MAX_LENGTH + "  ")

    def test_error_de_longitud_es_del_dominio(self):
        # Los tres errores cuelgan de TaskError, así que la UI puede atrapar
        # uno solo y no importa cuál sea.
        assert issubclass(TaskTooLongError, TaskError)
        assert issubclass(EmptyTaskError, TaskError)
        assert issubclass(TaskNotFoundError, TaskError)
