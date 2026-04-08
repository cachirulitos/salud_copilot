# Contexto del Proyecto: Salud Copilot
**Objetivo del Documento:** Proveer contexto profundo, detallado y funcional sobre el flujo de la aplicación "Salud Copilot" para generar un "Pitch" ganador de Hackathon enfocado en valor hospitalario y resolución de problemas.

---

## 1. El Problema que Resolvemos
En clínicas de alto flujo (multiestudios como laboratorios, rayos X, ultrasonido, etc.), los pacientes sufren tiempos de espera enormes y frustrantes debido a una logística anticuada: se forman en una fila estática y ciega para cada estudio, mientras otras áreas de la misma clínica están vacías. Los médicos no saben cuánta gente real hay afuera, y el orden en el que se atienden los pacientes no está optimizado para la velocidad global térmica del centro médico.

**Salud Copilot** es el sistema operativo inteligente para clínicas 4.0. Convierte las filas de espera físicas en *rutas dinámicas e iterativas*, balanceadas en tiempo real por inteligencia artificial, visión computacional y un motor de reglas médicas.

## 2. Flujo Integral de la Aplicación (El "User Journey")

### Paso 1: El Check-In Inteligente (Kiosko / Portal)
1. El paciente llega a la clínica y registra los estudios físicos que se va a realizar (Ej. Análisis de Sangre, Papanicolaou, y Ultrasonido) a través del portal de Check-in.
2. Atrás del telón, nuestro **Motor de Reglas Clínicas** valida los flujos obligatorios invariables (Por ejemplo: la regla estricta dicta que un *Papanicolaou* debe preceder a un *Ultrasonido Transvaginal*, o que los análisis en sangre con ayuno tienen prioridad absoluta).
3. Una vez validada la seguridad médica, el **Algoritmo de Optimización de Colas** (apoyado por IA Predictiva) procesa qué áreas están más vacías e inscribe instantáneamente al paciente en la sala donde será atendido más rápido.

### Paso 2: El Asistente en el Bolsillo (WhatsApp Bot)
1. Al terminar su check-in, el paciente recibe **automáticamente un mensaje en WhatsApp** a través de nuestro Bot.
2. El paciente ya no está amarrado a una silla en una sala abarrotada. Puede ir a la cafetería. El sistema interactúa con él, informándole su tiempo exacto de espera, notificaciones automáticas ("Tu turno en ultrasonido está listo en 5 minutos") y guiándolo por la clínica paso a paso.

### Paso 3: Análisis del Mundo Físico (Computer Vision - YOLO)
1. Mientras la aplicación rige la lógica digital, cámaras IP en la clínica observan las salas de espera.
2. Nuestro **Worker de Computer Vision** escanea el metraje y cuenta cuántos cuerpos reales existen en el área de Imagenología o Laboratorio. 
3. *¿Por qué esto importa?* Porque a veces hay familiares sentados, o gente que se saltó el sistema. La visión computacional manda datos al **Modelo Predictivo de Machine Learning (ML)** en el backend para predecir con exactitud extrema los verdaderos tiempos de espera, cruzando la "lista de espera digital" con las personas "físicas" detectadas por la IA.

### Paso 4: Empoderando al Paciente (Reordenamiento Dinámico)
1. Mientras espera, el paciente accede a su portal temporal de la visita y decide que prefiere ir a Rayos X antes que a su Electrocardiograma.
2. Con simples flechas (Drag & Drop), **cambia de fila él mismo**.
3. El Backend revalida el salto instantáneamente contra el Motor de Reglas Médicas para evitar incongruencias de la salud. Si es legal, la magia sucede: el gestor de colas del backend lo saca instantáneamente de la fila del primer médico y lo inserta en la cola del otro médico. 

### Paso 5: El Doctor Controlando el Tráfico (Dashboard WebSockets)
1. Dentro de los consultorios, los médicos ven un dashboard en **tiempo real**. 
2. Cuando el paciente cambia dinámicamente de fila o avanza tras terminar su estudio, **todo ocurre en directo mediante WebSockets**.
3. El dashboard del médico que "perdió" al paciente actualiza inmediatamente removiendo al paciente de su lista y lanzando una alerta flotante de ("El paciente X flexibilizó su ruta"), mientras en la pantalla del médico nuevo el paciente aparece materializado en su sistema de inmediato.
4. **Alerta de Cuellos de Botella (Overtime)**: Si un médico se tarda más de lo estipulado en una consulta superando su métrica histórica asignada por el ML de consulta esperada, el sistema emite señales de alarma a las demás áreas y el algoritmo redirecciona transparentemente la afluencia nueva de personas a otras áreas para evitar colpasos.

## 3. Resumen de los 4 Pilares Funcionales (Para el Pitch)

*   **Visión Computacional & ML Predictivo:** Mapeamos el mundo biológico real (gente esperando vs gente agendada) usando cámaras de seguridad e inteligencia artificial para predecir "Cuellos de botella inminentes".
*   **Decoupled Rules Engine:** Aplicación rigurosa de precedencia médica para asegurar calidad y cuidado de la salud sin importar qué tanto la IA intente optimizar la ruta.
*   **Enrutamiento Dinámico Empoderado:** Las filas ya no son de la clínica, son del paciente. El usuario altera la ruta en tiempo real y todos los tableros de doctores en el edificio reaccionan en un abrir y cerrar de ojos, sin romper operaciones.
*   **Bot Conversacional Unificado:** Rompiendo la cadena de la silla de espera y devolviéndole la certidumbre al usuario sobre su tiempo real hasta que sea atendido enviándolo vía WhatsApp.

---
**Instrucción para el LLM (Ej. Gemini):** Con todo este contexto operativo exacto, extrae una narrativa altamente emocional, un discurso demoledor que enganche a emprendedores, médicos y jueces de un Hackathon mostrando cómo revolucionar la experiencia hospitalaria mediante operaciones algorítmicas ágiles.
