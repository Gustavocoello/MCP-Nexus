# Guía Completa de Sincronización de Bases de Datos

## Estructura de archivos

```
src/database/
├── config/
|---test/
│       └── test_orchestrator.py     # Test de fallback
├── utils/
│   ├── create_tables.py             # PASO 1: Crear tablas
│   ├── database_sync.py             # PASO 2: Sync manual
│   └── auto_sync.py                 # PASO 3: Sync automático
└── models/
    └── models.py                    # Definicion de tablas
```

---

## Flujo Completo de Configuración

### PASO 1: Crear tablas en todas las bases de datos

Las tablas deben existir ANTES de sincronizar datos.

```bash
cd src/database/utils

# Crear en todas las BD disponibles
python create_tables.py --all

# O crear una por una
python create_tables.py --database windows
python create_tables.py --database linux
python create_tables.py --database azure
```

### PASO 2: Verificar que las tablas se crearon

```bash
python create_tables.py --check
```

Deberías ver algo como:
```
WINDOWS:
  Estado: DISPONIBLE
  Tablas existentes (5):
    [✓] users: OK
    [✓] chats: OK
    [✓] messages: OK
    [✓] documents: OK
    [✓] user_memory: OK
```

### PASO 3: Sincronizar datos

#### Opción A: Manual interactivo
```bash
python database_sync.py
```
Selecciona opción del menú.

#### Opción B: Automático desde Windows
```bash
python auto_sync.py --source windows
```

---

## Comandos Principales

### create_tables.py - Crear estructura

| Comando | Descripción |
|---------|-------------|
| `--all` | Crear tablas en todas las BD disponibles |
| `--database windows` | Crear solo en Windows |
| `--database linux` | Crear solo en Linux |
| `--database azure` | Crear solo en Azure |
| `--check` | Ver estado sin crear nada |
| `--all --drop` | CUIDADO: Recrear todo (borra datos) |

### database_sync.py - Sincronización manual

| Opción | Acción |
|--------|--------|
| 1 | Sincronizar Windows → Todas |
| 2 | Sincronizar Linux → Todas |
| 3 | Sincronizar específica (elegir origen/destino) |
| 4 | Solo ver estado |

### auto_sync.py - Sincronización automática

| Comando | Descripción |
|---------|-------------|
| `python auto_sync.py` | Sync automático desde Windows |
| `--source linux` | Sync desde Linux |
| `--history` | Ver historial de syncs |
| `--status` | Ver estado actual |

---

## Diferencias Importantes

### Sincronización vs Creación de Tablas

| Aspecto | create_tables.py | database_sync.py / auto_sync.py |
|---------|------------------|----------------------------------|
| **Qué hace** | Crea estructura (tablas, columnas) | Copia datos entre tablas |
| **Cuándo usar** | Primera vez o cambios en models.py | Regularmente para backup |
| **Requisito** | - | Las tablas deben existir |
| **Borra datos** | Solo con --drop | Sí, en destino |

### Importante:
1. **create_tables.py** → Crea la estructura (tablas vacías)
2. **Sync scripts** → Copian los datos entre tablas existentes

---

## Programar Sincronización Automática

### Linux/Mac (crontab)

```bash
# Editar crontab
crontab -e

# Agregar una de estas líneas:

# Cada 6 horas
0 */6 * * * cd /home/user/proyecto && python src/database/utils/auto_sync.py

# Cada día a las 2 AM
0 2 * * * cd /home/user/proyecto && python src/database/utils/auto_sync.py

# Con logs
0 */6 * * * cd /home/user/proyecto && python src/database/utils/auto_sync.py >> /var/log/db_sync.log 2>&1
```

### Windows (Task Scheduler)

**Opción 1: Línea de comandos (PowerShell como admin)**
```powershell
schtasks /create /tn "DB Sync" /tr "python C:\ruta\proyecto\src\database\utils\auto_sync.py" /sc daily /st 02:00
```

**Opción 2: Interfaz gráfica**
1. Abrir "Programador de tareas"
2. Crear tarea básica
3. Nombre: "DB Sync"
4. Desencadenador: Diario/Por horas
5. Acción: Iniciar programa
   - Programa: `python`
   - Argumentos: `C:\ruta\auto_sync.py`
   - Iniciar en: `C:\ruta\src\database\utils`

---

## Integración con Flask/FastAPI

### Endpoints recomendados

```python
# app.py
from src.database.utils.database_sync import DatabaseSync
from src.database.utils.auto_sync import AutoSync

@app.route('/admin/db-status', methods=['GET'])
def db_status():
    """Ver estado de todas las BD"""
    sync = DatabaseSync()
    sync.connect_databases()
    
    status = {}
    for db in ['windows', 'linux', 'azure']:
        if db in sync.available_databases:
            status[db] = {
                'available': True,
                'size_mb': sync.get_database_size(db),
                'tables': sync.get_tables_info(db)
            }
        else:
            status[db] = {'available': False}
    
    return jsonify(status)

@app.route('/admin/sync', methods=['POST'])
def trigger_sync():
    """Disparar sincronización manual"""
    data = request.json
    source = data.get('source', 'windows')
    
    auto_sync = AutoSync()
    success = auto_sync.run_sync(source=source)
    
    return jsonify({'success': success})

@app.route('/admin/sync-history', methods=['GET'])
def sync_history():
    """Ver historial de sincronizaciones"""
    auto_sync = AutoSync()
    history = auto_sync.load_history()
    
    return jsonify({
        'history': history[-10:],
        'total': len(history)
    })
```

---

## Casos de Uso Comunes

### 1. Primera configuración completa

```bash
# Paso 1: Crear tablas en todas las BD
python create_tables.py --all

# Paso 2: Verificar
python create_tables.py --check

# Paso 3: Si Windows tiene datos, sincronizar
python auto_sync.py --source windows

# Paso 4: Verificar resultado
python auto_sync.py --status
```

### 2. Actualizar estructura (cambios en models.py)

```bash
# Opción A: Usar Alembic (recomendado)
alembic revision --autogenerate -m "descripcion"
alembic upgrade head

# Opción B: Recrear tablas (BORRA TODO)
python create_tables.py --all --drop
```

### 3. Backup manual antes de cambios importantes

```bash
# Ver estado actual
python auto_sync.py --status

# Sincronizar todo a Azure como backup
python auto_sync.py --source windows
```

### 4. Recuperar desde backup

```bash
# Si Windows se cae, sincronizar desde Linux
python auto_sync.py --source linux

# O desde Azure
python auto_sync.py --source azure
```

### 5. Monitorear sincronizaciones

```bash
# Ver últimas 10 sincronizaciones
python auto_sync.py --history

# Ver estado actual
python auto_sync.py --status
```

---

## Solución de Problemas

### Error: "Table doesn't exist"
**Causa**: Intentaste sincronizar sin crear tablas primero  
**Solución**: Ejecuta `python create_tables.py --all`

### Error: "No databases available"
**Causa**: Ninguna BD pudo conectarse  
**Solución**: Verifica credenciales en `.env` y conexiones de red

### Sincronización muy lenta
**Causa**: Muchos datos o conexión lenta  
**Solución**: Sincroniza solo tablas específicas o aumenta timeout

### Datos no se sincronizan
**Causa**: Las tablas tienen estructuras diferentes  
**Solución**: Verifica que `models.py` sea el mismo y crea tablas con `create_tables.py`

---

## Checklist de Mantenimiento

### Diario
- [ ] Verificar que sync automático se ejecutó: `python auto_sync.py --history`

### Semanal
- [ ] Revisar estado de todas las BD: `python auto_sync.py --status`
- [ ] Verificar tamaños: `python create_tables.py --check`

### Mensual
- [ ] Backup completo manual: `python auto_sync.py --source windows`
- [ ] Revisar logs de sincronización

### Al hacer cambios en models.py
- [ ] Crear/actualizar tablas: `python create_tables.py --all`
- [ ] Verificar estructura: `python create_tables.py --check`
- [ ] Sincronizar datos: `python auto_sync.py`

---

## Notas Finales

- La sincronización **BORRA** datos del destino y los reemplaza
- Siempre verifica con `--status` antes de sincronizar
- El historial se guarda en `sync_history.json`
- Las tablas deben existir en origen Y destino
- Solo se sincronizan datos, no estructura

Para soporte adicional, revisa los comentarios en cada script.