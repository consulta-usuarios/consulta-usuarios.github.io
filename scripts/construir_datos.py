#!/usr/bin/env python3
"""
Convierte el padrón del TSE (PADRON_COMPLETO.txt) en una "base de datos"
estática que se puede servir desde GitHub Pages. Solo guarda cédula y nombre
completo; el resto de campos del padrón se descarta.

Uso:
    python3 scripts/construir_datos.py RUTA/PADRON_COMPLETO.txt --corte "octubre 2026"

Genera la carpeta  data/  junto a index.html:

    data/indice.json        manifiesto (primer registro de cada bloque)
    data/ced/N.gz           bloques ordenados por cédula
    data/ap1/N.gz           bloques ordenados por 1er apellido, 2do, nombre
    data/ap2/N.gz           bloques ordenados por 2do apellido, 1ero, nombre
    data/nom/N.gz           bloques ordenados por nombre, 1er, 2do apellido

Cada bloque es texto UTF-8 comprimido con gzip, un registro por línea:
    cedula|nombre|apellido1|apellido2

La página busca en el manifiesto qué bloques pueden contener la consulta,
descarga solamente esos (unos ~40 KB cada uno) y filtra en el navegador.

Solo usa la biblioteca estándar de Python 3.8+.
"""

import argparse
import datetime as dt
import gzip
import json
import os
import re
import shutil
import sys
import unicodedata

TAMANO_BLOQUE = 5000
SEP = "|"

_combinantes = re.compile("[̀-ͯ]")
_apostrofes = re.compile("['.´`]")
_no_alfanum = re.compile("[^A-Z0-9 ]+")
_espacios = re.compile(r"\s+")


def normalizar(texto):
    """Debe coincidir EXACTAMENTE con normalizar() en index.html."""
    t = unicodedata.normalize("NFD", texto)
    t = _combinantes.sub("", t).upper()
    t = _apostrofes.sub("", t)
    t = _no_alfanum.sub(" ", t)
    return _espacios.sub(" ", t).strip()


def leer_texto(ruta):
    """El TSE publica en ISO-8859-1 (latin-1); se acepta UTF-8 por si acaso."""
    with open(ruta, "rb") as f:
        crudo = f.read(1 << 20)
    try:
        crudo.decode("utf-8")
        cod = "utf-8"
    except UnicodeDecodeError:
        cod = "latin-1"
    return open(ruta, "r", encoding=cod, newline=None), cod


def escribir_bloques(carpeta, orden, lineas, clave):
    """Escribe los registros en el orden dado, en bloques gzip; devuelve
    la lista con la clave del primer registro de cada bloque."""
    os.makedirs(carpeta)
    primeras = []
    for n, inicio in enumerate(range(0, len(orden), TAMANO_BLOQUE)):
        tramo = orden[inicio:inicio + TAMANO_BLOQUE]
        primeras.append(clave(tramo[0]))
        cuerpo = "\n".join(lineas[i] for i in tramo).encode("utf-8")
        with open(os.path.join(carpeta, f"{n}.gz"), "wb") as f:
            # mtime=0 -> mismo contenido produce el mismo archivo (diffs limpios en git)
            f.write(gzip.compress(cuerpo, compresslevel=9, mtime=0))
    return primeras


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("padron", help="PADRON_COMPLETO.txt del TSE")
    ap.add_argument("--salida", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data"),
                    help="carpeta de salida (por defecto ../data)")
    ap.add_argument("--corte", default="", help='texto de fecha de corte, ej. "octubre 2026"')
    args = ap.parse_args()

    salida = os.path.abspath(args.salida)
    if os.path.basename(salida) != "data":
        sys.exit("Por seguridad la carpeta de salida debe llamarse 'data'.")

    # ---- 1. Leer padrón -------------------------------------------------
    cache = {}  # texto crudo -> (texto limpio, clave normalizada); muchos nombres se repiten

    def campo(crudo):
        r = cache.get(crudo)
        if r is None:
            limpio = _espacios.sub(" ", crudo).strip()
            r = cache[crudo] = (limpio, normalizar(limpio))
        return r

    lineas, k_ced, k_nom, k_a1, k_a2 = [], [], [], [], []
    archivo, cod = leer_texto(args.padron)
    print(f"Leyendo {args.padron} ({cod})…", flush=True)
    malas = 0
    with archivo:
        for num, fila in enumerate(archivo, 1):
            partes = fila.rstrip("\r\n").split(",")
            if len(partes) != 8:
                if fila.strip():
                    malas += 1
                continue
            ced, nom, a1, a2 = partes[0], partes[5], partes[6], partes[7]
            ced = ced.strip()
            if not ced.isdigit():
                malas += 1
                continue
            nom, kn = campo(nom)
            a1, ka1 = campo(a1)
            a2, ka2 = campo(a2)
            lineas.append(SEP.join((ced, nom, a1, a2)))
            k_ced.append(ced)
            k_nom.append(kn)
            k_a1.append(ka1)
            k_a2.append(ka2)
            if num % 500000 == 0:
                print(f"  {num:,} filas", flush=True)
    cache.clear()
    total = len(lineas)
    print(f"  {total:,} registros válidos, {malas} filas descartadas", flush=True)
    if not total:
        sys.exit("No se encontró ningún registro.")

    # ---- 2. Escribir índices ------------------------------------------------
    if os.path.isdir(salida):
        for sub in ("ced", "ap1", "ap2", "nom"):
            shutil.rmtree(os.path.join(salida, sub), ignore_errors=True)
    os.makedirs(salida, exist_ok=True)

    indices = {
        # nombre: función que arma la clave de ordenamiento del registro i
        "ced": lambda i: k_ced[i],
        "ap1": lambda i: SEP.join((k_a1[i], k_a2[i], k_nom[i], k_ced[i])),
        "ap2": lambda i: SEP.join((k_a2[i], k_a1[i], k_nom[i], k_ced[i])),
        "nom": lambda i: SEP.join((k_nom[i], k_a1[i], k_a2[i], k_ced[i])),
    }
    manifiesto = {}
    for nombre, clave in indices.items():
        print(f"Generando índice '{nombre}'…", flush=True)
        orden = sorted(range(total), key=clave)
        manifiesto[nombre] = escribir_bloques(os.path.join(salida, nombre), orden, lineas, clave)
        del orden

    meta = {
        "version": 2,
        "total": total,
        "tamanoBloque": TAMANO_BLOQUE,
        "corte": args.corte,
        "generado": dt.date.today().isoformat(),
        "indices": manifiesto,
    }
    with open(os.path.join(salida, "indice.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, separators=(",", ":"))

    # Versiones anteriores generaban distelec.json; ya no se usa
    viejo = os.path.join(salida, "distelec.json")
    if os.path.exists(viejo):
        os.remove(viejo)

    tam = sum(os.path.getsize(os.path.join(r, a)) for r, _, fs in os.walk(salida) for a in fs)
    archivos = sum(len(fs) for _, _, fs in os.walk(salida))
    print(f"Listo: {archivos:,} archivos, {tam / 1e6:,.1f} MB en {salida}")


if __name__ == "__main__":
    main()
