#!/usr/bin/env python3
"""
NetCDF Commander - Papiweb Desarrollos Informáticos
Script para manejo de archivos NetCDF (.nc) con interfaz tipo Norton Commander
Compatible con grupos de trabajo Windows y completamente configurable
Interfaz de usuario con paneles duales y navegación por teclado

Desarrollado por: Papiweb Desarrollos Informáticos
Version: 1.0.0
Copyright (c) 2025 Papiweb Desarrollos Informáticos
Email: mgenialive@gmail.com
Website: https://www.papiweb-desarrollos.github.io/papiweb

Beccar, Buenos Aires, Argentina
"""

import os
import sys
import json
import curses
import threading
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime
import signal

try:
    import os
    import sys
    import json
    import signal
    import curses
    import threading
    import netCDF4 as nc
    import numpy as np
    import pandas as pd
except ImportError as e:
    print(f"Error: Faltan dependencias requeridas. Instala con:")
    print("pip install netCDF4 numpy pandas")
    sys.exit(1)

class NetCDFConfig:
    """Clase para manejar la configuración del script"""
    
    def __init__(self, config_file: str = "nc_config.json"):
        self.config_file = config_file
        self.default_config = {
            "app_info": {
                "name": "NetCDF Commander",
                "version": "1.0.0",
                "developer": "Papiweb Desarrollos Informáticos",
                "website": "https://www.papiweb-desarrollos.github.io/papiweb",
                "email": "mgenialive@gmail.com",
                "location": "Beccar, Buenos Aires, Argentina"
            },
            "windows_mount_point": "/mnt/shared",
            "output_formats": ["csv", "json", "txt"],
            "default_output_format": "csv",
            "log_level": "INFO",
            "log_file": "nc_handler.log",
            "compression": True,
            "encoding": "utf-8",
            "date_format": "%Y-%m-%d %H:%M:%S",
            "windows_paths": {
                "shared_folder": "//server/shared",
                "mount_command": "sudo mount -t cifs //server/shared /mnt/shared -o username=user,password=pass"
            },
            "interface": {
                "show_hidden": False,
                "sort_by": "name",
                "panel_width": 40,
                "preview_enabled": True,
                "show_splash": True
            }
        }
        self.config = self.load_config()
    
    def load_config(self) -> Dict:
        """Carga la configuración desde archivo JSON"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                merged_config = self.default_config.copy()
                merged_config.update(config)
                return merged_config
            except Exception:
                return self.default_config
        else:
            self.save_config(self.default_config)
            return self.default_config
    
    def save_config(self, config: Dict = None) -> None:
        """Guarda la configuración en archivo JSON"""
        config = config or self.config
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

class FileItem:
    """Representa un elemento del sistema de archivos"""
    def __init__(self, path: str, name: str = None):
        self.path = path
        self.name = name or os.path.basename(path)
        self.is_dir = os.path.isdir(path)
        self.is_nc = path.lower().endswith('.nc') if not self.is_dir else False
        self.size = self._get_size()
        self.modified = self._get_modified()
    
    def _get_size(self) -> int:
        try:
            return os.path.getsize(self.path) if not self.is_dir else 0
        except:
            return 0
    
    def _get_modified(self) -> str:
        try:
            timestamp = os.path.getmtime(self.path)
            return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")
        except:
            return "N/A"
    
    def format_size(self) -> str:
        """Formatea el tamaño del archivo"""
        if self.is_dir:
            return "<DIR>"
        
        size = self.size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"

class Panel:
    """Panel de archivos estilo Norton Commander"""
    def __init__(self, x: int, y: int, width: int, height: int, path: str = None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.current_path = path or os.getcwd()
        self.items: List[FileItem] = []
        self.selected_index = 0
        self.scroll_offset = 0
        self.is_active = False
        self.refresh_items()
    
    def refresh_items(self):
        """Actualiza la lista de archivos del directorio actual"""
        try:
            self.items = []
            
            # Añadir directorio padre si no estamos en root
            if self.current_path != '/':
                parent_path = os.path.dirname(self.current_path)
                self.items.append(FileItem(parent_path, ".."))
            
            # Listar archivos y directorios
            try:
                entries = os.listdir(self.current_path)
                entries.sort()
                
                # Primero directorios, luego archivos
                dirs = []
                files = []
                
                for entry in entries:
                    if entry.startswith('.'):
                        continue  # Omitir archivos ocultos por ahora
                    
                    full_path = os.path.join(self.current_path, entry)
                    item = FileItem(full_path, entry)
                    
                    if item.is_dir:
                        dirs.append(item)
                    else:
                        files.append(item)
                
                self.items.extend(dirs)
                self.items.extend(files)
                
            except PermissionError:
                pass
            
            # Ajustar índice seleccionado
            if self.selected_index >= len(self.items):
                self.selected_index = max(0, len(self.items) - 1)
                
        except Exception:
            self.items = []
    
    def navigate_to(self, path: str):
        """Navega a un directorio específico"""
        if os.path.isdir(path):
            self.current_path = os.path.abspath(path)
            self.selected_index = 0
            self.scroll_offset = 0
            self.refresh_items()
    
    def get_selected_item(self) -> Optional[FileItem]:
        """Obtiene el elemento seleccionado actualmente"""
        if 0 <= self.selected_index < len(self.items):
            return self.items[self.selected_index]
        return None
    
    def move_up(self):
        """Mueve la selección hacia arriba"""
        if self.selected_index > 0:
            self.selected_index -= 1
            if self.selected_index < self.scroll_offset:
                self.scroll_offset = self.selected_index
    
    def move_down(self):
        """Mueve la selección hacia abajo"""
        if self.selected_index < len(self.items) - 1:
            self.selected_index += 1
            visible_items = self.height - 3  # Espacio para bordes y header
            if self.selected_index >= self.scroll_offset + visible_items:
                self.scroll_offset = self.selected_index - visible_items + 1
    
    def enter_selected(self):
        """Entra en el directorio seleccionado o devuelve archivo"""
        selected = self.get_selected_item()
        if selected:
            if selected.is_dir:
                self.navigate_to(selected.path)
                return None
            else:
                return selected
        return None

class NCPreview:
    """Panel de vista previa para archivos NetCDF"""
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.current_file = None
        self.nc_info = {}
    
    def analyze_file(self, file_path: str):
        """Analiza un archivo NetCDF y guarda la información"""
        if not file_path.lower().endswith('.nc'):
            self.nc_info = {}
            self.current_file = file_path
            return
        
        try:
            with nc.Dataset(file_path, 'r') as dataset:
                self.nc_info = {
                    "dimensions": dict(dataset.dimensions.items()),
                    "variables": list(dataset.variables.keys())[:10],  # Primeras 10
                    "global_attrs": dict(list(dataset.__dict__.items())[:5]),  # Primeros 5
                    "file_size": os.path.getsize(file_path)
                }
                self.current_file = file_path
        except Exception:
            self.nc_info = {"error": "No se pudo leer el archivo NetCDF"}
            self.current_file = file_path

class StatusBar:
    """Barra de estado inferior"""
    def __init__(self, x: int, y: int, width: int):
        self.x = x
        self.y = y
        self.width = width
        self.message = "Listo"
        self.help_text = "F1:Ayuda F2:Analizar F3:Extraer F4:Exportar F10:Salir"
    
    def set_message(self, message: str):
        """Establece el mensaje de estado"""
        self.message = message[:self.width - 20]  # Truncar si es muy largo

class NCInterface:
    """Interfaz principal tipo Norton Commander"""
    
    def __init__(self, config: NetCDFConfig):
        self.config = config
        self.screen = None
        self.running = True
        
        # Componentes de la interfaz
        self.left_panel = None
        self.right_panel = None
        self.preview_panel = None
        self.status_bar = None
        self.active_panel = 'left'
        
        # Estado de la aplicación
        self.mount_status = False
        self.last_operation = ""
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Maneja señales del sistema"""
        self.running = False
        if self.screen:
            curses.endwin()
        sys.exit(0)
    
    def init_colors(self):
        """Inicializa los colores de la interfaz"""
        curses.start_color()
        curses.use_default_colors()
        
        # Definir pares de colores
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)    # Panel activo
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)    # Panel inactivo
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLUE)   # Archivo seleccionado
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Archivo NC
        curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)     # Error
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Normal
        curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_WHITE)   # Barra de estado
        curses.init_pair(8, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Directorio
        curses.init_pair(9, curses.COLOR_CYAN, curses.COLOR_BLUE)     # Branding
        curses.init_pair(10, curses.COLOR_YELLOW, curses.COLOR_BLUE)  # Título
    
    def setup_panels(self):
        """Configura los paneles de la interfaz"""
        height, width = self.screen.getmaxyx()
        
        # Panel izquierdo
        panel_width = width // 3
        self.left_panel = Panel(0, 1, panel_width, height - 3)
        self.left_panel.is_active = True
        
        # Panel derecho
        self.right_panel = Panel(panel_width + 1, 1, panel_width, height - 3, 
                               self.config.config.get('windows_mount_point', '/tmp'))
        
        # Panel de vista previa
        preview_width = width - (2 * panel_width) - 2
        self.preview_panel = NCPreview(2 * panel_width + 2, 1, preview_width, height - 3)
        
        # Barra de estado
        self.status_bar = StatusBar(0, height - 1, width)
    
    def draw_panel_border(self, panel: Panel, title: str):
        """Dibuja el borde y título de un panel"""
        color = curses.color_pair(1) if panel.is_active else curses.color_pair(2)
        
        # Borde superior
        self.screen.addstr(panel.y - 1, panel.x, "┌" + "─" * (panel.width - 2) + "┐", color)
        
        # Título
        title_text = f" {title} "
        title_x = panel.x + (panel.width - len(title_text)) // 2
        self.screen.addstr(panel.y - 1, title_x, title_text, color | curses.A_BOLD)
        
        # Bordes laterales
        for i in range(panel.height - 2):
            self.screen.addstr(panel.y + i, panel.x, "│", color)
            self.screen.addstr(panel.y + i, panel.x + panel.width - 1, "│", color)
        
        # Borde inferior
        self.screen.addstr(panel.y + panel.height - 2, panel.x, 
                         "└" + "─" * (panel.width - 2) + "┘", color)
    
    def draw_panel_content(self, panel: Panel):
        """Dibuja el contenido de un panel"""
        visible_items = panel.height - 3
        
        for i in range(visible_items):
            item_index = panel.scroll_offset + i
            y_pos = panel.y + i
            
            if item_index >= len(panel.items):
                break
            
            item = panel.items[item_index]
            is_selected = (item_index == panel.selected_index) and panel.is_active
            
            # Determinar color
            if is_selected:
                color = curses.color_pair(3) | curses.A_REVERSE
            elif item.is_dir:
                color = curses.color_pair(8)
            elif item.is_nc:
                color = curses.color_pair(4)
            else:
                color = curses.color_pair(6)
            
            # Formatear texto del item
            name = item.name[:panel.width - 15]  # Truncar si es muy largo
            size = item.format_size()
            
            # Rellenar línea
            line = f" {name:<{panel.width-12}} {size:>8} "
            line = line[:panel.width - 2]
            line = line.ljust(panel.width - 2)
            
            try:
                self.screen.addstr(y_pos, panel.x + 1, line, color)
            except curses.error:
                pass  # Ignorar errores de dibujo en los bordes
    
    def draw_preview(self):
        """Dibuja el panel de vista previa"""
        # Borde del panel de vista previa
        color = curses.color_pair(2)
        
        # Borde superior
        self.screen.addstr(self.preview_panel.y - 1, self.preview_panel.x, 
                         "┌" + "─" * (self.preview_panel.width - 2) + "┐", color)
        
        # Título
        title = " Vista Previa "
        title_x = self.preview_panel.x + (self.preview_panel.width - len(title)) // 2
        self.screen.addstr(self.preview_panel.y - 1, title_x, title, color | curses.A_BOLD)
        
        # Bordes laterales
        for i in range(self.preview_panel.height - 2):
            self.screen.addstr(self.preview_panel.y + i, self.preview_panel.x, "│", color)
            self.screen.addstr(self.preview_panel.y + i, 
                             self.preview_panel.x + self.preview_panel.width - 1, "│", color)
        
        # Borde inferior
        self.screen.addstr(self.preview_panel.y + self.preview_panel.height - 2, 
                         self.preview_panel.x, 
                         "└" + "─" * (self.preview_panel.width - 2) + "┘", color)
        
        # Contenido de la vista previa
        self.draw_preview_content()
    
    def draw_preview_content(self):
        """Dibuja el contenido de la vista previa"""
        if not self.preview_panel.nc_info:
            return
        
        y_offset = 0
        max_lines = self.preview_panel.height - 3
        
        if "error" in self.preview_panel.nc_info:
            self.screen.addstr(self.preview_panel.y + y_offset, 
                             self.preview_panel.x + 1, 
                             "Error al leer archivo", 
                             curses.color_pair(5))
            return
        
        info = self.preview_panel.nc_info
        lines = []
        
        # Información del archivo
        if "file_size" in info:
            size = info["file_size"]
            size_str = f"{size/1024/1024:.1f} MB" if size > 1024*1024 else f"{size/1024:.1f} KB"
            lines.append(f"Tamaño: {size_str}")
        
        # Dimensiones
        if "dimensions" in info:
            lines.append("Dimensiones:")
            for name, dim in list(info["dimensions"].items())[:5]:
                size_info = f"({len(dim)} elementos)" if hasattr(dim, '__len__') else f"({dim})"
                lines.append(f"  {name}: {size_info}")
        
        # Variables
        if "variables" in info:
            lines.append("Variables:")
            for var in info["variables"]:
                lines.append(f"  {var}")
        
        # Atributos globales
        if "global_attrs" in info:
            lines.append("Atributos:")
            for key, value in info["global_attrs"].items():
                value_str = str(value)[:30] + "..." if len(str(value)) > 30 else str(value)
                lines.append(f"  {key}: {value_str}")
        
        # Dibujar líneas
        for i, line in enumerate(lines[:max_lines]):
            try:
                self.screen.addstr(self.preview_panel.y + i, 
                                 self.preview_panel.x + 1, 
                                 line[:self.preview_panel.width - 3], 
                                 curses.color_pair(6))
            except curses.error:
                pass
    
    def draw_header(self):
        """Dibuja el header con branding de Papiweb"""
        height, width = self.screen.getmaxyx()
        
        # Limpiar línea superior
        self.screen.addstr(0, 0, " " * width, curses.color_pair(1))
        
        # Título principal
        app_info = self.config.config.get("app_info", {})
        title = f"NetCDF Commander v{app_info.get('version', '1.0.0')}"
        branding = f"by {app_info.get('developer', 'Papiweb Desarrollos Informáticos')}"
        
        # Centrar título
        title_x = (width - len(title)) // 2
        self.screen.addstr(0, title_x, title, curses.color_pair(10) | curses.A_BOLD)
        
        # Branding a la derecha
        branding_x = width - len(branding) - 1
        if branding_x > title_x + len(title) + 2:
            self.screen.addstr(0, branding_x, branding, curses.color_pair(9))
    
    def show_splash_screen(self):
        """Muestra pantalla de bienvenida con branding"""
        if not self.config.config.get("interface", {}).get("show_splash", True):
            return
        
        height, width = self.screen.getmaxyx()
        
        # Crear ventana de splash
        splash_height = 20
        splash_width = 70
        splash_y = (height - splash_height) // 2
        splash_x = (width - splash_width) // 2
        
        splash_win = curses.newwin(splash_height, splash_width, splash_y, splash_x)
        splash_win.box('║', '═')
        
        # Arte ASCII del logo
        logo_lines = [
            "  ╔══════════════════════════════════════════════════════════════╗",
            "  ║                                                              ║",
            "  ║    ██████   █████  ██████  ██ ██     ██ ███████ ██████       ║",
            "  ║    ██   ██ ██   ██ ██   ██ ██ ██     ██ ██      ██   ██      ║",
            "  ║    ██████  ███████ ██████  ██ ██  █  ██ █████   ██████       ║",
            "  ║    ██      ██   ██ ██      ██ ██ ███ ██ ██      ██   ██      ║",
            "  ║    ██      ██   ██ ██      ██  ███ ███  ███████ ██████       ║",
            "  ║                                                              ║",
            "  ║            DESARROLLOS INFORMÁTICOS                         ║",
            "  ║                                                              ║",
            "  ╚══════════════════════════════════════════════════════════════╝"
        ]
        
        app_info = self.config.config.get("app_info", {})
        info_lines = [
            "",
            f"         🔬 NetCDF Commander v{app_info.get('version', '1.0.0')} 🔬",
            "",
            "    🚀 Manejador Avanzado de Archivos Científicos NetCDF",
            "    💻 Interfaz Tipo Norton Commander",
            "    🌐 Compatible con Recursos Compartidos Windows",
            "",
            f"    📧 {app_info.get('email', 'mgenialive@gmail.com')}",
            f"    🌍 {app_info.get('website', 'https://www.papiweb-desarrollos.github.io/papiweb.com')}",
            f"    📍 {app_info.get('location', 'Beccar, Buenos Aires, Argentina')}",
            "",
            "    ⚡ Cargando interfaz... Presiona cualquier tecla ⚡"
        ]
        
        # Dibujar logo
        start_y = 1
        for i, line in enumerate(logo_lines[:min(len(logo_lines), splash_height-2)]):
            if start_y + i < splash_height - 1:
                splash_win.addstr(start_y + i, 2, line[:splash_width-4], 
                                curses.color_pair(9) | curses.A_BOLD)
        
        # Dibujar información
        info_start_y = len(logo_lines) + 2
        for i, line in enumerate(info_lines):
            if info_start_y + i < splash_height - 1:
                # Centrar texto
                text_x = (splash_width - len(line)) // 2
                if "🔬" in line or "🚀" in line:
                    splash_win.addstr(info_start_y + i, text_x, line[:splash_width-4], 
                                    curses.color_pair(10) | curses.A_BOLD)
                elif "📧" in line or "🌍" in line or "📍" in line:
                    splash_win.addstr(info_start_y + i, text_x, line[:splash_width-4], 
                                    curses.color_pair(9))
                elif "⚡" in line:
                    splash_win.addstr(info_start_y + i, text_x, line[:splash_width-4], 
                                    curses.color_pair(3) | curses.A_BLINK)
                else:
                    splash_win.addstr(info_start_y + i, text_x, line[:splash_width-4], 
                                    curses.color_pair(6))
        
        splash_win.refresh()
        
        # Esperar tecla con timeout
        splash_win.timeout(3000)  # 3 segundos
        key = splash_win.getch()
        
        splash_win.clear()
        splash_win.refresh()
        del splash_win
        """Dibuja la barra de estado"""
        height, width = self.screen.getmaxyx()
        
        # Limpiar barra de estado
        self.screen.addstr(height - 2, 0, " " * width, curses.color_pair(7))
        self.screen.addstr(height - 1, 0, " " * width, curses.color_pair(7))
        
        # Información del panel activo
        active_panel = self.left_panel if self.active_panel == 'left' else self.right_panel
        path_info = f" {active_panel.current_path} "
        
        # Información de montaje
        mount_info = " [MONTADO] " if self.mount_status else " [NO MONTADO] "
        mount_color = curses.color_pair(4) if self.mount_status else curses.color_pair(5)
        
        try:
            self.screen.addstr(height - 2, 0, path_info, curses.color_pair(7))
            self.screen.addstr(height - 2, len(path_info), mount_info, mount_color)
            
            # Branding en barra de estado
            papiweb_text = "© Papiweb Desarrollos"
            papiweb_x = width - len(papiweb_text) - len(self.status_bar.message) - 3
            if papiweb_x > len(path_info) + len(mount_info) + 2:
                self.screen.addstr(height - 2, papiweb_x, papiweb_text, 
                                 curses.color_pair(9))
            
            self.screen.addstr(height - 2, width - len(self.status_bar.message) - 1, 
                             self.status_bar.message, curses.color_pair(7))
            
            # Teclas de ayuda con branding
            help_with_branding = f"{self.status_bar.help_text} | Papiweb Dev"
            self.screen.addstr(height - 1, 0, help_with_branding[:width-1], 
                             curses.color_pair(7))
        except curses.error:
            pass
    
    def update_preview(self):
        """Actualiza la vista previa basada en el archivo seleccionado"""
        active_panel = self.left_panel if self.active_panel == 'left' else self.right_panel
        selected = active_panel.get_selected_item()
        
        if selected and not selected.is_dir and selected.is_nc:
            self.preview_panel.analyze_file(selected.path)
        else:
            self.preview_panel.nc_info = {}
    
    def handle_f2_analyze(self):
        """Maneja F2 - Analizar archivo NetCDF"""
        active_panel = self.left_panel if self.active_panel == 'left' else self.right_panel
        selected = active_panel.get_selected_item()
        
        if not selected or not selected.is_nc:
            self.status_bar.set_message("Selecciona un archivo .nc para analizar")
            return
        
        self.status_bar.set_message("Analizando archivo...")
        self.screen.refresh()
        
        # Analizar en un hilo separado para no bloquear la UI
        def analyze_thread():
            try:
                # Aquí iría la lógica de análisis completo
                self.status_bar.set_message(f"Archivo analizado: {selected.name}")
            except Exception as e:
                self.status_bar.set_message(f"Error: {str(e)}")
        
        thread = threading.Thread(target=analyze_thread)
        thread.daemon = True
        thread.start()
    
    def handle_f4_export(self):
        """Maneja F4 - Exportar datos"""
        active_panel = self.left_panel if self.active_panel == 'left' else self.right_panel
        selected = active_panel.get_selected_item()
        
        if not selected or not selected.is_nc:
            self.status_bar.set_message("Selecciona un archivo .nc para exportar")
            return
        
        # Aquí iría un diálogo para seleccionar formato y destino
        self.status_bar.set_message("Exportando... (implementar diálogo)")
    
    def handle_f5_mount(self):
        """Maneja F5 - Montar/desmontar recurso Windows"""
        if self.mount_status:
            # Desmontar
            try:
                result = os.system(f"sudo umount {self.config.config['windows_mount_point']}")
                if result == 0:
                    self.mount_status = False
                    self.status_bar.set_message("Recurso desmontado")
                else:
                    self.status_bar.set_message("Error desmontando recurso")
            except:
                self.status_bar.set_message("Error desmontando recurso")
        else:
            # Montar
            self.status_bar.set_message("Montando recurso Windows...")
            # Aquí iría la lógica de montaje
            self.mount_status = True  # Simulado por ahora
    
    def run(self):
        """Ejecuta la interfaz principal"""
        self.screen = curses.initscr()
        
        try:
            # Configuración inicial de curses
            curses.noecho()
            curses.cbreak()
            curses.curs_set(0)  # Ocultar cursor
            self.screen.keypad(True)
            
            self.init_colors()
            self.setup_panels()
            
            # Mostrar pantalla de bienvenida
            self.show_splash_screen()
            
            # Bucle principal
            while self.running:
                # Limpiar pantalla
                self.screen.clear()
                
                # Dibujar header con branding
                self.draw_header()
                
                # Dibujar componentes
                self.draw_panel_border(self.left_panel, f"Panel Izq - {os.path.basename(self.left_panel.current_path)}")
                self.draw_panel_content(self.left_panel)
                
                self.draw_panel_border(self.right_panel, f"Panel Der - {os.path.basename(self.right_panel.current_path)}")
                self.draw_panel_content(self.right_panel)
                
                self.draw_preview()
                self.draw_status_bar()
                
                # Actualizar pantalla
                self.screen.refresh()
                
                # Procesar input
                key = self.screen.getch()
                
                # Navegación
                if key == curses.KEY_UP:
                    active_panel = self.left_panel if self.active_panel == 'left' else self.right_panel
                    active_panel.move_up()
                    self.update_preview()
                    
                elif key == curses.KEY_DOWN:
                    active_panel = self.left_panel if self.active_panel == 'left' else self.right_panel
                    active_panel.move_down()
                    self.update_preview()
                    
                elif key == ord('\t') or key == curses.KEY_RIGHT:
                    # Cambiar panel activo
                    if self.active_panel == 'left':
                        self.active_panel = 'right'
                        self.left_panel.is_active = False
                        self.right_panel.is_active = True
                    else:
                        self.active_panel = 'left'
                        self.right_panel.is_active = False
                        self.left_panel.is_active = True
                    self.update_preview()
                    
                elif key == curses.KEY_LEFT:
                    # Cambiar panel activo (izquierda)
                    self.active_panel = 'left'
                    self.left_panel.is_active = True
                    self.right_panel.is_active = False
                    self.update_preview()
                    
                elif key == ord('\n') or key == curses.KEY_ENTER:
                    # Entrar en directorio o seleccionar archivo
                    active_panel = self.left_panel if self.active_panel == 'left' else self.right_panel
                    result = active_panel.enter_selected()
                    if result and result.is_nc:
                        self.status_bar.set_message(f"Archivo NC seleccionado: {result.name}")
                    self.update_preview()
                
                # Teclas de función
                elif key == curses.KEY_F1:
                    self.show_help()
                elif key == curses.KEY_F2:
                    self.handle_f2_analyze()
                elif key == curses.KEY_F4:
                    self.handle_f4_export()
                elif key == curses.KEY_F5:
                    self.handle_f5_mount()
                elif key == curses.KEY_F10 or key == ord('q'):
                    self.running = False
                
                # Tecla ESC
                elif key == 27:
                    self.running = False
        
        finally:
            # Limpiar curses
            curses.endwin()
    
    def show_help(self):
        """Muestra la ventana de ayuda con branding"""
        height, width = self.screen.getmaxyx()
        
        # Crear ventana de ayuda
        help_height = 22
        help_width = 70
        help_y = (height - help_height) // 2
        help_x = (width - help_width) // 2
        
        help_win = curses.newwin(help_height, help_width, help_y, help_x)
        help_win.box('║', '═')
        
        app_info = self.config.config.get("app_info", {})
        
        help_lines = [
            f" {app_info.get('name', 'NetCDF Commander')} - AYUDA ",
            f" {app_info.get('developer', 'Papiweb Desarrollos Informáticos')} ",
            "═" * 66,
            "",
            "🎯 NAVEGACIÓN:",
            "  ↑/↓        - Mover selección en panel activo",
            "  ←/→/Tab    - Cambiar entre paneles",
            "  Enter      - Entrar en directorio o seleccionar archivo",
            "",
            "⚡ TECLAS DE FUNCIÓN:",
            "  F1         - Mostrar esta ayuda",
            "  F2         - Analizar archivo NetCDF seleccionado",
            "  F3         - Ver detalles del archivo",
            "  F4         - Exportar datos a CSV/JSON/TXT",
            "  F5         - Montar/desmontar recurso Windows",
            "  F6         - Copiar archivo entre paneles",
            "  F9         - Configuración del sistema",
            "  F10/Q/Esc  - Salir de la aplicación",
            "",
            "📊 FUNCIONES NetCDF:",
            "  • Vista previa automática de metadatos",
            "  • Análisis de dimensiones y variables",
            "  • Exportación a múltiples formatos",
            "",
            f"📧 Soporte: {app_info.get('email', 'info@papiweb.com.ar')}",
            f"🌍 Web: {app_info.get('website', 'www.papiweb.com.ar')}",
            "",
            "        ⌨️  Presiona cualquier tecla para continuar  ⌨️"
        ]
        
        for i, line in enumerate(help_lines):
            if i < help_height - 2:
                if i == 0:  # Título
                    text_x = (help_width - len(line)) // 2
                    help_win.addstr(i + 1, text_x, line[:help_width - 4], 
                                  curses.color_pair(10) | curses.A_BOLD)
                elif i == 1:  # Desarrollador
                    text_x = (help_width - len(line)) // 2
                    help_win.addstr(i + 1, text_x, line[:help_width - 4], 
                                  curses.color_pair(9))
                elif "🎯" in line or "⚡" in line or "📊" in line:
                    help_win.addstr(i + 1, 2, line[:help_width - 4], 
                                  curses.color_pair(4) | curses.A_BOLD)
                elif "📧" in line or "🌍" in line:
                    help_win.addstr(i + 1, 2, line[:help_width - 4], 
                                  curses.color_pair(9))
                elif "⌨️" in line:
                    text_x = (help_width - len(line)) // 2
                    help_win.addstr(i + 1, text_x, line[:help_width - 4], 
                                  curses.color_pair(3) | curses.A_BLINK)
                else:
                    help_win.addstr(i + 1, 2, line[:help_width - 4], 
                                  curses.color_pair(6))
        
        help_win.refresh()
        help_win.getch()  # Esperar tecla
        help_win.clear()
        help_win.refresh()

def main():
    """Función principal - Papiweb Desarrollos Informáticos"""
    try:
        # Mostrar información del desarrollador al inicio
        print("╔══════════════════════════════════════════════════════════════╗")
        print("║                  PAPIWEB DESARROLLOS INFORMÁTICOS            ║")
        print("║                                                              ║")
        print("║              🔬 NetCDF Commander v1.0.0 🔬                   ║")
        print("║        Manejador Avanzado de Archivos Científicos           ║")
        print("║                                                              ║")
        print("║    📧 mgenialive@gmail.com                                   ║")
        print("║    🌍 https://www.papiweb-desarrollos.github.io/papiweb      ║")
        print("║    📍 Beccar, Buenos Aires, Argentina                       ║")
        print("║                                                              ║")
        print("║           Iniciando interfaz Norton Commander...            ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        print()
        
        config = NetCDFConfig()
        interface = NCInterface(config)
        interface.run()
        
        # Mensaje de despedida
        print("\n╔══════════════════════════════════════════════════════════════╗")
        print("║        Gracias por usar NetCDF Commander                    ║")
        print("║              by Papiweb Desarrollos Informáticos            ║")
        print("║                                                              ║")
        print("║    Para soporte técnico: mgenialive@gmail.com                ║")
        print("╚══════════════════════════════════════════════════════════════╝")
        
    except KeyboardInterrupt:
        print("\n\n🚫 Operación cancelada por el usuario")
        print("👋 ¡Hasta la próxima! - Papiweb Desarrollos")
    except Exception as e:
        if 'interface' in locals():
            curses.endwin()
        print(f"\n❌ Error crítico: {e}")
        print("📧 Reporta este error a: mgenialive@gmail.com")
        print("🔧 Papiweb Desarrollos Informáticos - Soporte Técnico")
        sys.exit(1)

if __name__ == "__main__":
    main()