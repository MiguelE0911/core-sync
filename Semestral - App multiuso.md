Proyecto Semestral – App Multi Propósito

**Aplicación**** de ****monitoreo**** y ****administración**** ****remota**** del mini PC BOSGAME**

El estudiante desarrollará individualmente una aplicación profesional con 25 acciones obligatorias para monitorear, administrar y mantener el mini PC BOSGAME con Windows mediante una red local. Las operaciones deberán ejecutarse realmente en el equipo remoto y producir evidencias verificables.

| Aspecto | Definición |
| --- | --- |
| Modalidad | Individual y por turnos |
| Equipo administrado | Un mini PC BOSSGAME con Windows |
| Cliente | Aplicación ejecutada desde la computadora del estudiante |
| Conectividad | Red local sin dependencia de internet durante la evaluación |
| Compatibilidad del cliente | Windows con versión probada documentada |
| Acciones obligatorias | 25 |

## Propósito y alcance

Aplicar conocimientos de redes, sistemas operativos, programación y administración remota. El estudiante deberá explicar cómo obtiene los datos, interpretar los resultados y demostrar que cada operación se realizó en BOSSGAME.

BOSSGAME con Windows será el único equipo administrado. La aplicación se ejecutará desde la computadora del estudiante con Windows y realizará todas las acciones de forma remota en BOSSGAME.

Cada acción incluye todos sus pasos de comprobación. Las funciones agrupadas no aumentan el total: conectar y desconectar integran la acción 3; iniciar, detener y reiniciar un servicio integran la acción 14.

## Preparación y organización

### Preparación del estudiante

Elegir y justificar lenguaje, bibliotecas, mecanismo remoto y método de transferencia. Comprobar autenticación, permisos y funcionamiento del cliente en Windows. Separar interfaz, conexión, operaciones y registro; evitar que consultas o transferencias congelen la ventana.

### Estructura personal en BOSGAME

Ruta de ejemplo: C:\Laboratorio\AMartinez. El identificador será validado por el docente y no admitirá separadores ni secuencias que permitan salir de la carpeta asignada.

| Elemento | Contenido |
| --- | --- |
| Archivos | Transferencias y copias de trabajo |
| Respaldos | Copias recuperables y manifiestos |
| Restaurados | Contenido recuperado para verificación |
| Evidencias | Capturas y comprobaciones |
| Informes | Informe individual |
| Temporales | Archivos destinados a la práctica de limpieza |
| identificacion.txt y actividad.csv | Identidad e historial de operaciones |

Conservar trabajos anteriores y separar sesiones mediante un identificador único. Si se utilizan cuentas administrativas compartidas, las carpetas permiten organizar evidencias, pero no aíslan los datos de otros usuarios con los mismos permisos.

## Acciones de conexión y monitoreo

### 1 Configurar el acceso a BOSGAME

Guardar nombre, IP y parámetros de conexión sin fijarlos en el código. Validar entradas y proteger credenciales.

### 2 Identificar al estudiante

Registrar nombre completo, grupo e identificador. Asociar cada operación a la identidad y sesión; generar identificacion.txt.

### 3 Conectar y desconectar la sesión remota

Comprobar autenticación y destino. Mostrar estado, gestionar fallos y cerrar la sesión liberando sus recursos.

### 4 Preparar la carpeta personal

Crear la estructura indicada en BOSGAME. Conservar lo existente y verificar físicamente carpetas y archivos.

### 5 Consultar información del sistema

Mostrar nombre del equipo, versión de Windows, arquitectura, procesador y memoria instalada. Identificar los datos no disponibles.

### 6 Consultar el uso de CPU

Mostrar porcentaje e instante de consulta con un intervalo de medición definido. Demostrar variación al cambiar la carga.

### 7 Consultar el uso de RAM

Mostrar memoria total, utilizada y disponible con unidades consistentes y fuente de consulta documentada.

### 8 Consultar almacenamiento

Mostrar capacidad, espacio utilizado y libre por unidad. Contrastar el resultado con el sistema remoto.

### 9 Consultar procesos

Listar nombre, PID y consumo de recursos disponible. Identificar un proceso de prueba en ejecución.

## Acciones de red y administración

### 10 Consultar configuración de red

Mostrar interfaces, IP, MAC, máscara o prefijo, puerta de enlace y DNS disponibles. Admitir varias interfaces y campos vacíos.

### 11 Comprobar conectividad con BOSGAME

Indicar método, respuesta y tiempo. Ante un fallo, informar sin respuesta; un ping fallido no demuestra que el equipo esté apagado.

### 12 Examinar puertos TCP autorizados

Examinar únicamente el rango autorizado. Distinguir conexión aceptada, rechazada y resultado indeterminado o sin respuesta.

### 13 Consultar servicios

Mostrar nombre y estado real de los servicios definidos por el docente. No deducir el servicio únicamente por el número de puerto.

### 14 Administrar un servicio de práctica

Permitir iniciar, detener y reiniciar el servicio autorizado. Consultar el estado posterior y demostrar las tres operaciones.

### 15 Diagnosticar cerrar y restaurar el puerto de práctica

Relacionar puerto, PID y servicio; seleccionar una instrucción del menú, verificar el cierre, guardar evidencia y restaurar el escenario.

### 16 Explorar la carpeta personal

Listar nombres, tipos y tamaños. Validar las rutas efectivas para mantener la operación dentro del espacio asignado.

### 17 Crear una subcarpeta

Validar el nombre, crearla dentro de la carpeta personal y comprobar existencia. Si ya existe, informar sin borrar su contenido.

## Acciones de archivos y mantenimiento

### 18 Enviar un archivo a BOSGAME

Transferir desde el cliente, mostrar indicadores de avance y comparar integridad. Solicitar decisión antes de sobrescribir.

### 19 Descargar un archivo de BOSGAME

Recuperar en la carpeta local del estudiante, mostrar indicadores y verificar integridad. Distinguir archivos incompletos de completados.

### 20 Copiar un archivo en BOSGAME

Crear una copia dentro de la carpeta personal, conservar el original y verificar el resultado. Gestionar nombres existentes.

### 21 Crear un respaldo

Respaldar una carpeta personal en Respaldos. Registrar fecha y manifiesto; evitar incluir el respaldo dentro de sí mismo.

### 22 Restaurar un respaldo

Recuperar en Restaurados, conservando originales. Comparar archivos y sumas de comprobación con el contenido respaldado.

### 23 Analizar y limpiar temporales de práctica

Examinar solo Temporales del estudiante; mostrar candidatos y tamaños. Tras selección y confirmación, borrar y registrar espacio realmente liberado y fallos.

### 24 Guardar historial y generar el informe

Registrar operaciones, errores y evidencias. Guardar historial e informe localmente y en BOSGAME; identificar escrituras pendientes y sincronizar sin duplicar.

### 25 Recuperar un archivo desde una ruta revelada

Admitir la ruta que entregue el docente, listar sus archivos, seleccionar y descargar a Recuperados local. Conservar el original y comparar integridad.

## Diagnóstico del puerto de práctica

La acción 15 integra el ciclo completo de diagnóstico, corrección y restauración. La condición de un solo puerto abierto corresponde únicamente al rango de evaluación; BOSGAME puede mantener otros puertos necesarios para la administración.

| Opción del menú | Parámetro y resultado |
| --- | --- |
| 1 Consultar puertos en escucha | Mostrar puertos TCP locales y PID mediante la sesión remota |
| 2 Consultar proceso o servicio | Consultar el PID o nombre e identificar el responsable |
| 3 Detener servicio | Detener únicamente el servicio de práctica autorizado |
| 4 Terminar proceso | Terminar únicamente el PID validado del proceso de práctica |
| 5 Restaurar servicio | Iniciar nuevamente el servicio preparado y comprobarlo |

### Secuencia de demostración

1. Registrar estudiante, sesión, BOSSGAME y rango autorizado; guardar el estado inicial.

1. Explorar el rango e identificar el puerto que acepta conexiones. Relacionarlo con el proceso o servicio remoto.

1. Seleccionar una instrucción y completar sus parámetros. Mostrar la instrucción real antes de ejecutarla y su salida después.

1. Verificar que el proceso o servicio ya no escucha y repetir la prueba de conexión. Una espera agotada por sí sola no demuestra el cierre.

1. Guardar la evidencia de corrección antes de restaurar: instrucción, salida y comprobaciones.

1. Restaurar el servicio y verificar estado activo, puerto accesible y administración remota disponible. Guardar el resultado.

La aplicación no elegirá automáticamente la solución. Utilizar plantillas controladas y parámetros validados. Si el proceso se reinicia automáticamente, el estudiante deberá reconocerlo y detener el servicio de práctica. Solo mostrar laboratorio listo para el siguiente estudiante cuando todas las comprobaciones de restauración hayan pasado.

Transferencias y registro de evidencias

Las acciones 18, 19 y 25 mostrarán mediciones reales durante la transferencia y mantendrán operativa la interfaz.

| Indicador | Información requerida |
| --- | --- |
| Archivo y rutas | Nombre, equipo, origen y destino |
| Tamaño y avance | Tamaño total, bytes transferidos y porcentaje |
| Velocidad actual y promedio | Bytes por unidad de tiempo con unidades explícitas |
| Tiempo | Tiempo transcurrido y estimación restante |
| Estado | Conectando, transfiriendo, verificando, completado, cancelado o error |
| Integridad | Comparación de sumas de comprobación de origen y destino |

Usar unidades consistentes: MB/s para millones de bytes por segundo o MiB/s para múltiplos de 1 048 576 bytes. Separar tiempo de conexión, transferencia y verificación. Para archivos vacíos, evitar divisiones entre cero. Mostrar calculando cuando todavía no exista una estimación válida.

Solo indicar completado y verificado después de terminar la transferencia y comprobar integridad. La velocidad observada depende de discos, protocolo y carga; no equivale automáticamente a la capacidad del enlace.

### Ruta revelada durante la evaluación

La acción 25 constituye una excepción de lectura al espacio personal, limitada a la ruta autorizada por el docente en BOSSGAME. La ruta no estará fija en el código. Probar rutas con espacios, inexistentes y sin permiso; no modificar el archivo original.

### Registro mínimo

Registrar identificador de sesión y operación, estudiante, equipo, fecha y zona horaria, acción, parámetros no sensibles, origen y destino cuando corresponda, resultado, error y referencia de evidencia. Nunca incluir contraseñas. Diferenciar operación ejecutada de operación verificada.

Si falla la escritura remota, guardar localmente como pendiente y sincronizar posteriormente sin duplicados. Las capturas complementan los archivos e historiales físicos conservados en BOSGAME.

## Interfaz y presentación profesional

| Sección | Contenido |
| --- | --- |
| Panel principal | BOSSGAME, conexión y resumen de recursos |
| Conexión y estudiante | Parámetros de acceso, identidad y carpeta personal |
| Monitoreo | Sistema, CPU, RAM, almacenamiento y procesos |
| Red y servicios | Interfaces, conectividad, puertos y servicios |
| Archivos y mantenimiento | Transferencias, respaldo, restauración y temporales |
| Historial e informes | Operaciones, errores, evidencias e informe |

### Identidad del producto

Presentar nombre original con una explicación breve, logo e icono legibles, paleta, tipografías e iconografía coherentes. Incluir autor, versión, propósito, compatibilidad y créditos en Acerca de. Indicar licencias de recursos ajenos cuando corresponda.

### Experiencia de uso

Mostrar estudiante, equipo, IP y conexión antes de ejecutar operaciones. Combinar texto y color para los estados; incluir validaciones, indicadores de carga y mensajes que ayuden a resolver fallos. Evitar botones sin función y métricas simuladas.

### Fundamentos que debe explicar el estudiante

Distinguir cliente y equipo remoto, conectividad y autenticación, puerto y servicio, PID y proceso, respaldo y restauración. Explicar permisos y elevación efectiva en Windows, transferencia e integridad y diferencia entre una operación solicitada y una comprobada.

### Compatibilidad y uso de IA

Demostrar la ejecución del cliente en Windows y documentar la versión probada. Todas las acciones y los comandos se ejecutarán en el mini PC BOSGAME con Windows. Si utiliza IA, documentar sus aportes, verificar el código y poder explicarlo y modificarlo durante la defensa, conforme a las normas del curso.

## Entregables y evaluación

- Aplicación ejecutable o instalación reproducible para Windows.

- Código fuente organizado y configuración sin credenciales incorporadas.

- Nombre, logo, icono y ficha del producto con público objetivo, beneficios y limitaciones reales.

- Manual con requisitos, instalación, conexión, funciones, capturas y solución de problemas.

- Matriz de las 25 acciones y evidencias conservadas en BOSGAME.

- Informe final y demostración individual con defensa técnica.

### Comprobación de aceptación

La matriz incluirá número de acción, precondición, entrada, resultado esperado, resultado obtenido, evidencia y estado. Probar credenciales incorrectas, permisos insuficientes, BOSGAME sin respuesta, ruta inexistente, interrupción de transferencia, archivo vacío, falta de espacio, nombre existente y fallo de restauración. Verificar el estado real del destino, además del mensaje de la aplicación.

| Criterio | Peso |
| --- | --- |
| Funcionamiento de las 25 acciones | 35 % |
| Diagnóstico cierre y restauración del puerto | 15 % |
| Transferencias respaldos e integridad | 15 % |
| Organización del código y manejo de errores | 10 % |
| Identidad visual y experiencia de uso | 10 % |
| Documentación e instalación | 5 % |
| Defensa individual y comprensión | 10 % |
| Total | 100 % |

La rúbrica es una propuesta docente. Las fechas, turnos, credenciales, mecanismo remoto, servicio de práctica, rango TCP y ruta del archivo se establecerán antes o durante la evaluación según corresponda. La aplicación admitirá estos parámetros sin modificar su código.


Nombre elegido para la app: CoreSync