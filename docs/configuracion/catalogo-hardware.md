# Catálogo de hardware del lab

Se presentan **imagenes y datos de identificación** del equipamiento físico del banco de pruebas. Para cableado, comandos y configuración conviene ir a las guías enlazadas en cada bloque o en la tabla final.

## Relés Arduino (rack)

El Arduino del rack controla la potencia de los DUTs y de parte de la infraestructura; el detalle de canales, UTP, comandos serial y daemon está en [arduino-relay.md](arduino-relay.md).

### Módulo SSR de 4 canales (Omron G3MB-202P)

<img src="../img/hardware/ssr-omron.png" alt="Módulo SSR de 4 canales Omron G3MB-202P" width="280" style="max-width:100%;height:auto;display:block;" loading="lazy" />

En el laboratorio usamos **CH1** para el switch TP-Link SG2016P (canal lógico 8) y **CH2** para el cooler AC (canal 9). Los canales **CH3** y **CH4** quedan libres.

| Parámetro | Valor |
|-----------|--------|
| Relé | Omron G3MB-202P por canal; fototriac; zero-cross |
| Control | 5 V DC; activo en bajo (~0-2,5 V, ~2 mA); módulo hasta ~48 mA |
| Carga | 100-240 V AC, 0,1-2 A por canal; fusible |
| Placa / conexiones | ~57 x 55 x 25 mm; **DC+** / **DC-**; **CH1-CH4** |
| En el lab | CH1 switch, CH2 cooler; CH3-CH4 libres |

### Fotek SSR-25DA (canal 10)

<img src="../img/hardware/ssr-fotek.png" alt="Fotek SSR-25DA" width="220" style="max-width:100%;height:auto;display:block;" loading="lazy" />

Este relé corta la fase hacia la carga en **CA** del canal 10 (la fuente del rack). En el firmware del Arduino la lógica es **activa en alto** (canal 10: HIGH = ON; canales 0-9: LOW = ON).

| Parámetro | Valor |
|-----------|--------|
| Tipo | CC → CA, alto voltaje |
| Entrada | 4-32 V DC |
| Salida | 90-480 V AC, hasta 25 A (según fabricante y cableado) |

### Módulo de 8 relés (DUTs 0-7)

<img src="../img/hardware/8-channel-relay.png" alt="Módulo de 8 relés electromecánicos" width="280" style="max-width:100%;height:auto;display:block;" loading="lazy" />

Sirve para los canales **0 a 7** (pines **D2-D9** del Arduino): relés electromecánicos optoacoplados, alimentación **5 V DC**.

| Parámetro | Valor |
|-----------|--------|
| Alimentación | 5 V DC; opto; LED SMD por canal |
| Contactos | Hasta 10 A @ 250 V AC o 30 V DC / 10 A (según módulo) |
| Firmware | Mismo patrón de disparo digital que el resto de entradas |

**Cajas de tomas:** Llave Luz Armada Richi Quantum ERA 2 Tomas 3 Módulos Blanco PVC (corte de fase).

## Fuente AC (carga canal 10)

La fuente que alimenta esa rama de **CA** se enchufa detrás del **Fotek**; el papel del canal 10 en el rack se explica en [arduino-relay](arduino-relay.md). Abajo va la ficha de la unidad que usamos (Coper Light metálica).

<img src="../img/hardware/psu.png" alt="Fuente Coper Light metálica" width="260" style="max-width:100%;height:auto;display:block;" loading="lazy" />

| Especificación | Valor |
|----------------|-------|
| Marca/Modelo | Coper Light Metálica |
| Potencia | 480 W |
| Entrada | 12-110 VAC, 50/60 Hz |
| Salida | 12-220 V |
| Temperatura de funcionamiento | 0-40 °C |
| Protección | Cortocircuito |

## Hub USB

En el host solemos usar un hub de **carcasa metálica** con varios puertos USB 3.0; la foto de referencia del repositorio se llama `hubusb-NSUH113Q.png`.

<img src="../img/hardware/hubusb-NSUH113Q.png" alt="Hub USB 10 puertos USB 3.0 con alimentación" width="280" style="max-width:100%;height:auto;display:block;" loading="lazy" />

| Característica | Detalle |
|----------------|---------|
| Puertos USB | 10 x USB 3.0 (5 Gbps), tipo A hembra |
| Carga rápida | 1 puerto QC3.0 (5 V / 3 A; 9 V / 2 A; 12 V / 1,5 A) |
| Compatibilidad | USB 2.0 y versiones anteriores |
| Carcaza | Metálica |
| Cable incluido | USB 3.0 A macho - B macho, 1 m (hacia la PC) |
| Fuente externa | 12 V, 5,4 A |
| Por puerto USB 3.0 | Hasta 5 V, 0,9 A máx. por puerto |

Con varios adaptadores seriales y periféricos a la vez, lo razonable es tener **conectada la fuente del hub** para no depender solo del bus de la PC.

## Adaptadores USB-TTL (serial)

Son conversores **USB - UART TTL** para entrar por consola serial a routers y DUTs. Los nombres estables bajo `/dev/` (symlinks por equipo) y las reglas **udev** están documentados en [host-config, sección Udev](host-config.md#7-reglas-udev-para-adaptadores-seriales).

### CH340

<img src="../img/hardware/usb-ttl-ch340.png" alt="Adaptador USB-TTL con chip CH340" width="260" style="max-width:100%;height:auto;display:block;" loading="lazy" />

Diseño habitual con chip **CH340**; suele ser el más económico. El nivel lógico depende del cable o placa (**3,3 V** o **5 V**). Formato típico: dongle con USB a un lado y pinera o conector a la placa.

### FTDI FT232RNL (familia FT232)

<img src="../img/hardware/usb-ttl-Ft232rnl.png" alt="Adaptador USB-TTL FT232RNL" width="260" style="max-width:100%;height:auto;display:block;" loading="lazy" />

Variante con interfaz **FTDI** (en la foto, línea **FT232RNL**). En Linux suele ir bien con los drivers del kernel y resulta cómodo cuando hace falta estabilidad o compatibilidad con herramientas que reconocen bien FTDI.

## Otros componentes (enlaces)

El resto del lab (red, host, tests, CI) sigue descrito en las páginas dedicadas:

| Componente | Documentación |
|------------|---------------|
| Host de orquestación | [host-config.md](host-config.md) |
| Switch gestión / PoE | [switch-config.md](switch-config.md) |
| Gateway | [gateway.md](gateway.md) |
| DUTs (estado, puertos) | [duts-config.md](duts-config.md) |
| TFTP / dnsmasq | [tftp-server.md](tftp-server.md) |
| Ansible / Labgrid | [ansible-labgrid.md](ansible-labgrid.md) |
| CI self-hosted runner | [ci-runner.md](ci-runner.md) |

Se puede ir ampliando este catálogo con más fotos o fichas cuando entre hardware nuevo que valga la pena documentar aquí.
