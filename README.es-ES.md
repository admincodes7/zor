

# Zor

<div align="center">
  <img src="https://raw.githubusercontent.com/admincodes7/zor/refs/heads/master/assets/card.jpg" alt="Zor Logo" width="150" height="75" />
  <p><i>Una herramienta de código abierto similar a Claude Code</i></p>
  
  [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
  [![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
  [![PRs Welcome](https://img.shields.io/github/issues-pr/admincodes7/zor)](CONTRIBUTING.md)
  [![Build Status](https://github.com/admincodes7/zor/actions/workflows/python-package.yml/badge.svg)](https://github.com/admincodes7/zor/actions)
  [![PyPI Downloads](https://img.shields.io/pepy/dt/zor?cacheSeconds=3600)](https://pypi.org/project/zor)
  [![Stable Version](https://img.shields.io/pypi/v/zor?color=blue)](https://pypi.org/project/zor/)
</div>

## Descripción general

Zor es una poderosa herramienta de línea de comandos que lleva la asistencia de código impulsada por IA a tu terminal. Utilizando la API de Gemini, Zor te ayuda a comprender, modificar y mejorar tu base de código a través del lenguaje natural.

Piensa en ello como una alternativa de código abierto a herramientas como Claude Code: tu par programador con IA en la terminal.

## Características

- 🧠 **Comprensión contextual**: Zor analiza toda tu base de código para ofrecer asistencia informada
- 💬 **Modo interactivo**: Mantén conversaciones sobre tu código
- ✏️ **Editar archivos**: Realiza cambios utilizando instrucciones en lenguaje natural
- 🧪 **Generar pruebas**: Crea automáticamente pruebas para tu código
- 🔄 **Refactorizar código**: Implementa cambios complejos en múltiples archivos
- 🔧 **Integración con Git**: Realiza commits de cambios directamente desde Zor
- 🧠 **Creación de proyectos**: Crea nuevos proyectos con una descripción proporcionada

## Demostración rápida
[![Demo Video](https://raw.githubusercontent.com/admincodes7/zor/refs/heads/master/assets/coverpage.png)](https://youtu.be/mS0ONPNhMmU?si=efayT3KuuiqZtksH)

## Instalación

```bash
pip install zor
```

## Inicio rápido

1. **Configura tu clave API**:
   ```bash
   zor setup
   ```

2. **Consulta sobre tu código**:
   ```bash
   zor ask "How does the file reading in context.py work?"
   ```

3. **Inicia una sesión interactiva**:
   ```bash
   zor interactive
   ```
4. **Crea un nuevo proyecto con Zor**:
   ```bash
   zor init "create a modern React portfolio app for a software engineer with dark theme"
   ```

## Documentación

Para la documentación completa, visita nuestra [Documentación](docs/index.md).

## Ejemplos de uso

### Generar pruebas

```bash
zor generate_test zor/context.py
```

### Editar un archivo

```bash
zor edit zor/main.py "Add better error handling to the setup command"
```

### Refactorizar código

```bash
zor refactor "Improve error handling across the codebase by using custom exceptions"
```

## Contribuir

¡Las contribuciones son bienvenidas! Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para más detalles.

## Licencia

Zor está licenciado bajo la [Licencia MIT](LICENSE).

## Agradecimientos

- Gracias a todos los colaboradores que han ayudado a dar forma a este proyecto
- Inspirado por herramientas como Claude Code y GitHub Copilot
