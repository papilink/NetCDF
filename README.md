# NetCDF Commander

## 🔬 Sobre el Proyecto

NetCDF Commander es una aplicación de interfaz de usuario tipo Norton Commander especializada en el manejo de archivos NetCDF (.nc). Diseñada para facilitar la navegación, visualización y manipulación de archivos de datos científicos en formato NetCDF.

## ✨ Características

- Interfaz dual tipo Norton Commander
- Navegación intuitiva por teclado
- Vista previa de archivos NetCDF
- Compatible con grupos de trabajo Windows
- Exportación a múltiples formatos (CSV, JSON, TXT)
- Interfaz de usuario basada en curses
- Completamente configurable mediante JSON

## 🛠️ Requisitos

- Python 3.6+
- Bibliotecas requeridas:
  - netCDF4
  - numpy
  - pandas
  - curses

## 📦 Instalación

```bash
# Clonar el repositorio
git clone https://github.com/papilink/NetCDF.git

# Crear entorno virtual (recomendado)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate  # Windows

# Instalar dependencias
pip install netCDF4 numpy pandas
```

## 🚀 Uso

```bash
python nc_file_handler.py
```

### Teclas de Navegación

- F1: Ayuda
- F2: Analizar archivo NetCDF
- F3: Extraer datos
- F4: Exportar
- F5: Montar unidad de red
- F10: Salir
- ↑↓: Navegar archivos
- Enter: Abrir directorio/archivo
- Tab: Cambiar panel

## ⚙️ Configuración

El archivo `nc_config.json` permite personalizar varios aspectos de la aplicación:

- Puntos de montaje Windows
- Formatos de salida
- Nivel de logs
- Opciones de compresión
- Configuración de interfaz
- Y más...

## 👥 Desarrollado por

Papiweb Desarrollos Informáticos
- 📧 Email: mgenialive@gmail.com
- 🌐 Web: https://www.papiweb-desarrollos.github.io/papiweb
- 📍 Ubicación: Beccar, Buenos Aires, Argentina

## 📄 Licencia

Copyright (c) 2025 Papiweb Desarrollos Informáticos

Este proyecto está bajo licencia privada y todos los derechos están reservados.
