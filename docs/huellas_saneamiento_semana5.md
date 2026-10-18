# Huellas SHA-256 tras el formato de 4 espacios (Semana 5)

La rama de saneamiento reformateó con 4 espacios los 13 JSON versionados (Matriz 3, aprobado por el PM). **Solo cambian los espacios, no los datos**: para cada archivo, `json.loads` da el mismo valor antes (`031e15e`, develop) y después (`c592d57`). Como el SHA-256 se calcula sobre los bytes, cambian las huellas.

## Por qué hay dos huellas por versión

Git guarda los archivos en LF. En Windows, con `core.autocrlf=true`, la copia de trabajo queda en CRLF, y el mismo contenido da otro SHA-256. Las huellas LF son las del repositorio, Linux y Docker; las CRLF, las de una copia de Windows. Con el PR #39 de DS (abierto al 18 oct), los scripts de evaluación y auditoría guardan además una huella normalizada a LF (`holdout_sha256_lf`, `dataset_sha256_lf`, con `src/agentes/huellas.py`), que es la que conviene comparar entre equipos.

## Archivos destacados

| Archivo | Antes LF | Antes CRLF | Después LF | Después CRLF |
|---|---|---|---|---|
| `tests/fixtures/holdout_final_analisis_semana3.json` | `86345fe90c7590b913e0c419891fdc5fb0b04583902b71d517199ba700913798` | `d2958d3cb8232c25151c43596598d549946332c1a8a3562189e71ec8d412622e` | `59a67a2b7378795635dd6cca0469c64766e4e8d23f84934d64f7f3ab42e5d6f5` | `257e2d7a69601c85794ddeadfdccc95bdafe3e1039af6770f4638e56420c4b58` |
| `src/datos/mensajes_comunidad_simulados.json` | `14d9a7eb6ff639e8900c85de950d4b2c4e6ce467e610f4d03888ca48ba5091c6` | `63f19b4756d26c4f4fd64f6b289ada8fe1bee83c5f1ef1194f6009c3a7bfe045` | `ef19536be51a02c80f795076101efaf520d3cadaae5263babda7e45de0c172b6` | `acd059644cc5f89b38133e640dc4f74f0de3383b61cc0376f9ae71eb3435829e` |

- Holdout congelado de DS: la evidencia del 12 oct (`docs/evidencia_holdout_proveedores_semana3.json`) guarda `d2958d3c…`, que es la huella **CRLF** del holdout anterior. En LF daba `86345fe9…`.
- Dataset simulado: los JSON de auditoría y estrés de DS (17 oct) guardan `dataset_sha256` `63f19b47…`, que también es CRLF. En LF daba `14d9a7eb…`.

## Trazabilidad de las evidencias anteriores

Las evidencias y los reportes que citan huellas anteriores **no se reescriben**: quedan como registro de la fecha en que se generaron. Para verificarlos, se compara con la columna «Antes» de la tabla, según el salto de línea con que se calculó. Son:

- `docs/evidencia_holdout_proveedores_semana3.json`;
- `docs/evaluacion_proveedores_semana3.md`;
- `docs/guia_pruebas_nvidia.md`;
- `docs/reporte_consistencia_semana4.md`.

DS genera una evidencia nueva e independiente, con su propia huella, cuando corra el holdout v2.

## Todos los archivos

| Archivo | Antes LF | Antes CRLF | Después LF | Después CRLF |
|---|---|---|---|---|
| `configuracion/relevancia.json` | `8888e311a88e709d9acee239c63833447137942506698c3f3d63b33ec6865e32` | `69264b9f21a77c2659b3a26aa3cee08fab056a93be5032ebb3b6fee4afae6611` | `9afd2a846d96782afac5317d039a53969ea7abd6400d214ad44302bdfdc44884` | `1ea103f522b146057a1bf1387d941ae9c61412703d805b122e5b7128c6c69ab8` |
| `docs/arquitectura-solucion/contrato-entrada.schema.json` | `93dbdb6e5709b299a73174e4f3995778a14f3380bffc44cf00b52366951bf683` | `bd18a4e01de911466b8bade0d7b1d7fad927ca5b0c10aadcd94a1fc47196f1ef` | `d07ea2189f309d93809691139fdfc1e6f2ec0902321de28f6108cba3c93fcbb1` | `1ef79164f4bb1e09a9a5a38e00dc0a35e426dc905f502b270fb4d104b67fa448` |
| `docs/arquitectura-solucion/contrato-intermedio-ingesta.schema.json` | `32afbf43250884cdd9b387d73c1ed2c9495d8287b474b64bdeb10342d6c6d2a0` | `8a741ff386c898b5635e81b0d42865ec0e61bee8cb97f1ad13ff5e4c4a1ee052` | `06f506788738cf116e70da4a49ef1048415766af83be91021450e0f2b3f88892` | `c3f45335cefbc86da3f322c8aa1ed39344b136bb0cb111b5a595050f7edeaa55` |
| `docs/arquitectura-solucion/contrato-salida.schema.json` | `09212a5ba25f09cb6cb5e23e99f6e2bc89e908de94a74a43fc9549e5443d12ab` | `5e6ce5852502833b94d1bed9093e5a0280b978a9fbb6451aa6d829536c68451b` | `345ac471774b0f3ed49fa479fa05095ff04d8b87340b263c5af8e73a767487fd` | `120472b63c0b3ef1ba94a1839f94f47797e2926b44207806f910139fd5e45fc9` |
| `docs/benchmark_calibracion_casos_ambiguos.json` | `bbc7ec6779a02090aad7815845c6125b49f903a786141ddc65febb7287cfa2f2` | `0ec5541a4ed1be2aae1aef4ddec7acdbe82cc2f04154ac2a4cb6ad460896f0b7` | `2996571b3b570b80d4db78ee83546e1862740632760e7e30d05dad6b618ac870` | `7d22b4a75d787d0e91406c7878eb6acb49ad108777592aea942e608a0127fa20` |
| `docs/evidencia2_entrega_ciencia_datos_completa.json` | `d77138988316d9a3c8ac7ab34de4c81a12916c19f0d47bcec0633382a348a53e` | `a09c6d8bf13a501c866ae0ad8a2f472e0e505e7e80b03eac1767291e23763583` | `f7f92bd8b1bab0ea05596c756b7435eed82433345ea9dc1293a81e88855e4d62` | `0a56f4f63c043154d78904021e8af2a2f71a54a9e72ffe84b17694568bbe1c49` |
| `docs/evidencia_entrega_ciencia_datos_completa.json` | `fa14b533a18d4d4d584b86d6c85058960a3b6e322269770c05bd3d776a22d8f7` | `fd24b6e9641fd5b3d5fb832ca48da9cb88b0b95def6985dbc4483cb57abd8c1b` | `a3bf4a7f2d1701f66b8f56bad899e1a870bbb64c450b4e7b018197a3e1ebcb1b` | `1a7786a86ce87fddc6a32d417713cf94803a973bc628ba55355c2804d10413f3` |
| `docs/evidencia_holdout_proveedores_semana3.json` | `a62c8a2aa30de50bed8d6c0736a8e4a8f417f8b4deecc3121b361ac10b46946a` | `13678b820095435964dc1ae9d7b60791950e049bd6a5ce29aabdaf04848f9102` | `5259f4c6a446859354f50578adad44396a739a81fe82681504b6edc6557bc72e` | `5923f9c7497b96ab4dc03c73338932058a7071c2c6c121414644d8a47b44da23` |
| `src/datos/mensajes_comunidad_simulados.json` | `14d9a7eb6ff639e8900c85de950d4b2c4e6ce467e610f4d03888ca48ba5091c6` | `63f19b4756d26c4f4fd64f6b289ada8fe1bee83c5f1ef1194f6009c3a7bfe045` | `ef19536be51a02c80f795076101efaf520d3cadaae5263babda7e45de0c172b6` | `acd059644cc5f89b38133e640dc4f74f0de3383b61cc0376f9ae71eb3435829e` |
| `tests/fixtures/casos_consistencia_semana4.json` | `eee5053174952186872bf777cb40866b4d674c9739de42be1b406ee37a4ae5a2` | `cf630872e215ac91260a7d183039a6f085db037b50726678fad7a373759cced0` | `d36b7fcbaafbb52ac0fb234f095005fef2ccab3bdc48c252f73a70bb163dd2c1` | `f5aea2ead5be959c8343da0e7952ef8b40186e9e6a00404e4a73583a5c534300` |
| `tests/fixtures/casos_referencia_ia_candidatos.json` | `b2d1d90b6736d4c5daa05cf923fe319ed6ad937f687dce609d5365ea08b2a139` | `2bd38c732267f29766c440eca3b26f0ad410b6871b4aed3f5f8314770d502673` | `b3c938a6a9da3dd30862c6ea3da991a8178be4d627d881442b64f780da6517cd` | `c9e7c33a9e8895a3baeb3546bb40f5f21f34c12eb157412cc3dd24f31eb33046` |
| `tests/fixtures/holdout_final_analisis_semana3.json` | `86345fe90c7590b913e0c419891fdc5fb0b04583902b71d517199ba700913798` | `d2958d3cb8232c25151c43596598d549946332c1a8a3562189e71ec8d412622e` | `59a67a2b7378795635dd6cca0469c64766e4e8d23f84934d64f7f3ab42e5d6f5` | `257e2d7a69601c85794ddeadfdccc95bdafe3e1039af6770f4638e56420c4b58` |
| `tests/fixtures/prueba_reddit_controlada.json` | `89f92ac0bcc99e58882ff104b0b283843ab9cb3ee2db82fa9bded9fb10ad39a0` | `3fc3f39fd5db0f4f5731b81cacb4c92fb6f15012a4f6e48002518506eb5b8787` | `e5cdd215f0323a03471b56e697243e758365fa3b51b28beb93f12be7e1d6df13` | `981b782a101e867d590ce93cebe5194f8acef8dbf1a83b1d56293b8f78542536` |

Recalculado desde los blobs de git (`git show <rev>:<ruta>`), sin pasar por la copia de trabajo, para que `core.autocrlf` no altere el resultado.
