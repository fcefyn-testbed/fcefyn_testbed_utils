# Diseño 3D del rack

Esta carpeta contiene los archivos de diseño 3D (OpenSCAD, Fusion 360 y STL) utilizados para construir un rack de refrigeración personalizado para routers.

> **Nota:** Las imágenes referenciadas (`img/curved_intake_duct.png`, `img/airflow_chimney_duct_*.png`, etc.) no están incluidas. Crear `rack_design/img/` y añadir capturas si se desea visualización local. El sistema emplea un enfoque modular tipo chimenea para distribuir aire fresco desde un único ventilador de 120 mm a través de múltiples niveles.

## Resumen de piezas impresas

Para ensamblar el rack completo se imprimieron las siguientes piezas usando los archivos STL proporcionados:

*   **1x Conducto de admisión curvado (`curved_intake_duct.stl`):** Conecta el ventilador de 120 mm con la chimenea vertical.
*   **4x Conducto de chimenea con 3 niveles (`airflow_chimney_duct_3levels.stl`):** Segmentos verticales con rejillas de ventilación para tres niveles de routers.
*   **1x Conducto de chimenea con 2 niveles (`airflow_chimney_duct_2levels.stl`):** Segmento vertical con rejillas para dos niveles.
*   **1x Tapa de chimenea (`chimney_duct_cover.stl`):** Sella la parte superior de la chimenea para forzar el paso del aire por las rejillas.
*   **3x Base Belkin RT3200 (`belkin_rt3200_base.stl`):** Bases personalizadas para reemplazar las carcasas originales voluminosas.
*   **1x Soporte Arduino Nano (`NanoHolderA.stl`):** Bracket de montaje para el Arduino Nano.
*   **Logos decorativos (`logo fcefyn.stl`, `logo unc.stl`):** Detalles estéticos finales que representan FCEFyN y UNC.

## Detalles del diseño 3D

### 1. Conducto de admisión curvado (`curved_intake_duct.scad` / `.stl`)

Conducto loft tipo «saxofón» que transiciona desde la base circular del ventilador de 120 mm hasta el conector rectangular de la chimenea. Diseñado para flujo de aire suave sin esquinas internas pronunciadas.

<img src="img/curved_intake_duct.png" width="300">

*   **Parámetros:**
    *   `ancho_placa_base`: Ancho de la placa de montaje del ventilador (120 mm para ventiladores Bosser).
    *   `altura_saxofon`: Altura vertical de la transición.
    *   `desplazamiento_y`: Desplazamiento lateral entre el centro del ventilador y el centro de la chimenea.
    *   `rect_x` / `rect_y`: Dimensiones de la salida rectangular para ajustar a la chimenea.

### 2. Conducto de chimenea (`airflow_chimney_duct.scad` / `_2levels.stl` / `_3levels.stl`)

Conducto vertical modular y apilable. Cada módulo incluye rejillas segmentadas («branquias») anguladas a 45° para dirigir el aire hacia los routers sin requerir soportes de impresión.

<img src="img/airflow_chimney_duct_3levels.png" width="300" height="273"> <img src="img/airflow_chimney_duct_2levels.png" width="300">

*   **Parámetros:**
    *   `niveles_por_modulo`: Número de niveles de refrigeración por segmento (2 o 3 en los STL proporcionados).
    *   `dist_niveles`: Distancia vertical entre niveles (60 mm).
    *   `tolerancia`: Holgura para los conectores de apilado macho/hembra.
    *   `grosor_pared`: Grosor de pared para rigidez estructural.

### 3. Tapa de chimenea (`chimney_duct_cover.scad` / `.stl`)

Tapa simple con conector hembra que encaja en la parte superior del último segmento de chimenea para sellar el sistema.

<img src="img/chimney_duct_cover.png" width="300">

*   **Parámetros:**
    *   `grosor_pared`: Grosor de pared.
    *   `tolerancia`: Tolerancia de ajuste para el conector macho.

<img src="img/drawer_stop.png" width="300">

### 4. Base Belkin RT3200 (`belkin_rt3200_base.stl`)

Las carcasas originales del Belkin RT3200 eran demasiado grandes para el rack. Se reemplazaron por una base impresa en 3D para ahorrar espacio y mantener los routers fijos al conectar cables. Adaptación del [RT3200/E8450 Wall Mount Case](https://www.thingiverse.com/thing:5864938) de **TuxInvader** — solo el componente base, parte superior descubierta para refrigeración.

<img src="img/belkin_case_adapted.jpg" width="300">

### 5. Piezas auxiliares y decorativas

*   **Soporte Arduino Nano (`NanoHolderA.stl`):** Pequeño bracket de montaje para mantener el Arduino Nano fijo en su nivel asignado.

<img src="img/NanoHolder.jpg" width="300">

*   **Logos FCEFyN y UNC:** Logos decorativos impresos en 3D como detalles estéticos finales, que representan FCEFyN y UNC.

<img src="img/logos.png" width="300">

---

Los modelos OpenSCAD se imprimen sin soportes cuando se orientan correctamente. Impreso en Creality Ender 3 Pro.


# DOCUMENTACIÓN TÉCNICA: CONTROL REMOTO DE RACK (SSH + ARDUINO)

## 1. RESUMEN DEL PROYECTO
El rack incluye un módulo separado y opcional para la gestión de energía de distintos componentes del rack desde el host.

El control se realiza con el mismo microcontrollador Arduino Nano que comanda al módulo de 8 relés de los DUTs,
pero en este caso se trata de un módulo de relés SSR (reles de estado solido) para AC de 4 canales (solo se usan 2), el cable que lleva las señales de control
del arduino hasta el modulo tiene distancia de 2 metros y utiliza cableado estructurado.

## 2. ESPECIFICACIONES DE CARGA (220V AC)
Se corta únicamente el cable de LÍNEA (Fase - Marrón) para cada dispositivo.
- Canal 1: Switch TP-Link SG2016P (Seguro, ~145W PoE Máx).
- Canal 2: Cooler Booster AC (Seguro, 0.09A).
- IMPORTANTE: No se usa con fuente de 495W por picos de arranque (Inrush Current), ya que estos modulos de reles son de 2A por canal como maximo.

## 3. INFRAESTRUCTURA DE CONTROL (DC)
- Alimentación Módulo: Cargador externo 5V (Rojo a DC+, Negro a DC-).
- Distancia: 2 metros mediante cable UTP Cat5e/6.
- Configuración: Masa común (GND) compartida entre cargador, Arduino y módulo.

### TABLA DE AGRUPACIÓN DE CABLES UTP
| PAR TRENZADO    | COLOR HILO      | FUNCIÓN       | ORIGEN (ARDUINO) | DESTINO (MÓDULO) |
|-----------------|-----------------|---------------|------------------|------------------|
| Par Naranja     | Naranja         | Señal CH1     | Pin Digital (D2) | Borne CH1        |
|                 | Blanco/Naranja  | GND (Retorno) | Pin GND          | Borne DC-        |
| Par Verde       | Verde           | Señal CH2     | Pin Digital (D3) | Borne CH2        |
|                 | Blanco/Verde    | GND (Retorno) | Pin GND          | Borne DC-        |
| Par Azul        | Azul            | Señal CH3     | Pin Digital (D4) | Borne CH3        |
|                 | Blanco/Azul     | GND (Retorno) | Pin GND          | Borne DC-        |
| Par Marrón      | Marrón          | Señal CH4     | Pin Digital (D5) | Borne CH4        |
|                 | Blanco/Marrón   | GND (Retorno) | Pin GND          | Borne DC-        |

* NOTA: Los 4 hilos blancos se trenzan juntos en ambos extremos para minimizar 
  interferencias y asegurar el retorno de corriente.

## 4. LÓGICA DE OPERACIÓN (LOW LEVEL TRIGGER)
El módulo se activa por nivel bajo (0V).
- digitalWrite(PIN, LOW)  => DISPOSITIVO ENCENDIDO
- digitalWrite(PIN, HIGH) => DISPOSITIVO APAGADO

## 5. RECOMENDACIONES DE SEGURIDAD
1. Asegurar que la PC que corre el SSH no dependa del Switch controlado.
2. No pasar los 2 metros de UTP pegados a cables de alta potencia (220V).
3. Verificar que los hilos blancos y el negativo del cargador estén unidos.