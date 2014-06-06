import logging
from time import strftime

from PyQt4 import uic
from PyQt4.QtGui import QWidget, QTableWidgetItem, QAbstractItemView, QFileDialog
from src.utility import resource_path
from src.modules.module_track_history import ModuleTrackHistory


class UITrackHistory(QWidget):

    isListening = False
    recognizer = ModuleTrackHistory()

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        self.widget = uic.loadUi(resource_path('interface/tab_history.ui'), self)

        self.widget.tableTrackHistory.setSelectionBehavior(QAbstractItemView.SelectRows)

        # Set table sizes
        self.widget.tableTrackHistory.setColumnWidth(0, 50)
        self.widget.tableTrackHistory.setColumnWidth(1, 163)
        self.widget.tableTrackHistory.setColumnWidth(2, 260)

        # Connect signals
        self.widget.buttonStartStop.clicked.connect(self.listeningStartStop)
        self.widget.buttonDeleteRow.clicked.connect(self.delete_row)
        self.connect(self.recognizer, self.recognizer.signal_positive_result, self.add_item)
        self.widget.buttonSaveAs.clicked.connect(self.save_list_as)

    def listeningStartStop(self):
        if self.isListening:
            self.isListening = False
            self.widget.buttonStartStop.setText('Music recognition:\nEnable')
            self.listeningStop()
        else:
            self.isListening = True
            self.widget.buttonStartStop.setText('Music recognition:\nDisable')
            self.listeningStart()

    def listeningStart(self):
        self.set_status('Listening...')
        self.recognizer.start()

    def listeningStop(self):
        self.set_status()
        self.recognizer.shutdown()

    def save_list_as(self):
        default_filename = 'Playlist ' + strftime('%Y-%m-%d') + '.txt'

        filepath = QFileDialog.getSaveFileName(caption='Save playlist as...', directory=default_filename)

        if filepath == '':
            return

        table = self.widget.tableTrackHistory

        with open(filepath, 'w') as f:

            f.write('Playlist ' + strftime('%Y-%m-%d'))
            f.write('\n\n')

            for row in range(0, table.rowCount()):

                f.write(table.item(row, 1).text() + ' - ' + table.item(row, 2).text())
                f.write('\n')



    def add_item(self, artist, track):

        currentTime = strftime('%H:%M')

        table = self.widget.tableTrackHistory
        table.setRowCount(table.rowCount() + 1)

        table.setItem(table.rowCount() - 1, 0, QTableWidgetItem(currentTime))
        table.setItem(table.rowCount() - 1, 1, QTableWidgetItem(artist))
        table.setItem(table.rowCount() - 1, 2, QTableWidgetItem(track))

        logging.info('added item to history table: ' + artist + ', ' + track + ', ' + repr(currentTime))

        table.scrollToBottom()

    def delete_row(self):
        table = self.widget.tableTrackHistory

        selectedRows = table.selectionModel().selectedRows()

        if len(selectedRows):
            logging.info('removed history: ' + repr(selectedRows))

            for n in selectedRows:
                table.removeRow(n.row())

    def set_status(self, status=None):
        if status is None:
            status = 'Idle'

        self.widget.labelStatus.setText(status)