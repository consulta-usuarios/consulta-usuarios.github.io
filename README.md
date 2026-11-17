# Consulta de usuarios

Página estática para consultar el Padrón Nacional Electoral de Costa Rica (TSE)
por **cédula**, **nombre** o **apellidos**. Solo muestra la cédula y el nombre
completo; el resto de campos del padrón no se publica. No necesita servidor ni base de datos
externa: funciona en GitHub Pages.

## Cómo funciona

`scripts/construir_datos.py` convierte `PADRON_COMPLETO.txt` en ~3.000 archivos
pequeños comprimidos (`data/`), ordenados de cuatro formas:

| Carpeta     | Orden                                  | Sirve para                         |
|-------------|----------------------------------------|------------------------------------|
| `data/ced`  | cédula                                 | consulta por cédula                |
| `data/ap1`  | 1er apellido, 2do apellido, nombre     | búsquedas con 1er apellido         |
| `data/ap2`  | 2do apellido, 1er apellido, nombre     | búsquedas con 2do apellido         |
| `data/nom`  | nombre, 1er apellido, 2do apellido     | búsquedas solo por nombre          |

`data/indice.json` guarda el primer registro de cada bloque. La página usa ese
índice para saber qué bloques descargar (normalmente 1 de ~80 KB) y filtra en el
navegador. Las búsquedas no distinguen tildes, Ñ/N ni mayúsculas.

## Actualizar los datos

1. Descargue el padrón completo desde el sitio del TSE y descomprímalo.
2. Desde esta carpeta ejecute (Python 3.8+, sin dependencias):

```bash
python3 scripts/construir_datos.py ~/Downloads/padron_completo/PADRON_COMPLETO.txt --corte "octubre 2026"
```

Tarda ~1,5 minutos y reemplaza `data/`. `--corte` es el texto que se muestra bajo
el título (opcional).

## Probar en su computadora

```bash
python3 -m http.server 8000
```

Abra http://localhost:8000 (abrir `index.html` con doble clic no funciona; necesita
un servidor).

## Publicar en GitHub Pages

1. Cree un repositorio en GitHub (p. ej. `consulta-usuarios`).
2. En esta carpeta:

```bash
git init -b main
git add .
git commit -m "Consulta del padrón"
git remote add origin https://github.com/SU_USUARIO/consulta-usuarios.git
git push -u origin main
```

3. En GitHub: **Settings → Pages → Build and deployment → Source: Deploy from a branch**,
   rama `main`, carpeta `/ (root)`. En uno o dos minutos queda en
   `https://SU_USUARIO.github.io/consulta-usuarios/`.

## Notas

- **El sitio es público.** GitHub Pages publica para cualquiera (aun con repositorio
  privado, salvo planes Enterprise). El padrón ya es público por el TSE, pero tenga
  en cuenta que cualquiera puede descargar los archivos de `data/`. La página y
  `robots.txt` piden a los buscadores no indexar el sitio.
- **Tamaño:** ~245 MB en `data/`, dentro de los límites de GitHub (1 GB por sitio,
  ningún archivo cerca de 100 MB). Cada actualización mensual suma ~245 MB al
  historial de git; si el repositorio crece mucho, puede publicar cada actualización
  como un commit nuevo en una rama sin historial (`git checkout --orphan`).
- `.nojekyll` evita que GitHub procese el sitio con Jekyll (más rápido).
- Requiere un navegador de 2023 en adelante (usa `DecompressionStream`).
