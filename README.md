## Сласти от всех напастей

Все необходимые библиотеки находятся в *requirements.txt*
Скрипт *install.sh* устанавливает все необходимые зависимости

Установка:
 1. git clone git@github.com:GrozniyToaster/academy.git
 2. ./install.sh

Запуск: `python3 app.py`

Стандартно запускается на 0.0.0.0:8080

Запуск тестов: ./unittests.sh

Мажно запускать тесты на удаленной машине, для этого нужно прописать вместо localhost IP адрес тестируемой машины 
(переменная класса теста self.address)

Очистка базы данных нужно выключить приложение и удалить файл *data.db* 
При запуске база данных создаётся снова.


Для удаленной очистки данных можно сделать POST запрос на */clear*, сообщение вида `{"pass": 4685}`
Если вернет ответ с кодом 200, то база данных очищена. 

Сейчас на сервере настроено возобновление работы при перезагрузке сервис yandex_tasks.service 

В проекте используется flask для реализации REST API приложения. 
Pydantic для валидации и сериализации, десериализации Json сообщений.
SQLAlchemy для реализации субд.
Requests и unittest для юнит тестов.
