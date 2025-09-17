# imagen_gui.py - Imagen 3 Batch Generator с GUI
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import time
import pathlib
import concurrent.futures
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
import os
import subprocess

class ImagenBatchGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("🎨 Imagen 3 Batch Generator Pro")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Настройки
        self.PROJECT_ID = "my-imagen-generator"
        self.LOCATION = "us-central1"
        self.MODEL_ID = "imagen-3.0-generate-002"
        self.model = None
        self.is_generating = False
        
        self.create_widgets()
        self.init_vertex_ai()

    def create_widgets(self):
        # Главная рамка
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Заголовок
        title_label = ttk.Label(main_frame, text="🎨 Imagen 3 Batch Generator Pro", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # === НАСТРОЙКИ ===
        settings_frame = ttk.LabelFrame(main_frame, text="⚙️ Настройки генерации", padding="10")
        settings_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Количество изображений на промпт
        ttk.Label(settings_frame, text="Количество вариантов на промпт:").grid(row=0, column=0, sticky=tk.W)
        self.variations_var = tk.StringVar(value="3")
        variations_combo = ttk.Combobox(settings_frame, textvariable=self.variations_var, 
                                      values=["1", "2", "3", "4", "5"], width=5, state="readonly")
        variations_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Размер изображения
        ttk.Label(settings_frame, text="Размер изображения:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0))
        self.aspect_var = tk.StringVar(value="1:1")
        aspect_combo = ttk.Combobox(settings_frame, textvariable=self.aspect_var,
                                   values=["1:1", "16:9", "9:16", "4:3", "3:4"], width=8, state="readonly")
        aspect_combo.grid(row=0, column=3, sticky=tk.W, padx=(10, 0))
        
        # Количество потоков
        ttk.Label(settings_frame, text="Параллельных потоков:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.workers_var = tk.StringVar(value="2")
        workers_combo = ttk.Combobox(settings_frame, textvariable=self.workers_var,
                                   values=["1", "2", "3", "4"], width=5, state="readonly")
        workers_combo.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        
        # === ПРОМПТЫ ===
        prompts_frame = ttk.LabelFrame(main_frame, text="📝 Промпты для генерации", padding="10")
        prompts_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Текстовое поле для промптов
        self.prompts_text = scrolledtext.ScrolledText(prompts_frame, height=12, wrap=tk.WORD)
        self.prompts_text.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Кнопки для работы с промптами
        ttk.Button(prompts_frame, text="📂 Загрузить из файла", 
                  command=self.load_prompts).grid(row=1, column=0, sticky=tk.W)
        ttk.Button(prompts_frame, text="💾 Сохранить в файл", 
                  command=self.save_prompts).grid(row=1, column=1, padx=(10, 0))
        ttk.Button(prompts_frame, text="🗑️ Очистить", 
                  command=self.clear_prompts).grid(row=1, column=2, padx=(10, 0))
        
        # === УПРАВЛЕНИЕ ===
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Большая кнопка генерации
        self.generate_btn = ttk.Button(control_frame, text="🚀 ЗАПУСТИТЬ ГЕНЕРАЦИЮ", 
                                      command=self.start_generation, style='Accent.TButton')
        self.generate_btn.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Кнопки управления результатами
        ttk.Button(control_frame, text="📁 Открыть папку результатов", 
                  command=self.open_results_folder).grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        ttk.Button(control_frame, text="🔄 Создать новую папку", 
                  command=self.create_new_folder).grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        # === ПРОГРЕСС И СТАТУС ===
        progress_frame = ttk.LabelFrame(main_frame, text="📊 Прогресс", padding="10")
        progress_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Прогресс бар
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        # Статус
        self.status_var = tk.StringVar(value="✅ Готов к работе")
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        self.status_label.grid(row=1, column=0, sticky=tk.W)
        
        # Лог
        self.log_text = scrolledtext.ScrolledText(progress_frame, height=6)
        self.log_text.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        
        # Настройка растягивания
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        prompts_frame.columnconfigure(0, weight=1)
        prompts_frame.rowconfigure(0, weight=1)
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(2, weight=1)
        
        # Загружаем примерные промпты
        self.load_sample_prompts()

    def init_vertex_ai(self):
        """Инициализация Vertex AI"""
        def init_in_thread():
            try:
                self.log("🚀 Инициализация Vertex AI...")
                vertexai.init(project=self.PROJECT_ID, location=self.LOCATION)
                self.model = ImageGenerationModel.from_pretrained(self.MODEL_ID)
                self.log("✅ Vertex AI готов к работе!")
                self.status_var.set("✅ Готов к генерации")
            except Exception as e:
                self.log(f"❌ Ошибка инициализации: {e}")
                self.status_var.set("❌ Ошибка подключения")
        
        threading.Thread(target=init_in_thread, daemon=True).start()

    def log(self, message):
        """Добавляет сообщение в лог"""
        timestamp = time.strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def load_sample_prompts(self):
        """Загружает примерные промпты"""
        sample_prompts = """красивый закат над океаном, фотореалистично
футуристический город, неоновые огни, киберпанк стиль
уютная гостиная с камином, теплый свет, зима за окном
космический корабль в далекой галактике, звезды, драматическое освещение
портрет красивой девушки в винтажном стиле, ретро мода
горный пейзаж на рассвете, туман, фотография природы"""
        self.prompts_text.insert("1.0", sample_prompts)

    def load_prompts(self):
        """Загружает промпты из файла"""
        filename = filedialog.askopenfilename(
            title="Выберите файл с промптами",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.prompts_text.delete("1.0", tk.END)
                self.prompts_text.insert("1.0", content)
                self.log(f"📂 Промпты загружены из {filename}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")

    def save_prompts(self):
        """Сохраняет промпты в файл"""
        filename = filedialog.asksaveasfilename(
            title="Сохранить промпты",
            defaultextension=".txt",
            filetypes=[("Текстовые файлы", "*.txt"), ("Все файлы", "*.*")]
        )
        if filename:
            try:
                content = self.prompts_text.get("1.0", tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.log(f"💾 Промпты сохранены в {filename}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

    def clear_prompts(self):
        """Очищает поле промптов"""
        if messagebox.askyesno("Подтверждение", "Очистить все промпты?"):
            self.prompts_text.delete("1.0", tk.END)
            self.log("🗑️ Промпты очищены")

    def get_prompts_list(self):
        """Получает список промптов из текстового поля"""
        content = self.prompts_text.get("1.0", tk.END)
        prompts = [line.strip() for line in content.splitlines() if line.strip()]
        return prompts

    def clean_filename(self, text, max_len=30):
        """Создает безопасное имя файла"""
        clean = "".join(c for c in text if c.isalnum() or c in (" ", "_", "-"))
        return clean[:max_len].strip().replace(" ", "_")

    def generate_for_prompt(self, prompt_data):
        """Генерирует изображения для одного промпта"""
        index, prompt, total_prompts = prompt_data
        
        try:
            # Обновляем прогресс
            progress = (index / total_prompts) * 100
            self.progress_bar['value'] = progress
            
            self.log(f"🎨 [{index+1}/{total_prompts}] {prompt[:40]}...")
            
            # Генерация
            images = self.model.generate_images(
                prompt=prompt,
                number_of_images=int(self.variations_var.get()),
                aspect_ratio=self.aspect_var.get(),
                safety_filter_level="block_some",
                person_generation="allow_adult"
            )
            
            # Сохранение
            outdir = pathlib.Path("results")
            outdir.mkdir(exist_ok=True)
            
            saved_files = []
            timestamp = int(time.time() * 1000)
            base_name = self.clean_filename(prompt)
            
            for i, image in enumerate(images, start=1):
                filename = f"{timestamp}_{base_name}_v{i}.png"
                filepath = outdir / filename
                image.save(filepath)
                saved_files.append(str(filepath))
            
            self.log(f"✅ [{index+1}/{total_prompts}] Готово: {len(saved_files)} файлов")
            return len(saved_files)
            
        except Exception as e:
            self.log(f"❌ [{index+1}/{total_prompts}] Ошибка: {str(e)[:50]}...")
            return 0

    def start_generation(self):
        """Запускает генерацию в отдельном потоке"""
        if self.is_generating:
            messagebox.showwarning("Внимание", "Генерация уже запущена!")
            return
            
        prompts = self.get_prompts_list()
        if not prompts:
            messagebox.showwarning("Внимание", "Введите хотя бы один промпт!")
            return
            
        if not self.model:
            messagebox.showerror("Ошибка", "Vertex AI не инициализирован!")
            return
        
        def generation_thread():
            self.is_generating = True
            self.generate_btn.config(text="⏳ Генерация...", state="disabled")
            self.status_var.set("🔄 Генерация изображений...")
            
            start_time = time.time()
            total_images = 0
            
            try:
                max_workers = int(self.workers_var.get())
                self.log(f"🚀 Запуск генерации: {len(prompts)} промптов, {max_workers} потоков")
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [executor.submit(self.generate_for_prompt, (i, prompt, len(prompts))) 
                              for i, prompt in enumerate(prompts)]
                    
                    for future in concurrent.futures.as_completed(futures):
                        total_images += future.result()
                
                elapsed_time = time.time() - start_time
                
                self.log("=" * 50)
                self.log("🎯 ГЕНЕРАЦИЯ ЗАВЕРШЕНА!")
                self.log(f"⏱️ Время: {elapsed_time:.1f} сек")
                self.log(f"🖼️ Создано изображений: {total_images}")
                self.log(f"📁 Папка: {pathlib.Path('results').absolute()}")
                
                self.progress_bar['value'] = 100
                self.status_var.set(f"✅ Готово! {total_images} изображений")
                
                messagebox.showinfo("Готово!", 
                                   f"Генерация завершена!\n"
                                   f"Создано изображений: {total_images}\n"
                                   f"Время: {elapsed_time:.1f} секунд")
                
            except Exception as e:
                self.log(f"❌ Критическая ошибка: {e}")
                self.status_var.set("❌ Ошибка генерации")
                messagebox.showerror("Ошибка", f"Критическая ошибка: {e}")
            
            finally:
                self.is_generating = False
                self.generate_btn.config(text="🚀 ЗАПУСТИТЬ ГЕНЕРАЦИЮ", state="normal")
        
        threading.Thread(target=generation_thread, daemon=True).start()

    def open_results_folder(self):
        """Открывает папку с результатами"""
        results_path = pathlib.Path("results")
        results_path.mkdir(exist_ok=True)
        
        try:
            if os.name == 'nt':  # Windows
                os.startfile(results_path)
            else:  # macOS/Linux
                subprocess.run(['open' if os.name == 'posix' else 'xdg-open', results_path])
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть папку: {e}")

    def create_new_folder(self):
        """Создает новую папку для результатов"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        new_folder = pathlib.Path(f"results_{timestamp}")
        new_folder.mkdir(exist_ok=True)
        self.log(f"📁 Создана папка: {new_folder}")
        messagebox.showinfo("Готово", f"Создана новая папка:\n{new_folder.absolute()}")

def main():
    root = tk.Tk()
    app = ImagenBatchGenerator(root)
    root.mainloop()

if __name__ == "__main__":
    main()
