# Análisis Técnico: [ISSUE-SDK-CLI-01] Documentación Explícita de Comandos Arbitrarios en jg dev

## 1. Diagnóstico del Estado Previo
En `jg_sdk/cli.py:1446-1454`:
```python
dev_parser = subparsers.add_parser(
    "dev",
    help="Habilita el entorno virtual (.venv) o ejecuta comandos dentro de él.",
)
dev_parser.add_argument(
    "command",
    nargs=argparse.REMAINDER,
    help="Comando opcional a ejecutar dentro de .venv (ej. 'pytest', 'ruff check .').",
)
```

Y en `handle_dev`:
```python
if command:
    cmd = list(command)
    bin_candidate = venv_dir / "bin" / cmd[0]
    if bin_candidate.exists():
        cmd[0] = str(bin_candidate)
    res = subprocess.run(cmd, env=new_env, cwd=plugin_root)
    return res.returncode
```

### Observaciones
- La entrada del usuario `command` se ejecuta directamente sin validación semántica ni lista blanca de comandos.
- Aunque el comportamiento es deseable para desarrollo local en Python (permite lanzar cualquier utilidad como `pytest`, `ruff`, `mypy`, `pip`, etc.), la ayuda del CLI no explicitaba esta naturaleza arbitraria.

## 2. Alternativas Evaluadas
- **Alternativa A (Implementar Whitelist de comandos permitidos):**
  - *Desventaja:* Altamente restrictiva. Impediría al desarrollador usar herramientas legítimas como `coverage`, `black`, `isort`, `bandit` o scripts internos sin actualizar el SDK.
- **Alternativa B (Documentación Explícita y Ejemplos Claros - Seleccionada):**
  - *Ventajas:* Mantiene la flexibilidad total requerida por un entorno de desarrollo moderno mientras aclara inequívocamente al usuario el comportamiento del comando.

## 3. Plan de Mitigación
1. Configurar `description` y `formatter_class=argparse.RawDescriptionHelpFormatter` en `dev_parser`.
2. Actualizar el docstring de `handle_dev`.
3. Añadir test unitario en `tests/test_cli.py`.
4. Verificar con Ruff y Pytest.
