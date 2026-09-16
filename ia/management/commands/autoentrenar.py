"""Recolecta preguntas públicas y destila respuestas en memoria."""
import time
from django.core.management.base import BaseCommand
from ia.services import llm_service
from ia.services.memoria_destilada import _cargar_vistos, guardar_par, hash_pregunta, leer_pares
from ia.training.recolector_preguntas import recolectar

SYSTEM_MASTER = "Eres un tutor enciclopédico. Responde en español, de forma breve (2-4 frases), clara y correcta. No inventes datos."


class Command(BaseCommand):
    help = "Recolecta preguntas públicas y destila respuestas del modelo maestro"

    def add_arguments(self, parser):
        parser.add_argument("--total", type=int, default=20)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--fuentes", type=str, default="opentdb,stackexchange,wikipedia,wikipedia_dominio")
        parser.add_argument("--pausa", type=float, default=1.0)
        parser.add_argument("--reintentos", type=int, default=2)

    def handle(self, *args, **options):
        fuentes = [f.strip() for f in options["fuentes"].split(",") if f.strip()]
        vistos = _cargar_vistos()
        previos = len(leer_pares())
        total = options["total"]
        candidatos = recolectar(total * 2, fuentes=fuentes)
        self.stdout.write(f"Recolectadas {len(candidatos)} preguntas de {fuentes}.")
        nuevas = [c for c in candidatos if hash_pregunta(c["pregunta"]) not in vistos][:total]
        self.stdout.write(f"Tras deduplicación: {len(nuevas)} preguntas nuevas.")
        if not nuevas:
            self.stdout.write(self.style.WARNING("No hay preguntas nuevas que procesar."))
            return
        if options["dry_run"]:
            for candidato in nuevas:
                self.stdout.write(f"  [{candidato['fuente']}] {candidato['pregunta']}")
            self.stdout.write(self.style.SUCCESS(f"Dry-run OK: {len(nuevas)} preguntas serían procesadas."))
            return
        if llm_service.client is None:
            self.stdout.write(self.style.ERROR("Modelo maestro no configurado. Configura LLM_BASE_URL/LLM_API_KEY/LLM_MODEL."))
            return
        ok = fallos = 0
        for candidato in nuevas:
            respuesta = None
            for intento in range(max(1, options["reintentos"])):
                try:
                    referencia = candidato.get("metadata", {}).get("texto_referencia", "")
                    response = llm_service.client.chat.completions.create(model=llm_service.LLM_MODEL, messages=[{"role": "system", "content": SYSTEM_MASTER}, {"role": "user", "content": f"{candidato['pregunta']}\n{referencia}"}], temperature=0.3)
                    respuesta = (response.choices[0].message.content or "").strip()
                    if respuesta:
                        break
                except Exception as exc:
                    self.stdout.write(self.style.WARNING(f"Intento {intento + 1} falló: {exc}"))
                    time.sleep(max(0, options["pausa"]))
            if respuesta:
                guardar_par(candidato["pregunta"], respuesta, candidato["fuente"], candidato.get("metadata", {}))
                ok += 1
            else:
                fallos += 1
            time.sleep(max(0, options["pausa"]))
        self.stdout.write(self.style.SUCCESS(f"Listo: {ok} pares destilados, {fallos} fallos. Memoria total: {previos + ok} pares."))
