import sys
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QFont
 
from constants import FONT_FAMILY, FONT_SIZE_NORMAL
from ui.main_window import MainWindow
 
 
def main():
    app = QApplication(sys.argv)
 
    font = QFont(FONT_FAMILY, FONT_SIZE_NORMAL)
    app.setFont(font)
 
    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception:
        err = traceback.format_exc()
        print(err, file=sys.stderr)
        # 用 MessageBox 顯示（視窗都沒出現時這個也會跳）
        msg = QMessageBox()
        msg.setWindowTitle("啟動錯誤")
        msg.setText(err)
        msg.exec()
        sys.exit(1)
 
 
if __name__ == "__main__":
    main()