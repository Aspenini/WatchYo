import sys, os, json, requests
from dotenv import load_dotenv
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QHBoxLayout, QStackedLayout, QDialog, QTextEdit,
    QGridLayout, QMessageBox, QFrame, QLineEdit, QInputDialog
)
from PyQt6.QtGui import QPixmap, QIcon, QAction
from PyQt6.QtCore import Qt, QSize
from PIL import Image
from io import BytesIO

# === Setup ===
load_dotenv()
API_KEY = os.getenv("TMDB_API_KEY")
APP_DIR = os.path.dirname(__file__)
LIBRARY_FILE = os.path.join(APP_DIR, "watchyo_library.json")
POSTER_DIR = os.path.join(APP_DIR, "posters")
os.makedirs(POSTER_DIR, exist_ok=True)

# === Helpers ===
def fetch_movie_data(title):
    url = f'https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={title}'
    res = requests.get(url).json()
    if res['results']:
        return res['results'][0]
    return None

def download_poster(poster_path):
    if not poster_path:
        return None
    url = f'https://image.tmdb.org/t/p/w342{poster_path}'
    img_data = requests.get(url).content
    local_path = os.path.join(POSTER_DIR, poster_path.lstrip('/'))
    with open(local_path, 'wb') as f:
        f.write(img_data)
    # Return relative path instead of absolute
    return os.path.relpath(local_path, APP_DIR)

def load_library():
    if os.path.exists(LIBRARY_FILE):
        with open(LIBRARY_FILE, 'r') as f:
            return json.load(f)
    return []

def save_library(library):
    with open(LIBRARY_FILE, 'w') as f:
        json.dump(library, f, indent=4)

# === Movie Detail Dialog ===
class MovieDialog(QDialog):
    def __init__(self, movie):
        super().__init__()
        self.setWindowTitle(movie['title'])
        layout = QVBoxLayout()

        if movie['poster_path']:
            # Convert relative path to absolute for QPixmap
            poster_path = os.path.join(APP_DIR, movie['poster_path'])
            pixmap = QPixmap(poster_path).scaledToWidth(300, Qt.TransformationMode.SmoothTransformation)
            poster = QLabel()
            poster.setPixmap(pixmap)
            layout.addWidget(poster)

        title_label = QLabel(f"<h2>{movie['title']} ({movie['year']})</h2>")
        layout.addWidget(title_label)

        overview = QTextEdit(movie['overview'])
        overview.setReadOnly(True)
        overview.setStyleSheet("background-color: #111; color: white;")
        layout.addWidget(overview)

        self.setLayout(layout)
        self.setStyleSheet("background-color: #222; color: white;")

# === Main App ===
class WatchYoApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WatchYo")
        self.setMinimumSize(1200, 700)
        self.library = load_library()

        self.main_layout = QHBoxLayout(self)
        self.sidebar = self.create_sidebar()
        self.stack = QStackedLayout()

        self.movie_page = self.create_movie_grid()
        self.stack.addWidget(self.movie_page)

        self.settings_page = QLabel("⚙️ Settings coming soon...")
        self.settings_page.setStyleSheet("color: white; font-size: 18px;")
        self.stack.addWidget(self.settings_page)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addLayout(self.stack)
        self.setLayout(self.main_layout)

        self.render_movie_grid()
        
        # Set initial active state
        self.current_page = 0
        self.update_active_button()

        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: white;
            }
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 16px;
                padding: 10px;
                text-align: left;
                border-radius: 5px;
                margin: 2px 5px;
            }
            QPushButton:hover {
                background-color: #1e1e1e;
            }
            QPushButton:focus {
                outline: none;
                border: none;
            }
            QPushButton.active {
                background-color: #2d5af5;
                color: white;
            }
            QLabel {
                background-color: transparent;
            }
        """)

    def create_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(200)
        layout = QVBoxLayout(sidebar)

        self.btn_movies = QPushButton("🎬  Movies")
        self.btn_settings = QPushButton("⚙️  Settings")
        self.btn_add = QPushButton("➕  Add Movie")

        for btn in [self.btn_movies, self.btn_settings, self.btn_add]:
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFlat(True)

        self.btn_movies.clicked.connect(lambda: self.switch_to_page(0))
        self.btn_settings.clicked.connect(lambda: self.switch_to_page(1))
        self.btn_add.clicked.connect(self.add_movie)

        layout.addStretch(1)
        layout.addWidget(self.btn_movies)
        layout.addWidget(self.btn_settings)
        layout.addStretch(1)
        layout.addWidget(self.btn_add)
        layout.addStretch(10)

        sidebar.setStyleSheet("background-color: #202020;")
        return sidebar

    def create_movie_grid(self):
        self.movie_grid_widget = QWidget()
        self.movie_grid_layout = QGridLayout(self.movie_grid_widget)
        self.movie_grid_layout.setSpacing(30)  # Increased spacing between items
        self.movie_grid_layout.setContentsMargins(30, 30, 30, 30)  # Increased margins
        return self.movie_grid_widget

    def render_movie_grid(self):
        for i in reversed(range(self.movie_grid_layout.count())):
            self.movie_grid_layout.itemAt(i).widget().setParent(None)

        for idx, movie in enumerate(self.library):
            # Convert relative path to absolute for QPixmap
            poster_path = os.path.join(APP_DIR, movie['poster_path']) if movie['poster_path'] else None
            poster = QPixmap(poster_path) if poster_path else QPixmap()
            
            # Create a container widget for each movie
            movie_container = QWidget()
            movie_container.setFixedSize(170, 245)  # Fixed size container
            movie_container.setCursor(Qt.CursorShape.PointingHandCursor)
            movie_container.mousePressEvent = lambda e, m=movie: self.on_poster_click(e, m)
            
            # Create layout for the container
            container_layout = QVBoxLayout(movie_container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(5)
            
            # Create the poster label
            thumb = QLabel()
            thumb.setPixmap(poster.scaled(QSize(150, 225), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb.setStyleSheet("background-color: transparent;")
            
            # Add poster to container
            container_layout.addWidget(thumb)
            
            # Add container to grid
            self.movie_grid_layout.addWidget(movie_container, idx // 5, idx % 5)

    def on_poster_click(self, event, movie):
        if event.button() == Qt.MouseButton.LeftButton:
            dlg = MovieDialog(movie)
            dlg.exec()
        elif event.button() == Qt.MouseButton.RightButton:
            os.startfile(movie['file_path'])

    def add_movie(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Choose Movie", "", "Video files (*.mp4 *.mkv *.avi)")
        if not file_path:
            return

        base = os.path.basename(file_path)
        title, ok = QInputDialog.getText(self, "Movie Title", "Enter movie title:", text=base.rsplit('.', 1)[0])
        if not ok or not title:
            return

        data = fetch_movie_data(title)
        if not data:
            QMessageBox.critical(self, "Error", "Movie not found.")
            return

        poster_path = download_poster(data['poster_path'])
        movie = {
            'title': data['title'],
            'overview': data['overview'],
            'year': data['release_date'][:4] if data['release_date'] else 'N/A',
            'poster_path': poster_path,
            'file_path': file_path
        }

        self.library.append(movie)
        save_library(self.library)
        self.render_movie_grid()

    def switch_to_page(self, page_index):
        """Switch to a page and update the active button"""
        self.stack.setCurrentIndex(page_index)
        self.current_page = page_index
        self.update_active_button()

    def update_active_button(self):
        """Update the visual state of sidebar buttons based on current page"""
        # Reset all buttons to default style
        self.btn_movies.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 16px;
                padding: 10px;
                text-align: left;
                border-radius: 5px;
                margin: 2px 5px;
            }
            QPushButton:hover {
                background-color: #1e1e1e;
            }
        """)
        
        self.btn_settings.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 16px;
                padding: 10px;
                text-align: left;
                border-radius: 5px;
                margin: 2px 5px;
            }
            QPushButton:hover {
                background-color: #1e1e1e;
            }
        """)
        
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 16px;
                padding: 10px;
                text-align: left;
                border-radius: 5px;
                margin: 2px 5px;
            }
            QPushButton:hover {
                background-color: #1e1e1e;
            }
        """)
        
        # Set active style for current button
        if self.current_page == 0:
            self.btn_movies.setStyleSheet("""
                QPushButton {
                    background-color: #2d5af5;
                    color: white;
                    font-size: 16px;
                    padding: 10px;
                    text-align: left;
                    border-radius: 5px;
                    margin: 2px 5px;
                }
                QPushButton:hover {
                    background-color: #3d6af5;
                }
            """)
        elif self.current_page == 1:
            self.btn_settings.setStyleSheet("""
                QPushButton {
                    background-color: #2d5af5;
                    color: white;
                    font-size: 16px;
                    padding: 10px;
                    text-align: left;
                    border-radius: 5px;
                    margin: 2px 5px;
                }
                QPushButton:hover {
                    background-color: #3d6af5;
                }
            """)

# === Run App ===
if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = WatchYoApp()
    win.show()
    sys.exit(app.exec())
