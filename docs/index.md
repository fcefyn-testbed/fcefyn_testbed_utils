# Documentación del Banco de pruebas HIL de la FCEFyN

Bienvenido! :wave: 

Esta es la documentación del repositorio [fcefyn_testbed_utils](https://github.com/ccasanueva7/fcefyn_testbed_utils) donde se encuentran centralizados los componentes que dan soporte al **banco de pruebas Hardware in-the-loop** para [OpenWrt](https://openwrt.org/) y [LibreMesh](https://libremesh.org/) de la [Facultad de Ciencias Exactas, 
Físicas y Naturales](https://fcefyn.unc.edu.ar/) de la [Universidad Nacional de Córdoba](https://www.unc.edu.ar/).

Aquí podras encontrar información sobre:

* Operación el laboratorio
* Diseño e infraestrctura 
* Componentes de hardware y software junto con sus configuraciones 
* Topología de red
* Integraciones con las suites e infraestructura de pruebas de [openwrt-tests](https://github.com/aparcar/openwrt-tests) y su fork [libremesh-tests](https://github.com/francoriba/libremesh-tests)

---

## :point_up: Antes de empezar.. 

Antes de avanzar a las diversas secciones, conviene tener claro **para qué existe** este banco de pruebas y que necesidades busca cubrir. Esto se puede resumir en: 

- **Validar firmware** de routers basados en *OpenWrt* y *LibreMesh* de forma **automatizada y repetible**, usando el ecosistema [Labgrid](https://labgrid.readthedocs.io/en/latest/) + [pytest](https://docs.pytest.org/en/stable/), en la línea de *openwrt-tests* y *libremesh-tests*.
- **Cubrir targets físicos y emulados**: permitir pruebas sobre **dispositivos físicos** dispuestos en un rack mediante enlaces físicos y sobre instancias [QEMU](https://www.qemu.org/) aprovisionadas con enlances WiFi simulados mediante [vwifi](https://github.com/sysprog21/vwifi).
- **Operar un laboratorio compartido**: bajo distintos modos de trabajo, y brindando acceso remoto para los administradores.

---
Teniendo claro esto, pasemos a ver un diagrama general, de alto nivel de la estructura de nuestro banco de pruebas y sus componentes principales:

![Diagrama general del banco de pruebas y componentes principales](img/diagrams/general-design-overview.png)

Tener en mente este diagrama facilita en gran medida la lectura y comprensión de lo documentado.

## Todo listo! 

Dependiendo de lo que necesites saber sugerimos: 

| Si sos                   | Empezar por | Luego |
|--------------------------|-------------|-------|
| **Administrador del lab** | [Manual de operación](operar/SOM.md) | [Dashboard testbed-status](operar/testbed-status.md), [Rack cheatsheets](operar/rack-cheatsheets.md), [Agregar un DUT](operar/adding-dut-guide.md) |
| **Revisor/colaborador**  | [Propuesta lab híbrido](diseno/hybrid-lab-proposal.md) | [Tracking](diseno/hybrid-lab-tracking.md), [CI](diseno/ci-use-cases-proposal.md) |
| **Desarrollador (tests)** | [Enfoque de testing](tests/libremesh-testing-approach.md) | [Manual de operación](operar/SOM.md) para ejecutar |


---

## Secciones

- **[Operar el lab](operar/SOM.md)** - Procedimientos diarios, cambio de modos, power cycle, troubleshooting. TUI de estado: [testbed-status](operar/testbed-status.md).
- **[Configuración](configuracion/host-config.md)** - Detalle de cada componente: host, switch, gateway, DUTs, TFTP, Arduino, Ansible.
- **[Tests y desarrollo](tests/libremesh-testing-approach.md)** - Enfoque de testing, proxy SSH, catálogo de firmware CI, troubleshooting Labgrid.
- **[Diseño y propuestas](diseno/hybrid-lab-proposal.md)** - Propuestas técnicas, tracking de fases, CI, virtual mesh.
