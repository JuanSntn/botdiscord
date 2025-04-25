# 🎵 Bot de Música para Discord

Este es un bot de música para Discord con funcionalidades como reproducir canciones en alta calidad, manejar colas de reproducción, obtener letras de canciones desde Genius, y más.

## 🚀 Funcionalidades

- 🎶 Reproducción de música en alta calidad.  
- 📝 Sistema de colas.  
- 🔍 Búsqueda de letras integrada con Genius API.  
- ⏭ Salta canciones.  
- 📜 Muestra la cola de canciones.  
- ⏹ Comandos intuitivos con prefijo `!`  

## 🛠 Instalación

- Python 3.8+  
- FFmpeg ([Guía de instalación](https://www.youtube.com/watch?v=JR36oH35Fgg))  
- Tokens de API:  
  - [Token de Discord Bot](https://discord.com/developers/applications)  
  - [Token de Genius API](https://genius.com/api-clients) (opcional para comandos de letras)
    
## 📦 Requisitos

- Python 3.8 o superior  
- Una cuenta de Discord y un bot configurado  
- Token de Genius API para obtener letras (opcional)

## 📜 Comandos Disponibles

| Comando         | Descripción                                         | Ejemplo                                 |
|-----------------|-----------------------------------------------------|------------------------------------------|
| `!play [url]`   | Reproduce música o la añade a la cola               | `!play url, !play Molotov Frijolero`     |
| `!cola`         | Muestra la cola de reproducción actual              | `!cola`                                  |
| `!skip`         | Salta la canción actual                             | `!skip`                                  |
| `!stop`         | Detiene la música y limpia la cola                  | `!stop`                                  |
| `!letra`        | Muestra la letra de la canción actual               | `!letra`                                 |
| `!buscarletra`  | Busca letras por nombre de canción                  | `!buscarletra Bohemian Rhapsody`         |
| `!votar`        | Elige aleatoriamente entre opciones dadas           | `!votar pizza hamburguesa tacos`         |


## 🔧 Instalación

1. **Clonar el repositorio**

```bash
git clone https://github.com/tu-usuario/botdiscord.git
pip install -r requirements.txt
configurar .env con token de discord y Genius
python main.py
cd botdiscord
