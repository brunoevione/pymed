import sys, time, os
from PyQt5.uic import loadUi
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QFileDialog
from PyQt5.QtCore import *
from pymed.api import PubMed

import csv, pandas as pd
import itertools

class GetArticlesThread(QThread):
    # cria sinal para valor que desejo enviar. Se for mais de 1 valor, basta declarar os tipos (int str dict), pe.
    update_progress = pyqtSignal(int)


    def __init__(self, query, articles_amount, batch, pubmed, fname):
        super(QThread, self).__init__()
        self.query = query
        self.articles_amount = articles_amount
        self.batch = batch
        self.pubmed = pubmed
        self.fname = fname.replace('/','\\')

    def run(self):
        articles_ids = self.pubmed._getArticleIds(self.query, int(self.articles_amount))
        count_completed = 0
        articles = []

        for x in range(0, self.articles_amount, self.batch):
            result = self.pubmed._getArticles(articles_ids[x :  min(x + self.batch, self.articles_amount)])
            articles.append(result)
            count_completed += self.batch
            round_progress = int(count_completed * 100 / self.articles_amount) if int(count_completed * 100 / self.articles_amount)<=100 else 100
            self.update_progress.emit(round_progress) #emite o sinal desejado, que é recebido update_progress.connect
            time.sleep(0.5) # ver como vai ficar essa verificacao com o acesso direto aos metodos
        
        try:
            iteravel = itertools.chain.from_iterable(articles)
        except Exception as e:
            print('Erro na geracao do iteravel')
            print(e)
        try:
            pubmed = [article.toDict() for article in iteravel]
        except Exception as e:
            print('Erro na geracao do dataframe pubmed')
            print(e)
        try:
            pd.DataFrame(pubmed).to_csv(self.fname, index=False, quoting=csv.QUOTE_ALL)
        except Exception as e:
            print('Erro na geracao do csv')
            print(e)

        
        

    def checkStopIteration(self):
        pass


class MainWindow(QDialog):
    total_articles = 0
    query = ''
    stopIteration = pyqtSignal(bool)

    def __init__(self):
        super(MainWindow,self).__init__()
        self.search = loadUi('search_frames.ui')
        self.search.search_button.clicked.connect(self.get_count)
        self.search.get_articles_button.clicked.connect(self.get_articles_thread)
        self.search.browse_filesystem.clicked.connect(self.browse_filesystem)
        self.search.stop_get_articles_button.clicked.connect(self.confirm_stop_iteration)
        # self.search.total_input.clicked.connect(self.check_radio_number)
        self.search.frame_get_articles.setVisible(False) 
        self.search.frame_progress.setVisible(False)     
        self.search.show()
        self.pubmed = PubMed()

        self.total_input =  self.search.total_input
        self.total_input.mouseReleaseEvent = self.check_radio_number



    def get_count(self):
        # self.reset_progress_bar()
        self.query = self.search.query_input.text()
        results = self.pubmed.getTotalResultsCount(self.query)
        self.total_articles = results
        self.search.result_label.setText(f'{results} resultados encontrados')
        self.search.frame_get_articles.setVisible(True)
        suggested_filename = os.path.expanduser('~\Documents') + '\\' + self.query.replace(' ','_') + '.csv'
        self.search.filename_input.setText(suggested_filename)

    def _get_input_amount(self):
        if self.search.radio_all.isChecked():
            return self.total_articles
        return int(self.search.total_input.text())

    def _get_input_bacth(self):
        return int(self.search.batch_input.text())

    def check_radio_number(self, event):
        self.search.radio_number.setChecked(True)

    def get_articles_thread(self):
        self.reset_progress_bar()
        self.search.frame_progress.setVisible(True)
        query = self.query
        articles_amount = self._get_input_amount()
        batch = self._get_input_bacth()
        pubmed = self.pubmed
        if self.validate_filename():
            fname =  self.search.filename_input.text()
            self.get_articles = GetArticlesThread(query, articles_amount, batch, pubmed, fname)
            self.get_articles.start()
            self.get_articles.update_progress.connect(self.update_progress) # recebe o sinal enviado e chama funcao
            self.get_articles.finished.connect(self.search_finished)
        else:
            QMessageBox.information(self, 'Erro', 'Favor informar local para salvar arquivo')
            


    def search_finished(self):
        self.search.get_articles_progress.setValue(100)
        msg_done = QMessageBox.information(self, 'Fim', 'Artigos salvos com sucesso')

    def update_progress(self, value):
        self.search.get_articles_progress.setValue(value)

    def reset_progress_bar(self):
        self.search.get_articles_progress.setValue(0)

    def browse_filesystem(self):
        dir = os.path.expanduser('~\Documents')
        fname=QFileDialog.getSaveFileName(self, 'Save file', dir, 'Arquivos csv (*.csv)')
        self.search.filename_input.setText(fname[0])

    def validate_filename(self):
        fname =  self.search.filename_input.text()
        return fname.find('\\') != -1 or fname.find('/') != -1

    def confirm_stop_iteration(self):
        confirmation = QMessageBox.question(self, 'Atenção', 'Deseja mesmo parar a busca dos artigos?', buttons=QMessageBox.StandardButtons(QMessageBox.Ok|QMessageBox.Cancel))
        if (confirmation==QMessageBox.Ok):
            self.stop_iteration.emit(True)
        ##################################################
        # como fazer pra o sinal ser recebido no Worker? #
        # pq ai poderia salvar os artigos ja obtidos     #
        # m ndar um stop so interromperia a thread       #
        ################################################ #

        # uma possibilidade: criar uma variavel global q eh consultada a cada loop for na thread
        

    def sucess_stop_get_articles(self):
        # alerta informando q parou
        self.reset_progress_bar()
        pass




if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainwindow = MainWindow()
    widget=QtWidgets.QStackedWidget()
    widget.addWidget(mainwindow)
    sys.exit(app.exec_())
