from flask import Flask, send_file

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, World!'

@app.route('/download')
def download_file():
    # Путь к файлу, который нужно скачать
    file_path = 'data.xlsx'

    # Отправляем файл пользователю для скачивания
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    app.run()