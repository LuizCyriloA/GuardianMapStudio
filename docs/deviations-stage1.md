# Stage 1 — Deviations from Blueprint v3

Desvios mínimos aplicados para conformidade com as ferramentas reais (mypy 1.13, ruff 0.8.6, Python 3.12).
Nenhum desvio altera lógica de negócio, contratos de domínio ou comportamento em runtime.

---

## 1. `pyproject.toml` — mypy override: `ignore_missing_stubs` → `ignore_missing_imports`

**Blueprint:**
```toml
[[tool.mypy.overrides]]
module = ["shapely.*", "pyproj.*"]
ignore_missing_stubs = true
```

**Aplicado:**
```toml
[[tool.mypy.overrides]]
module = ["shapely.*", "pyproj.*"]
ignore_missing_imports = true
```

**Motivo:** `ignore_missing_stubs` não é uma opção válida do mypy 1.13.0 — causa `Unrecognized option` e aborta a checagem. A opção correta para suprimir erros de stubs ausentes em pacotes de terceiros é `ignore_missing_imports`.

---

## 2. `pyproject.toml` — ruff per-file-ignores: adição de `S108`

**Blueprint:**
```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "S105", "S106"]
```

**Aplicado:**
```toml
[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "S105", "S106", "S108"]
"tests/conftest.py" = ["S101", "S105", "S106", "S108"]
```

**Motivo:** O `conftest.py` do Blueprint usa `/tmp/gms_test_exports` como `export_dir`. O ruff 0.8.6 aciona `S108` (uso inseguro de diretório temporário) nessa string. A regra `tests/**` não cobre arquivos diretamente em `tests/` no glob do ruff, por isso foi necessária a linha extra para `tests/conftest.py`. Sem esse ajuste, `ruff check` falha com exit code 1.

---

## 3. `domain/contracts.py` — `dict` → `dict[str, Any]` em `Waypoint.extra_data`

**Blueprint:**
```python
extra_data: dict               # TREAT AS READ-ONLY
```

**Aplicado:**
```python
from typing import Any
...
extra_data: dict[str, Any]     # TREAT AS READ-ONLY
```

**Motivo:** O mypy 1.13.0 em modo `strict = true` exige parâmetros de tipo para `dict` (erro `[type-arg]`). `dict[str, Any]` é o tipo correto para um campo JSON arbitrário e não altera o comportamento em runtime.

---

## 4. `domain/events.py` — `timezone.utc` → `datetime.UTC`

**Blueprint:**
```python
from datetime import datetime, timezone
timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

**Aplicado:**
```python
import datetime as dt
timestamp: dt.datetime = field(default_factory=lambda: dt.datetime.now(dt.UTC))
```

**Motivo:** O ruff 0.8.6 aciona `UP017` (use `datetime.UTC` alias), disponível desde Python 3.11. Como o projeto requer Python ≥ 3.12, `datetime.UTC` é seguro. O comportamento em runtime é idêntico.

---

## 5. `main.py` — `from typing import AsyncGenerator` → `from collections.abc import AsyncGenerator`

**Blueprint:**
```python
from typing import AsyncGenerator
```

**Aplicado:**
```python
from collections.abc import AsyncGenerator
```

**Motivo:** O ruff 0.8.6 aciona `UP035` (importar de `collections.abc` em vez de `typing` para Python ≥ 3.9). O tipo é idêntico em runtime.

---

## Resumo

| # | Arquivo | Tipo de desvio | Impacto |
|---|---------|----------------|---------|
| 1 | `pyproject.toml` | Opção mypy inválida corrigida | Nenhum |
| 2 | `pyproject.toml` | Regra ruff adicionada ao ignore de testes | Nenhum |
| 3 | `domain/contracts.py` | Tipo genérico explicitado | Nenhum |
| 4 | `domain/events.py` | Alias moderno de UTC | Nenhum |
| 5 | `main.py` | Import movido para `collections.abc` | Nenhum |
