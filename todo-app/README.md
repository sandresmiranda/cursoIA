# ToDo

App de tareas en Python + Streamlit. Agregar, completar y filtrar.

Las tareas se guardan en **`tasks.db`**, un archivo SQLite en esta carpeta. Sobreviven a
cerrar el navegador, reiniciar el servidor y apagar la máquina. Para borrarlas
todas: `rm tasks.db`.

`st.session_state` sigue siendo la copia de trabajo del render, cargada desde la
base al abrir la sesión de navegador.

## Correrla

```bash
cd todo-app
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/streamlit run app.py
```

Se abre en <http://localhost:8501>.

## Tests

```bash
.venv/bin/python -m pytest
```

61 tests, ~0.3s. **No necesitan Streamlit instalado**: es la prueba de que la
separación entre capas es real. Lo verificás así:

```bash
.venv/bin/python -m pytest   # 61 passed
```

## Estructura

```
todo-app/
├── app.py              # UI. Único archivo que importa streamlit.
├── storage.py          # SQLite. Solo I/O, sin reglas de dominio.
├── tasks.py            # Lógica pura. Solo stdlib.
└── tests/
    ├── test_tasks.py   # reglas
    └── test_storage.py # persistencia, con base temporal
```

```
app.py  ->  storage.py  ->  tasks.py
  UI         I/O          reglas puras
```

La separación no es decorativa. Ni `tasks.py` ni `storage.py` importan Streamlit,
así que los 61 tests corren sin navegador, sin servidor y sin la dependencia
pesada instalada. `storage.py` tampoco importa nada de dominio: las reglas viven
una sola vez, en `tasks.py`.

## API de `tasks.py`

```python
add_task(tasks, text) -> list[Task]      # lanza EmptyTaskError si está vacío
toggle_task(tasks, task_id) -> list[Task] # lanza TaskNotFoundError si no existe
filter_tasks(tasks, criteria) -> list[Task]
delete_task(tasks, task_id) -> list[Task]
edit_task(tasks, task_id, text) -> list[Task]
```

Tres decisiones que explican el resto:

- **Ninguna función muta lo que recibe.** Devuelven listas nuevas. Por eso la UI
  puede asignar el resultado a `st.session_state` sin Effects alias.
- **`Task` es `frozen=True`.** Si una función devolviera la instancia mutada, el
  estado viejo de la UI apuntaría al objeto nuevo y el cambio no se vería.
- **Los errores son excepciones de dominio**, no tuplas `(valor, error)`. La UI
  las captura con `try/except`; los tests usan `pytest.raises`.

`filter_tasks` con un filtro desconocido lanza `ValueError` en vez de devolver
todo: un typo que devuelve todo en silencio rompe la vista sin ningún síntoma.

## Decisiones de UI

- El campo de texto **se limpia** al agregar una tarea válida, pero **se conserva**
  si el texto era inválido — si no, el usuario pierde lo que acaba de escribir.
- El checkbox se dibuja desde el estado y el estado solo cambia vía
  `toggle_task`. Si divergen, es porque el usuario recién hizo clic.
- **Editar conserva el estado de completada.** Corregir un typo no debería
  des-completar la tarea.
- La base se escribe en cada acción (agregar, completar, editar, borrar), no en
  un autosave. Es lo más simple de razonar; el costo es que dos pestañas
  abiertas al mismo tiempo pueden pisarse. Para el uso de una persona no
  molesta. Si necesitaras multiusuario, habría que releer la base en cada
  rerun en vez de confiar en `session_state`.
- Cada tarea se filtra por id, no por índice: con un filtro activo, el índice de
  la lista visible no corresponde al de la lista real.

## Fuera de alcance

Login, API de IA, reordenar tareas, fechas y prioridades. Este proyecto es
deliberadamente chico.
