"""Interfaz Streamlit del ToDo.

Tres capas, en este orden de dependencia:

    app.py  ->  storage.py  ->  tasks.py
      UI        I/O          reglas puras

app.py orquesta y no decide nada: pide una decisión a tasks.py (¿es válido este
texto?) y, si es positiva, la escribe en storage. Las reglas viven una sola vez.

PERSISTENCIA: las tareas viven en tasks.db (SQLite). st.session_state sigue
siendo la copia de trabajo del render, cargada desde la base al abrir la sesión.
"""

from __future__ import annotations

import streamlit as st

from storage import TaskStore
from tasks import (
    Filter,
    Task,
    TaskError,
    TaskNotFoundError,
    add_task,
    delete_task,
    edit_task,
    filter_tasks,
    toggle_task,
)

st.set_page_config(page_title="ToDo", page_icon="📝", layout="centered")

ETIQUETAS = {
    Filter.ALL: "Todas",
    Filter.PENDING: "Pendientes",
    Filter.COMPLETED: "Completadas",
}


def _store() -> TaskStore:
    return TaskStore()


def _iniciar_estado() -> None:
    """Carga la base una sola vez por sesión de navegador.

    El chequeo es necesario porque Streamlit re-ejecuta el script entero en cada
    interacción: sin esto, cada clic volvería a leer el archivo y pisaría los
    cambios que todavía no se guardaron.
    """
    if "tasks" not in st.session_state:
        st.session_state.tasks = _store().load()
    if "input_version" not in st.session_state:
        st.session_state.input_version = 0
    if "editando" not in st.session_state:
        st.session_state.editando = None


def _seccion_agregar() -> None:
    st.subheader("Agregar tarea")

    # El form evita un rerun por cada tecla. Cambiar el key del text_input es lo
    # que limpia el campo: con la misma key Streamlit recuerda el valor.
    with st.form("agregar", clear_on_submit=False):
        texto = st.text_input(
            "Nueva tarea",
            placeholder="¿Qué hay que hacer?",
            label_visibility="collapsed",
            key=f"nueva_tarea_{st.session_state.input_version}",
        )
        enviado = st.form_submit_button("Agregar", type="primary")

    if not enviado:
        return

    try:
        nuevas = add_task(st.session_state.tasks, texto)
    except TaskError as error:
        # No se incrementa input_version: si el texto era inválido, el usuario
        # lo tiene que ver en la caja para poder corregirlo.
        st.error(str(error))
        return

    _store().insert(nuevas[-1])
    st.session_state.tasks = nuevas
    st.session_state.input_version += 1
    st.rerun()


def _seccion_filtro() -> Filter:
    return st.radio(
        "Filtrar",
        options=list(Filter),
        format_func=lambda criterio: ETIQUETAS[criterio],
        horizontal=True,
    )


def _fila(tarea: Task) -> None:
    """Una tarea: completar, editar y borrar."""
    editando = st.session_state.editando == tarea.id

    if editando:
        with st.form(f"editar_{tarea.id}"):
            nuevo = st.text_input("Texto", value=tarea.text, label_visibility="collapsed")
            guardar, cancelar = st.columns(2)
            with guardar:
                ok = st.form_submit_button("Guardar", type="primary")
            with cancelar:
                fuera = st.form_submit_button("Cancelar")

        if fuera:
            st.session_state.editando = None
            st.rerun()
        if ok:
            try:
                st.session_state.tasks = edit_task(st.session_state.tasks, tarea.id, nuevo)
            except TaskError as error:
                st.error(str(error))
                return
            _store().update(next(t for t in st.session_state.tasks if t.id == tarea.id))
            st.session_state.editando = None
            st.rerun()
        return

    col_texto, col_editar, col_borrar = st.columns([0.7, 0.15, 0.15])

    with col_texto:
        marcado = st.checkbox(tarea.text, value=tarea.completed, key=f"tarea_{tarea.id}")
        if marcado != tarea.completed:
            try:
                st.session_state.tasks = toggle_task(st.session_state.tasks, tarea.id)
            except TaskNotFoundError:
                # No debería pasar: la lista que se dibuja ES session_state.
                # Si pasa, es que el estado se desfasó, y tragarse el error
                # escondería la causa real detrás de un "el clic no hizo nada".
                st.warning("No se encontró la tarea. Recargá la página.")
                return
            _store().update(next(t for t in st.session_state.tasks if t.id == tarea.id))
            st.rerun()

    with col_editar:
        if st.button("✏️", key=f"editar_{tarea.id}", help="Editar"):
            st.session_state.editando = tarea.id
            st.rerun()

    with col_borrar:
        if st.button("🗑️", key=f"borrar_{tarea.id}", help="Borrar"):
            try:
                st.session_state.tasks = delete_task(st.session_state.tasks, tarea.id)
            except TaskNotFoundError:
                st.warning("No se encontró la tarea. Recargá la página.")
                return
            _store().delete(tarea.id)
            st.rerun()


def _seccion_lista(criterio: Filter) -> None:
    visibles = filter_tasks(st.session_state.tasks, criterio)

    if not visibles:
        st.info("No hay tareas para mostrar.")
        return

    for tarea in visibles:
        _fila(tarea)


def main() -> None:
    _iniciar_estado()

    st.title("📝 ToDo")
    st.caption("Las tareas se guardan en tasks.db y sobreviven a cerrar el navegador.")

    _seccion_agregar()
    st.divider()

    criterio = _seccion_filtro()
    _seccion_lista(criterio)


main()
