# Carcasa y montaje mecánico

Fuente editable: `mechanical/enclosure.scad`. Exportables: `mechanical/stl/base.stl`, `lid.stl`, `speaker_clamp.stl`. Medidas en milímetros. El archivo incluye volúmenes simplificados de componentes; no son STEP oficiales ni modelos de tolerancia exacta.

## Geometría fijada

| Elemento | Posición / medida |
|---|---|
| Caja cerrada | 94 × 82 × 42; base 40; tapa 2 |
| Pared y fondo | 2 |
| PCB | origen X=7, Y=9; cara inferior Z=6; espesor 1,6 |
| Tornillos PCB | PCB (3,3), (61,3), (3,51), (61,51); taladro 3,2 |
| Tornillos tapa | caja (5,5), (89,5), (5,77), (89,77) |
| USB-C | hueco frontal 18 × 14, centro X=22, Z=19; sobremolde del cable ≤16 × 12 |
| Altavoz | centro caja (60,47), alojamiento Ø40,6 |
| Retenedor | interior Ø36,8; exterior Ø44,6; espesor 2 |
| Botón | centro (76,16), orificio Ø16,1, E-Switch PV6F240SS; reserva de tuerca Ø22 |
| LED | centro (87,29), orificio Ø3,2, Kingbright WP710A10SGD |
| Rejilla micrófono | centro (22,18), múltiples orificios Ø1,5 |
| Antena FPC | pared trasera, X=10…47,4; Z=16…33,5; radiador hacia interior |

El Visaton K40 art.2840 tiene Ø40±0,2, cuerpo posterior Ø36±0,3, reborde 1,3±0,2 y profundidad total 4,3±0,3 según el plano. El aro Ø36,8 deja al menos 0,25 mm radiales al cuerpo máximo de 36,3 mm y retiene el reborde. La junta de espuma cerrada se corta con Ø40/Ø36,5, espesor inicial 1 mm, comprimida a unos 0,7 mm: 2 mm de tapa + 0,7 de junta + 1,3 de reborde = plano nominal de sujeción Z=4 en coordenadas de tapa. Ajustar junta por tolerancia real; no apretar sobre la membrana.

Botón M16 con tuerca y arandela de su proveedor, contactos NO. Un anillo interior refuerza el panel hasta 3,5 mm de espesor local. El volumen de reserva contempla aproximadamente 18,5 mm de profundidad bajo la superficie exterior y Ø22 para la tuerca. Se comprobaron las separaciones nominales con el alojamiento del altavoz, el LED y los pilares de tapa. No sustituirlo por un botón largo sin modificar CAD.

## Impresión

PETG como primera opción, boquilla 0,4 mm, capas 0,2 mm, cuatro perímetros, cinco capas de techo/fondo, 25–35 % de relleno. PLA sirve para ajuste, pero verificar temperatura interior antes de uso prolongado. Los tres STL están orientados con su cara plana en Z=0. La base requiere un puente de 18 mm sobre la abertura USB; usar soporte local si la impresora no lo resuelve. No se ha ejecutado laminado ni impresión física.

Compensar contracción XY con una prueba de orificios antes de la caja completa. Los pilotos son 2,5 mm para tornillos M3 y 1,65 para M2 en plástico; roscar cuidadosamente sin atravesar la tapa. Debe quedar plástico bajo las puntas. Usar tornillos PCB M3×5, tapa M3×8 y retenedor M2×4. Tornillos PCB de cabeza cilíndrica Ømáximo 5,5 mm, sin arandelas anchas junto a U1. No usar M3×6 en PCB: con placa de 1,6 mm y pedestal de 4 mm podría acercarse demasiado al fondo.

## Secuencia

1. Limpiar rebabas, comprobar paso USB, diámetros de botón y LED; probar la PCB sin forzarla.
2. Soldar zócalos 1×7 y conectores antes de fijar la PCB. Montar U1 en dos zócalos y U2 en uno; la cámara se retira de U1, pero se mantiene su expansión con micrófono. No colocar microSD.
3. U2: usar dos espaciadores tubulares de nailon de altura nominal 11 mm entre caras de PCB, Øexterior ≤5 mm, paso ≥2,7 mm, y dos tornillos M2,5×18 con tuercas. Los agujeros locales de portadora son (36,65;35,97) y (49,35;35,97). La hembra Samtec SSW mide 8,51 mm y el plástico del macho TSW 2,54 mm: altura nominal conjunta 11,05 mm. Ajustar el espaciador a la altura real sin doblar placas ni forzar los zócalos; un juego distinto requiere revisar el conjunto.
4. Fijar la PCB sobre los cuatro pedestales con M3×5. Conectar antena U.FL verticalmente, sin palanca. Pegar sólo la antena a la pared trasera, dejando su cable sin tensión y sin cruzar el altavoz.
5. Insertar botón y LED en tapa. Aislar patillas con termorretráctil; asegurar LED con una pequeña cantidad de silicona neutra. El botón se fija con su tuerca.
6. Soldar al altavoz un par trenzado flexible de 26 AWG, longitud ≤100 mm. Colocar junta, altavoz y aro; alinear terminales con las ranuras del aro. Apretar los cuatro M2×4 uniformemente.
7. Guiar cables por las dos presillas de la base. Empezar con dos hilos de unos 120 mm para PTT y otros dos de unos 120 mm para LED; ajustar al recorrido real dejando bucle de servicio para abrir tapa. La BOM reserva 1 m total de cable, incluido el altavoz. Conectar J1, J2 y la bornera de U2 según `hardware/wiring.kicad_sch`.
8. Comprobar que nada pisa la membrana ni pellizca el cable RF. Cerrar con cuatro M3×8 después de completar pruebas eléctricas.

La antena A-02 SKU318020968 tiene cable de 65±2 mm. Orientar su alimentación hacia U1 y verificar alcance real antes de pegarla. La reserva posterior deja 15,2 mm respecto al borde de PCB considerando 1,8 mm de espesor de antena. El camino real depende del conector de la revisión de U1; no tensar el cable para cumplir el dibujo. Si no alcanza, se necesita una antena equivalente de cable más largo y nueva comprobación RF.

La rejilla no sella acústicamente el micrófono contra el volumen interno. Un pequeño conducto de espuma cerrada alrededor de su puerto puede mejorar recepción, sin taparlo. Esto y la separación acústica requieren una prueba física; semidúplex evita intentar reconocer la respuesta del propio altavoz.

## Regenerar y validar

```powershell
python -m pip install trimesh==4.6.8 numpy==2.2.6
python mechanical/export.py --openscad C:/ruta/openscad.exe --render
```

`validation/mechanical-meshes.json` comprueba mallas cerradas, orientación, volumen positivo, una pieza conectada por STL y apoyo sobre Z=0. También registra la intersección CGAL vacía entre las envolventes nominales modeladas y la carcasa, el sobremolde USB y la base, y las cabezas de tornillos PCB y los módulos. `validation/interfaces.json` comprueba agujeros y separaciones adicionales. Los cables flexibles, las tolerancias completas de los componentes y el comportamiento acústico quedan fuera de esos ensayos. No demuestra ajuste impreso, firmeza o disipación térmica. La caja no tiene clasificación IP ni protección contra líquidos.
