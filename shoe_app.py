import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from PIL import Image, ImageTk
import os

# ====================== НАСТРОЙКИ ПОДКЛЮЧЕНИЯ К БД ======================
DB_CONFIG = {
    'dbname': 'shoe_store',
    'user': 'postgres',          
    'password': '1234',   
    'host': 'localhost',
    'port': '5433'
}

# Путь к заглушке фото 
PLACEHOLDER_IMAGE = "picture.png"

class ShoeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Магазин обуви")
        self.root.geometry("1200x700")
        self.root.configure(bg="#f0f0f0")

        self.current_user = None
        self.photo_label = None  # Для отображения фото

        self.show_login_screen()

    def connect_db(self):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            print("[INFO] Подключение к БД установлено")
            return conn
        except Exception as e:
            print(f"[ERROR] Ошибка подключения к БД: {e}")
            messagebox.showerror("Ошибка", f"Не удалось подключиться к БД:\n{e}")
            return None

    # ====================== ЭКРАН ВХОДА ======================
    def show_login_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.pack(pady=100)

        tk.Label(frame, text="Авторизация", font=("Arial", 20, "bold"), bg="#f0f0f0").pack(pady=20)

        tk.Label(frame, text="Логин:", font=("Arial", 12), bg="#f0f0f0").pack()
        self.login_entry = tk.Entry(frame, font=("Arial", 12), width=30)
        self.login_entry.pack(pady=5)

        tk.Label(frame, text="Пароль:", font=("Arial", 12), bg="#f0f0f0").pack()
        self.password_entry = tk.Entry(frame, font=("Arial", 12), width=30, show="*")
        self.password_entry.pack(pady=5)

        btn_frame = tk.Frame(frame, bg="#f0f0f0")
        btn_frame.pack(pady=20)

        tk.Button(btn_frame, text="Войти", font=("Arial", 12), bg="#4CAF50", fg="white", width=15,
                  command=self.login).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Гость", font=("Arial", 12), bg="#2196F3", fg="white", width=15,
                  command=self.enter_as_guest).pack(side=tk.LEFT, padx=10)

    def login(self):
        login = self.login_entry.get().strip()
        password = self.password_entry.get().strip()

        if not login or not password:
            messagebox.showwarning("Внимание", "Введите логин и пароль")
            return

        conn = self.connect_db()
        if not conn:
            return

        cur = conn.cursor()
        cur.execute("""
            SELECT u.id, u.full_name, r.name 
            FROM users u 
            JOIN roles r ON u.role_id = r.id 
            WHERE u.login = %s AND u.password = %s
        """, (login, password))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user:
            self.current_user = {
                'id': user[0],
                'full_name': user[1],
                'role': user[2]
            }
            print(f"[OK] Успешный вход: {self.current_user['full_name']} ({self.current_user['role']})")
            self.show_main_screen()
        else:
            print("[ERROR] Неверный логин или пароль")
            messagebox.showerror("Ошибка", "Неверный логин или пароль")

    def enter_as_guest(self):
        self.current_user = {'id': None, 'full_name': 'Гость', 'role': 'Гость'}
        print("[OK] Вход как Гость")
        self.show_main_screen()

    # ====================== ГЛАВНЫЙ ЭКРАН СО СПИСКОМ ТОВАРОВ ======================
    def show_main_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

        # ФИО в правом верхнем углу
        tk.Label(self.root, text=f"Пользователь: {self.current_user['full_name']}",
                 font=("Arial", 12, "bold"), bg="#f0f0f0").pack(anchor="ne", padx=20, pady=10)

        # Кнопка выхода
        tk.Button(self.root, text="Выход", font=("Arial", 10), bg="#f44336", fg="white",
                  command=self.show_login_screen).pack(anchor="ne", padx=20)

        # Заголовок
        tk.Label(self.root, text="Каталог обуви", font=("Arial", 18, "bold"), bg="#f0f0f0").pack(pady=10)

        # Таблица товаров
        columns = ("article", "name", "category", "manufacturer", "supplier", "price", "unit", "stock", "discount")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=20)
        self.tree.heading("article", text="Артикул")
        self.tree.heading("name", text="Наименование")
        self.tree.heading("category", text="Категория")
        self.tree.heading("manufacturer", text="Производитель")
        self.tree.heading("supplier", text="Поставщик")
        self.tree.heading("price", text="Цена / Со скидкой")
        self.tree.heading("unit", text="Ед.")
        self.tree.heading("stock", text="На складе")
        self.tree.heading("discount", text="Скидка %")

        self.tree.column("article", width=80)
        self.tree.column("name", width=250)
        self.tree.column("category", width=120)
        self.tree.column("manufacturer", width=120)
        self.tree.column("supplier", width=100)
        self.tree.column("price", width=140)
        self.tree.column("unit", width=50)
        self.tree.column("stock", width=80)
        self.tree.column("discount", width=80)

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Стили для подсветки
        style = ttk.Style()
        style.configure("Green.Treeview", background="#2E8B57", foreground="white")
        style.configure("Blue.Treeview", background="lightblue")
        style.configure("Strike.Treeview", font=("Arial", 10, "overstrike"))

        self.load_products()

        # Привязка двойного клика для показа фото-заглушки
        self.tree.bind("<Double-1>", self.show_placeholder_photo)

    def load_products(self):
        conn = self.connect_db()
        if not conn:
            return

        cur = conn.cursor()
        cur.execute("""
            SELECT p.article, p.name, c.name AS category, m.name AS manufacturer, s.name AS supplier,
                   p.price, p.unit, p.stock_quantity, p.discount
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN manufacturers m ON p.manufacturer_id = m.id
            LEFT JOIN suppliers s ON p.supplier_id = s.id
            ORDER BY p.article
        """)
        rows = cur.fetchall()

        self.tree.delete(*self.tree.get_children())

        for row in rows:
            article, name, category, manuf, supp, price, unit, stock, discount = row

            # Преобразуем Decimal в float один раз — это решает проблему
            price_float = float(price)

            # Теперь расчёт скидки безопасен
            final_price = price_float * (1 - discount / 100) if discount > 0 else price_float

            price_text = f"{price_float:.2f}"
            if discount > 0:
                price_text = f"~~{price_float:.2f}~~ → {final_price:.2f}"

            iid = self.tree.insert("", "end", values=(
                article, name, category or "-", manuf or "-", supp or "-",
                price_text, unit, stock, discount
            ))

            # Подсветка
            tags = []
            if discount > 15:
                tags.append("Green")
            if stock == 0:
                tags.append("Blue")

            if tags:
                self.tree.item(iid, tags=tags)

        cur.close()
        conn.close()
        print(f"[OK] Загружено товаров: {len(rows)}")

    def show_placeholder_photo(self, event):
        if self.photo_label:
            self.photo_label.destroy()

        try:
            img = Image.open(PLACEHOLDER_IMAGE)
            img = img.resize((200, 200), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.photo_label = tk.Label(self.root, image=photo, bg="#f0f0f0")
            self.photo_label.image = photo  # сохранить ссылку
            self.photo_label.pack(pady=10)
            print("[INFO] Показана заглушка фото")
        except Exception as e:
            print(f"[ERROR] Не удалось загрузить picture.png: {e}")
            messagebox.showinfo("Фото", "Заглушка фото не найдена (picture.png)")

# Запуск приложения
if __name__ == "__main__":
    print("[INFO] Запуск приложения...")
    root = tk.Tk()
    app = ShoeApp(root)
    root.mainloop()
    print("[INFO] Приложение закрыто")