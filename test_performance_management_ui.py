from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QPushButton, QLabel, QListWidget, QTabWidget
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from transformers import pipeline


# Class for handling AI model inference in a separate process
class AiWorker(QThread):
    result_signal = pyqtSignal(str, str)  # For categorization or summarization results

    def __init__(self, task_type, text, categories=None):
        super().__init__()
        self.task_type = task_type
        self.text = text
        self.categories = categories

    def run(self):
        # Lazy loading of models
        if self.task_type == 'summarize':
            summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
            result = summarizer(self.text, max_length=150, min_length=50, do_sample=False)[0]['summary_text']
        elif self.task_type == 'categorize':
            classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
            result = classifier(self.text, candidate_labels=self.categories)
            best_category = result["labels"][0]
            result = f"[{best_category}] {self.text}"

        self.result_signal.emit(self.task_type, result)


# Main application UI
class AccomplishmentApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        # Define competency categories
        self.categories = [
            "Communication", "Customer Focus", "Influence", "Job Specific Skills",
            "Judgment", "Lives the Values", "Problem Solving", "Results Focus", "Teamwork"
        ]

    def initUI(self):
        """Initialize the UI layout with tabs."""
        self.setWindowTitle("Accomplishment Categorizer & Summarizer")
        self.setGeometry(100, 100, 600, 500)
        layout = QVBoxLayout()

        # Create Tabs
        self.tabs = QTabWidget(self)

        # Tab 1: Categorization
        self.categorization_tab = QWidget()
        self.initCategorizationTab()
        self.tabs.addTab(self.categorization_tab, "Categorization")

        # Tab 2: Summarization
        self.summarization_tab = QWidget()
        self.initSummarizationTab()
        self.tabs.addTab(self.summarization_tab, "Summarization")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def initCategorizationTab(self):
        """Initialize the Categorization Tab."""
        layout = QVBoxLayout()

        self.input_box_cat = QTextEdit(self)
        self.input_box_cat.setPlaceholderText("Enter accomplishments, one per line...")
        layout.addWidget(self.input_box_cat)

        self.categorize_button = QPushButton("Categorize", self)
        self.categorize_button.clicked.connect(self.categorize_text)
        layout.addWidget(self.categorize_button)

        self.output_list_cat = QListWidget(self)
        layout.addWidget(self.output_list_cat)

        self.categorization_tab.setLayout(layout)

    def initSummarizationTab(self):
        """Initialize the Summarization Tab."""
        layout = QVBoxLayout()

        self.input_box_sum = QTextEdit(self)
        self.input_box_sum.setPlaceholderText("Enter text to summarize...")
        layout.addWidget(self.input_box_sum)

        self.summarize_button = QPushButton("Summarize", self)
        self.summarize_button.clicked.connect(self.summarize_text)
        layout.addWidget(self.summarize_button)

        # QLabel to display the summary with word wrapping
        self.output_label_sum = QLabel("Summary will appear here.", self)
        self.output_label_sum.setWordWrap(True)  # Enable word wrapping
        self.output_label_sum.setAlignment(Qt.AlignmentFlag.AlignTop)  # Align the text to the top
        self.output_label_sum.setStyleSheet(
            "QLabel { width: 100%; max-width: 550px; }")  # Set a max-width to control wrapping
        layout.addWidget(self.output_label_sum)

        self.summarization_tab.setLayout(layout)

    def categorize_text(self):
        """Classifies multiple accomplishments into predefined categories."""
        text = self.input_box_cat.toPlainText().strip()
        if not text:
            self.output_list_cat.clear()
            self.output_list_cat.addItem("Please enter accomplishments to categorize.")
            return

        self.output_list_cat.clear()
        accomplishments = text.split("\n")  # Split input by lines

        # Use multiprocessing to handle classification in a separate process
        for acc in accomplishments:
            acc = acc.strip()
            if not acc:
                continue
            worker = AiWorker(task_type='categorize', text=acc, categories=self.categories)
            worker.result_signal.connect(self.update_result)
            worker.start()

    def summarize_text(self):
        """Summarizes the input text using AI."""
        text = self.input_box_sum.toPlainText().strip()
        if not text:
            self.output_label_sum.setText("Please enter text to summarize.")
            return

        # Use multiprocessing to handle summarization in a separate process
        worker = AiWorker(task_type='summarize', text=text)
        worker.result_signal.connect(self.update_summary)
        worker.start()

    def update_result(self, task_type, result):
        """Updates the result in the Categorization tab."""
        if task_type == 'categorize':
            self.output_list_cat.addItem(result)

    def update_summary(self, task_type, result):
        """Updates the summary result in the Summarization tab."""
        if task_type == 'summarize':
            # Update the QLabel with the summary
            self.output_label_sum.setText(f"Summary: {result}")


if __name__ == "__main__":
    app = QApplication([])
    window = AccomplishmentApp()
    window.show()
    app.exec()
