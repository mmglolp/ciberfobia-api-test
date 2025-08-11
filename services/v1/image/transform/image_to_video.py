import os
import subprocess
import logging
from services.file_management import download_file
from PIL import Image

STORAGE_PATH = "/tmp/"
logger = logging.getLogger(__name__)

def process_image_to_video(image_url, length, frame_rate, zoom_speed, job_id, webhook_url=None, output_format="reels"):
    """
    Procesa una imagen para convertirla en video con zoom
    :param image_url: URL de la imagen
    :param length: Duración del video en segundos
    :param frame_rate: Cuadros por segundo
    :param zoom_speed: Velocidad de zoom (0 para sin zoom)
    :param job_id: ID único para el trabajo
    :param webhook_url: URL para notificación (opcional)
    :param output_format: Formato de salida (reels, square, landscape)
    """
    try:
        # Descargar la imagen
        image_path = download_file(image_url, STORAGE_PATH)
        logger.info(f"Descargada imagen en {image_path}")

        # Obtener dimensiones de la imagen
        with Image.open(image_path) as img:
            width, height = img.size
        logger.info(f"Dimensiones originales: {width}x{height}")

        # Ruta de salida
        output_path = os.path.join(STORAGE_PATH, f"{job_id}.mp4")

        # Configuración de formatos (compatible con solicitudes antiguas)
        format_settings = {
            "square": {
                "intermediate": "2880:2880",
                "output": "720x720"
            },
            "reels": {
                "intermediate": "4320:7680",
                "output": "1080x1920"
            },
            "landscape": {
                "intermediate": "7680:4320",
                "output": "1920x1080"
            }
        }

        # Compatibilidad con versiones anteriores
        if output_format == "auto":
            # Comportamiento original basado en orientación
            if width > height:
                settings = format_settings["landscape"]
            else:
                settings = format_settings["reels"]
        else:
            # Usar formato solicitado (valor por defecto es "reels")
            settings = format_settings.get(output_format, format_settings["reels"])
        
        intermediate_size = settings["intermediate"]
        output_dims = settings["output"]

        # Calcular frames y factor de zoom
        total_frames = int(length * frame_rate)
        zoom_factor = 1 + (zoom_speed * length)

        logger.info(f"Formato: {output_format}, Tamaño intermedio: {intermediate_size}, Salida: {output_dims}")
        logger.info(f"Duración: {length}s, FPS: {frame_rate}, Total frames: {total_frames}")
        logger.info(f"Zoom: {zoom_speed}/s, Factor final: {zoom_factor}")

        # Comando FFmpeg optimizado
        cmd = [
            'ffmpeg',
            '-framerate', str(frame_rate),
            '-loop', '1',
            '-i', image_path,
            '-vf',
            # Procesamiento en dos etapas
            f"scale={intermediate_size}:force_original_aspect_ratio=cover,crop={intermediate_size}," +
            f"zoompan=z='min(1+({zoom_speed}*{length})*on/{total_frames},{zoom_factor})':d={total_frames}" +
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={output_dims}",
            '-c:v', 'libx264',
            '-t', str(length),
            '-pix_fmt', 'yuv420p',
            output_path
        ]

        logger.info(f"Ejecutando comando FFmpeg: {' '.join(cmd)}")

        # Ejecutar FFmpeg
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Error en FFmpeg: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)

        logger.info(f"Video creado exitosamente: {output_path}")

        # Limpiar archivo temporal
        os.remove(image_path)

        return output_path
    except Exception as e:
        logger.error(f"Error en process_image_to_video: {str(e)}", exc_info=True)
        raise
