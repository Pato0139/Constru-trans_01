from __future__ import annotations

import os
import re
from pathlib import Path

import django
import pytest
from django.urls import NoReverseMatch, reverse


_RAIZ = Path(__file__).resolve().parents[2]
_EXCLUIR = {".venv", "venv", "node_modules", ".git", "staticfiles", "media"}


def _extraer_urls_template(texto: str) -> list[str]:
    refs = []
    for m in re.finditer(r"{%\s*url\s+['\"]([^'\"]+?)['\"][^%]*%}", texto):
        ref = m.group(1).strip()
        if ":" in ref:
            refs.append(ref)
    return refs


def _extraer_urls_python(texto: str) -> list[str]:
    pat = re.compile(r"(reverse|redirect|reverse_lazy)\s*\(\s*['\"]([^'\"]*:[^'\"]*)['\"]")
    pat_sl = re.compile(r"success_url\s*=\s*reverse_lazy\s*\(\s*['\"]([^'\"]*:[^'\"]*)['\"]")
    return [m.group(2) for m in pat.finditer(texto)] + [m.group(1) for m in pat_sl.finditer(texto)]


def _intentar_resolver(ref: str):
    kwargs_comunes = [
        {}, {"id": 1}, {"pk": 1}, {"conductor_id": 1}, {"entrega_id": 1}, {"novedad_id": 1},
        {"seguimiento_id": 1}, {"orden_id": 1}, {"uidb64": "MQ", "token": "abc-def-123"},
        {"tipo": "clientes"}, {"codigo_proveedor": 1}, {"rol": "cliente"}, {"categoria_id": 1},
        {"guia_id": 1},
    ]
    args_list = [[], [1], [1, 1], [1, 1, 1], [1, "A", "B"]]

    ultimo_error: Exception | None = None
    for kwargs in kwargs_comunes:
        try:
            return reverse(ref, kwargs=kwargs)
        except (NoReverseMatch, TypeError) as exc:
            ultimo_error = exc
            pass
    for args in args_list:
        try:
            return reverse(ref, args=args)
        except (NoReverseMatch, TypeError) as exc:
            ultimo_error = exc
            pass
    raise ultimo_error or NoReverseMatch(ref)


def _recolectar(ext: str, fn_extract):
    referencias: dict[str, list[str]] = {}
    for root, dirs, files in os.walk(_RAIZ):
        dirs[:] = [d for d in dirs if d not in _EXCLUIR]
        for name in files:
            if not name.endswith(ext):
                continue
            ruta = Path(root) / name
            try:
                texto = ruta.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            refs = fn_extract(texto)
            if refs:
                referencias[str(ruta)] = refs
    return referencias


@pytest.mark.django_db(databases=["default", "remota"])
class TestUrlsRegistradas:
    def setup_method(self):
        django.setup()

    def test_todos_los_url_tag_en_templates_resuelven(self):
        casos = _recolectar(".html", _extraer_urls_template)
        errores: list[str] = []
        for ruta, refs in casos.items():
            for ref in refs:
                try:
                    _intentar_resolver(ref)
                except Exception as exc:
                    errores.append(f"[{ruta}] '{ref}' :: {exc}".replace(str(_RAIZ), ""))
        assert not errores, (
            f"Se encontraron {len(errores)} referencias de URL no resolubles en templates:\n  - "
            + "\n  - ".join(errores)
        )

    def test_todos_los_reverse_redirect_en_python_resuelven(self):
        casos = _recolectar(".py", _extraer_urls_python)
        errores: list[str] = []
        for ruta, refs in casos.items():
            if any(d in ruta for d in _EXCLUIR):
                continue
            for ref in refs:
                try:
                    _intentar_resolver(ref)
                except Exception as exc:
                    errores.append(f"[{ruta}] '{ref}' :: {exc}".replace(str(_RAIZ), ""))
        assert not errores, (
            f"Se encontraron {len(errores)} referencias de URL no resolubles en código Python:\n  - "
            + "\n  - ".join(errores)
        )

    def test_vistas_urls_mapeadas_existen(self):
        apps_urls = [
            "usuarios.urls", "clientes.urls", "catalogo.urls", "compras.urls",
            "pedidos.urls", "logistica.urls", "auditoria.urls", "reportes.urls",
            "inicio.urls", "licensing.urls", "ayuda.urls", "ia.urls",
        ]
        faltantes: list[str] = []
        from django.urls.resolvers import URLPattern
        from inspect import isclass

        for url_mod in apps_urls:
            mod = __import__(url_mod, fromlist=["urlpatterns"])
            app_label = url_mod.split(".")[0]
            try:
                views_mod = __import__(f"{app_label}.views", fromlist=["*"])
            except Exception as exc:
                faltantes.append(f"No se pudo cargar views de {app_label}: {exc}")
                continue
            for p in getattr(mod, "urlpatterns", []):
                if not isinstance(p, URLPattern):
                    continue
                cb = p.callback
                name = p.name or "<sin nombre>"
                if hasattr(cb, "view_class"):
                    cls = cb.view_class
                    if "auth" in cls.__module__:
                        continue
                    if not hasattr(views_mod, cls.__name__):
                        faltantes.append(f"{app_label}:{name} falta view_class {cls.__name__} en views")
                else:
                    n = getattr(cb, "__name__", None)
                    if not n or n == "<lambda>":
                        continue
                    if not hasattr(views_mod, n):
                        faltantes.append(f"{app_label}:{name} falta funcion {n} en views")
        assert not faltantes, (
            "Faltan referencias de vistas en sus módulos views:\n  - "
            + "\n  - ".join(faltantes)
        )
