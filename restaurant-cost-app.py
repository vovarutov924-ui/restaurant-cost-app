import sys
import requests
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QTabWidget, QTextEdit, QMessageBox, QStyledItemDelegate, QFormLayout,
    QDialogButtonBox, QMainWindow, QMenu, QComboBox, QDateEdit, QDialog
)
from PySide6.QtGui import QIcon, QDoubleValidator, QAction, QActionGroup
from PySide6.QtCore import Qt, QDateTime
import sqlite3


class IngredientDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        if index.column() == 1 or index.column() == 2:
            editor = QLineEdit(parent)
            validator = QDoubleValidator(0.0, 99999.0, 2)
            editor.setValidator(validator)
            return editor
        else:
            return super().createEditor(parent, option, index)

    def displayText(self, value, locale):
        if isinstance(value, float):
            return f"{value:.2f}"
        return super().displayText(value, locale)


class RestaurantSelector(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Выберите ресторан")

        layout = QVBoxLayout()
        self.comboBox = QComboBox()
        self.load_restaurants()
        layout.addWidget(self.comboBox)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def load_restaurants(self):
        conn = sqlite3.connect('costchef.db')
        c = conn.cursor()
        c.execute('SELECT name FROM restaurants ORDER BY id ASC')
        restaurants = [row[0] for row in c.fetchall()]
        conn.close()

        self.comboBox.addItems(restaurants)


class CostApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Калькулятор себестоимости")
        self.resize(800, 600)

        self.comboBox = QComboBox()

        self.init_db()
        self.create_actions()
        self.create_menu_bar()

        self.tabs = QTabWidget()
        self.tab_ingredients = QWidget()
        self.tab_ai = QWidget()

        self.tabs.addTab(self.tab_ingredients, "Ингредиенты")
        self.tabs.addTab(self.tab_ai, "Анализ ИИ")

        self.init_ingredients_tab()
        self.init_ai_tab()

        central_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)

        self.setCentralWidget(central_widget)

    def create_actions(self):
        self.action_dark_theme = QAction("Темная тема", self, checkable=True)
        self.action_light_theme = QAction("Светлая тема", self, checkable=True)

        group = QActionGroup(self)
        group.addAction(self.action_dark_theme)
        group.addAction(self.action_light_theme)
        self.action_light_theme.setChecked(True)

    def create_menu_bar(self):
        menu_bar = self.menuBar()

        view_menu = menu_bar.addMenu("Вид")
        view_menu.addAction(self.action_dark_theme)
        view_menu.addAction(self.action_light_theme)

        self.action_dark_theme.triggered.connect(self.set_dark_theme)
        self.action_light_theme.triggered.connect(self.set_light_theme)

    def set_dark_theme(self):
        self.setStyleSheet("background-color: #2c3e50; color: white;")

    def set_light_theme(self):
        self.setStyleSheet("background-color: white; color: black;")

    def init_db(self):
        conn = sqlite3.connect('costchef.db')
        c = conn.cursor()

        # Удаляем старую таблицу, если она есть
        c.execute('DROP TABLE IF EXISTS ingredients')
        c.execute('DROP TABLE IF EXISTS restaurants')

        # Создаём таблицу ресторанов
        c.execute('''
            CREATE TABLE IF NOT EXISTS restaurants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')

        # Создаём таблицу ингредиентов
        c.execute('''
            CREATE TABLE IF NOT EXISTS ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                restaurant_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                grams REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Добавляем ресторан по умолчанию
        c.execute('INSERT OR IGNORE INTO restaurants (name) VALUES (?)', ('Основной ресторан',))

        conn.commit()
        conn.close()

    def init_ingredients_tab(self):
        layout = QVBoxLayout()

        title_label = QLabel("Добавление ингредиента")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(title_label)

        input_layout = QFormLayout()

        self.category_input = QComboBox()
        self.category_input.addItems(["Кухня", "Бар", "Хоз товары"])

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название")
        self.name_input.setFixedWidth(200)

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("Цена за кг")
        self.price_input.setFixedWidth(100)
        validator_price = QDoubleValidator(0.0, 99999.0, 2)
        self.price_input.setValidator(validator_price)

        self.grams_input = QLineEdit()
        self.grams_input.setPlaceholderText("Граммы")
        self.grams_input.setFixedWidth(100)
        validator_grams = QDoubleValidator(0.0, 99999.0, 2)
        self.grams_input.setValidator(validator_grams)

        input_layout.addRow(QLabel("Категория"), self.category_input)
        input_layout.addRow(QLabel("Название"), self.name_input)
        input_layout.addRow(QLabel("Цена за кг"), self.price_input)
        input_layout.addRow(QLabel("Граммы"), self.grams_input)

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_ingredient)
        add_btn.setFixedSize(100, 32)
        input_layout.addWidget(add_btn)

        layout.addLayout(input_layout)

        title_label = QLabel("Список ингредиентов")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(title_label)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Название", "Цена за кг", "Граммы", "Стоимость", "Категория", "Создан", "Изменен"])
        delegate = IngredientDelegate(self)
        self.table.setItemDelegate(delegate)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        title_label = QLabel("Расчет себестоимости")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(title_label)

        calc_layout = QHBoxLayout()

        calc_layout.addWidget(QLabel("Наценка, %:"))

        self.markup_input = QLineEdit("200")
        self.markup_input.setPlaceholderText("Наценка")
        self.markup_input.setFixedWidth(80)
        validator_markup = QDoubleValidator(0.0, 99999.0, 2)
        self.markup_input.setValidator(validator_markup)

        calc_layout.addWidget(self.markup_input)

        calc_btn = QPushButton("Рассчитать себестоимость")
        calc_btn.clicked.connect(self.calculate)
        calc_btn.setFixedSize(200, 32)
        calc_layout.addWidget(calc_btn)

        layout.addLayout(calc_layout)

        self.result_label = QLabel("Себестоимость: —")
        self.result_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.result_label)

        self.tab_ingredients.setLayout(layout)

    def init_ai_tab(self):
        layout = QVBoxLayout()

        self.ai_output = QTextEdit()
        self.ai_output.setReadOnly(True)
        self.ai_output.setStyleSheet("background-color: #f0f0f0; border: 1px solid #ccc; font-family: Arial, sans-serif;")
        layout.addWidget(self.ai_output)

        ask_btn = QPushButton("Спросить ИИ")
        ask_btn.clicked.connect(self.ask_ai)
        ask_btn.setFixedSize(200, 32)
        layout.addWidget(ask_btn)

        self.tab_ai.setLayout(layout)

    def add_ingredient(self):
        category = self.category_input.currentText()
        name = self.name_input.text().strip()
        price_text = self.price_input.text().strip()
        grams_text = self.grams_input.text().strip()

        if not name or not price_text or not grams_text:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля.")
            return

        try:
            price = float(price_text)
            grams = float(grams_text)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите числа в поля цены и граммов")
            return

        cost = (price / 1000) * grams

        conn = sqlite3.connect('costchef.db')
        c = conn.cursor()

        restaurant_id = self.get_selected_restaurant_id()

        c.execute('''
            INSERT INTO ingredients (restaurant_id, category, name, price, grams) VALUES (?, ?, ?, ?, ?)
        ''', (restaurant_id, category, name, price, grams))

        conn.commit()
        conn.close()

        self.load_ingredients()

        self.name_input.clear()
        self.price_input.clear()
        self.grams_input.clear()

    def calculate(self):
        total = 0
        for row in range(self.table.rowCount()):
            try:
                cost_item = self.table.item(row, 3)
                if cost_item is not None and cost_item.text():
                    total += float(cost_item.text())
            except ValueError:
                pass

        markup_text = self.markup_input.text().strip()
        if not markup_text:
            QMessageBox.warning(self, "Ошибка", "Введите число в поле наценки")
            return

        try:
            markup = float(markup_text)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите число в поле наценки")
            return

        price = total * (1 + markup / 100)

        self.result_label.setText(f"Себестоимость: {total:.2f} ₽ | Цена продажи: {price:.2f} ₽")

    def ask_ai(self):
        ingredients = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            cost_item = self.table.item(row, 3)

            if name_item and cost_item:
                name = name_item.text()
                cost = cost_item.text()
                ingredients.append(f"{name}: {cost} ₽")

        total_label = self.result_label.text()

        if not total_label.startswith("Себестоимость:"):
            QMessageBox.warning(self, "Ошибка", "Сначала рассчитайте себестоимость блюда.")
            return

        prompt = (
            f"У меня есть блюдо. Ингредиенты: {', '.join(ingredients)}. "
            f"{total_label}. "
            "Проанализируй и скажи: стоит ли поднять цену, заменить ингредиент или убрать его? "
            "Ответь кратко и по делу."
        )

        url = "http://127.0.0.1:1234/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        data = {
            "model": "qwen/qwen2.5-coder-14b",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 500
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                self.ai_output.setText(result["choices"][0]["message"]["content"])
            else:
                self.ai_output.setText(f"Ошибка: {response.status_code}")

        except Exception as e:
            self.ai_output.setText(f"Не удалось подключиться к LM Studio: {e}")

    def load_ingredients(self):
        conn = sqlite3.connect('costchef.db')
        c = conn.cursor()

        restaurant_id = self.get_selected_restaurant_id()

        c.execute('''
            SELECT name, price, grams, (price / 1000) * grams, category, created_at, updated_at
            FROM ingredients
            WHERE restaurant_id = ?
            ORDER BY id DESC
        ''', (restaurant_id,))

        rows = c.fetchall()
        conn.close()

        self.table.setRowCount(0)
        for row in rows:
            name, price, grams, cost, category, created_at, updated_at = row

            created_at_formatted = created_at.split(".")[0] if isinstance(created_at, str) else created_at.strftime("%d.%m.%Y")
            updated_at_formatted = updated_at.split(".")[0] if isinstance(updated_at, str) else updated_at.strftime("%d.%m.%Y")

            self.table.insertRow(self.table.rowCount())

            item_name = QTableWidgetItem(name)
            item_price = QTableWidgetItem(f"{price:.2f}")
            item_grams = QTableWidgetItem(f"{grams:.2f}")
            item_cost = QTableWidgetItem(f"{cost:.2f}")
            item_category = QTableWidgetItem(category)
            item_created_at = QTableWidgetItem(str(created_at_formatted))
            item_updated_at = QTableWidgetItem(str(updated_at_formatted))

            item_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            item_price.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_grams.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_cost.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            item_category.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            item_created_at.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            item_updated_at.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            self.table.setItem(self.table.rowCount() - 1, 0, item_name)
            self.table.setItem(self.table.rowCount() - 1, 1, item_price)
            self.table.setItem(self.table.rowCount() - 1, 2, item_grams)
            self.table.setItem(self.table.rowCount() - 1, 3, item_cost)
            self.table.setItem(self.table.rowCount() - 1, 4, item_category)
            self.table.setItem(self.table.rowCount() - 1, 5, item_created_at)
            self.table.setItem(self.table.rowCount() - 1, 6, item_updated_at)

    def get_selected_restaurant_id(self):
        restaurant_name = self.comboBox.currentText()
        if not restaurant_name:
            restaurant_name = "Основной ресторан"
        conn = sqlite3.connect('costchef.db')
        c = conn.cursor()
        c.execute('SELECT id FROM restaurants WHERE name = ?', (restaurant_name,))
        row = c.fetchone()
        conn.close()
        if row:
            return row[0]
        else:
            return 1

    def show_login_window(self):
        selector = RestaurantSelector(self)
        result = selector.exec()
        if result == QDialog.Accepted:
            self.comboBox.setCurrentText(selector.comboBox.currentText())
            self.load_ingredients()
            self.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = CostApp()
    window.show_login_window()

    sys.exit(app.exec())