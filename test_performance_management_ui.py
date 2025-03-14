from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel
from transformers import pipeline


class AccomplishmentClassifier(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
        self.categories = [
            "Communication", "Customer Focus", "Influence", "Job Specific Skills",
            "Judgment", "Lives the Values", "Problem Solving", "Results Focus", "Teamwork"
        ]

    def initUI(self):
        self.setWindowTitle("Accomplishment Categorizer")
        self.setGeometry(100, 100, 500, 400)
        layout = QVBoxLayout()

        self.input_box = QTextEdit(self)
        self.input_box.setPlaceholderText("Enter an accomplishment here...")
        layout.addWidget(self.input_box)

        self.button = QPushButton("Categorize", self)
        self.button.clicked.connect(self.categorize_text)
        layout.addWidget(self.button)

        self.output_label = QLabel("Category will appear here.", self)
        layout.addWidget(self.output_label)

        self.setLayout(layout)

    def categorize_text(self):
        text = self.input_box.toPlainText()
        if not text.strip():
            self.output_label.setText("Please enter an accomplishment.")
            return

        result = self.classifier(text, candidate_labels=self.categories)
        best_category = result["labels"][0]
        self.output_label.setText(f"Category: {best_category}")


app = QApplication([])
window = AccomplishmentClassifier()
window.show()
app.exec()
