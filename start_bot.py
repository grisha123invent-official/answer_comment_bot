import subprocess
import sys
import time
import os

def run_bot():
    print("Запуск бота...")
    
    # Формируем команду для запуска бота
    cmd = [sys.executable, "telebot_version.py"]
    
    try:
        # Запускаем процесс с перенаправлением вывода
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Выводим информацию о процессе
        print(f"Бот запущен с PID: {process.pid}")
        
        # Читаем и выводим вывод бота в реальном времени
        for line in process.stdout:
            print(f"БОТ > {line.strip()}")
        
        # Ждем завершения процесса
        return_code = process.wait()
        
        if return_code != 0:
            print(f"Бот завершился с ошибкой (код {return_code})")
            return False
        
        return True
    
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
        return False
    except KeyboardInterrupt:
        print("Получен сигнал CTRL+C, останавливаю бота...")
        if process:
            process.terminate()
            process.wait()
        return False

if __name__ == "__main__":
    run_bot() 