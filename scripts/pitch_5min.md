# SaludCopilot — Pitch 5 Minutos (1 presentador)

---

## SLIDE 1 — APERTURA (30 seg)

**[Mostrar: Logo + nombre del proyecto]**

> "Imaginen esto: son las 7 de la mañana en una clinica de Salud Digna. Hay 200 pacientes esperando, 7 areas clinicas, y un solo objetivo — que cada persona reciba su atencion lo mas rapido posible.
>
> El problema? Hoy ese proceso se maneja con papel, gritos entre pasillos, y pacientes que no saben si les faltan 10 minutos o 2 horas.
>
> Nosotros construimos SaludCopilot — un copiloto de inteligencia artificial que optimiza todo el flujo del paciente, en tiempo real."

---

## SLIDE 2 — EL PROBLEMA (45 seg)

**[Mostrar: Datos del problema]**

> "En Mexico, clinicas de alto volumen como Salud Digna atienden entre 150 y 400 pacientes diarios por sucursal. Cada paciente necesita entre 1 y 5 estudios — laboratorio, ultrasonido, rayos X, electrocardiograma...
>
> Los problemas actuales son tres:
>
> **Uno** — Tiempos de espera impredecibles. El paciente no sabe cuanto le falta y la ansiedad crece.
>
> **Dos** — Orden de estudios ineficiente. No existe optimizacion — los pacientes van en el orden que les toco, aunque otra secuencia los sacaria 30 minutos antes.
>
> **Tres** — Cero comunicacion entre areas. Si un area se satura, nadie se entera hasta que el pasillo esta lleno.
>
> El resultado? Pacientes frustrados, doctores sin contexto, y recursos mal aprovechados."

---

## SLIDE 3 — LA SOLUCION (60 seg)

**[Mostrar: Diagrama de arquitectura simple — 4 modulos]**

> "SaludCopilot resuelve esto con cuatro modulos integrados:
>
> **Primero — Motor de Reglas Clinicas.** Un engine que conoce las restricciones medicas. Por ejemplo: el Papanicolaou debe ir antes del ultrasonido transvaginal. La densitometria antes de la tomografia. Estudios en ayuno primero. El sistema calcula la secuencia optima respetando todas las reglas clinicas, automaticamente.
>
> **Segundo — Prediccion de Tiempos con Machine Learning.** Un modelo de Random Forest entrenado con datos historicos que predice el tiempo de espera por area, considerando hora del dia, dia de la semana, capacidad del area, longitud de la fila, y si el paciente tiene cita. No es un numero fijo — se adapta en tiempo real.
>
> **Tercero — Bot de WhatsApp con IA.** El paciente recibe por WhatsApp toda su experiencia: su secuencia de estudios, tiempo estimado, instrucciones de preparacion, contenido educativo sobre cada estudio, y notificaciones cuando es su turno. Usa Gemini 2.5 Flash para responder preguntas en lenguaje natural — sin dar diagnosticos, solo orientacion clinica.
>
> **Cuarto — Dashboard Operativo en Tiempo Real.** Los doctores y administradores ven un panel con WebSocket que muestra filas por area, alertas de sobretiempo, KPIs, y la capacidad de cada consultorio. Todo se actualiza en vivo, sin recargar."

---

## SLIDE 4 — DEMO EN VIVO (120 seg)

**[Cambiar a pantalla del demo]**

> "Veamoslo en accion."

### Flujo del demo:

1. **Check-in** — "Aqui un paciente llega a la clinica. Selecciona sus 3 estudios — laboratorio, rayos X, y electrocardiograma. El sistema calcula la secuencia optima respetando reglas clinicas, y le asigna tiempos de espera con ML."

2. **Vista del paciente** — "El paciente ve su recorrido completo. Puede reordenar sus estudios pendientes — pero si viola una regla clinica, el sistema lo rechaza y le explica por que. Si el reorden no ahorra al menos 5 minutos, tampoco lo permite."

3. **Doctor login** — "El doctor inicia sesion con su ID de 4 digitos. Ve su fila de pacientes, el tiempo que lleva cada uno, y alertas si alguien supera el 15% de su tiempo estimado."

4. **Dashboard** — "El administrador ve todas las areas en un solo panel. Filas en tiempo real, pacientes activos, alertas de sobretiempo — todo actualizado por WebSocket sin delay."

5. **Pantalla de sala de espera** — "En la sala de espera, una pantalla tipo aeropuerto muestra los turnos por area, para que los pacientes sepan exactamente donde y cuando les toca."

6. **Avanzar paso** — "Cuando el doctor termina, avanza al paciente. El sistema automaticamente recalcula tiempos, mueve al paciente a la siguiente fila en Redis, y le notifica por WhatsApp."

> "Todo esto pasa en menos de un segundo. Sin papel. Sin gritos. Sin incertidumbre."

---

## SLIDE 5 — STACK TECNICO (30 seg)

**[Mostrar: Iconos de tecnologias]**

> "El stack es:
> - **Backend:** FastAPI con SQLAlchemy async y PostgreSQL
> - **Colas en tiempo real:** Redis con sorted sets
> - **ML:** scikit-learn con reentrenamiento automatico semanal
> - **Frontend:** Next.js 16 con React 19 y WebSocket nativo
> - **Bot:** WhatsApp Cloud API con Google Gemini 2.5 Flash
> - **Reglas:** Motor propio de reglas clinicas — 6 reglas validadas medicamente
>
> Todo corre en Docker Compose. 5 servicios. Un comando para levantar."

---

## SLIDE 6 — IMPACTO Y CIERRE (45 seg)

**[Mostrar: Metricas de impacto estimadas]**

> "Con SaludCopilot estimamos:
>
> - **Reduccion del 25-35% en tiempos de espera** — al optimizar secuencias y predecir con ML en lugar de asignar a ciegas.
> - **90% menos quejas por desinformacion** — el paciente siempre sabe donde esta, cuanto le falta, y que sigue.
> - **Deteccion de cuellos de botella en tiempo real** — las alertas de sobretiempo permiten actuar antes de que el problema escale.
> - **Cero friccion para adopcion** — todo es por WhatsApp, la app que ya usan 95 millones de mexicanos.
>
> No estamos reemplazando al doctor. Estamos dandole un copiloto.
>
> SaludCopilot. Atencion mas inteligente, pacientes mas tranquilos.
>
> Gracias."

---

## NOTAS PARA EL PRESENTADOR

- **Tiempo total:** ~5 minutos (30 + 45 + 60 + 120 + 30 + 45 = 330 seg = 5.5 min)
- **Si te pasas de tiempo:** Recorta la parte tecnica (Slide 5) a una sola frase: "FastAPI, Next.js, Redis, ML, WhatsApp — todo en Docker."
- **Si el demo falla:** Usa el pitch sin demo, enfocate en slides 2, 3 y 6
- **Tip:** Durante el demo, no expliques cada click. Haz los clicks y narra por encima. La audiencia entiende interfaces visualmente.
- **Credenciales demo:** Doctor login 0001 / 12345678
- **URLs clave:**
  - Check-in: `localhost:3000/checkin/1db93003-d50e-4f56-80d0-8b994b98eaa8`
  - Dashboard: `localhost:3000/dashboard`
  - Doctor: `localhost:3000/doctor/login`
  - Pantalla: `localhost:3000/pantalla/1db93003-d50e-4f56-80d0-8b994b98eaa8`
  - Paciente: `localhost:3000/patient-test/v1000001-0000-0000-0000-000000000001`
