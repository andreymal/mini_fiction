# mini_fiction


## Быстрый старт (развёртывание минимального окружения для разработки)

* Устанавливаем Python версии 3.4 или новее (ОС не имеет значения)

* Некоторые зависимости собираются из исходников, поэтому нужно подготовить систему (на Ubuntu это можно сделать командой `sudo apt-get install build-essential`, на Windows — установить Visual Studio или MinGW) или установить их из бинарников заранее (scrypt и/или bcrypt, mysqlclient, lxml)

* Скачиваем mini_fiction, выполнив команду `git clone` или просто скачав и распаковав zip-архив, и переходим в консоли в каталог с проектом:

    cd mini_fiction

* Опционально, но желательно, чтобы не мусорить в системе: устанавливаем `virtualenv` и создаём виртуальное окружение, в каталоге с проектом выполнив команду:

    virtualenv --no-site-packages env

* Входим в созданное окружение командой `. env/bin/activate` (*sh) или `.\env\Scripts\activate` (командная строка Windows)

* Устанавливаем проект командой `make develop` (пользователям Windows придётся открыть `Makefile` и перепечатать команды вручную или использовать make из MinGW)

* Инициализируем базу данных (будет создан файл `db.sqlite3`):

    mini_fiction seed

* Создаём учётную запись администратора:

    mini_fiction createsuperuser

* Запускаем сервер для разработки:

    mini_fiction runserver

* Сайт станет доступен по адресу `http://localhost:5000/`.


## Развёртывание приближенного к Production окружения (с поиском и прочим)

* Выполняем всё написанное выше

* Дополнительно устанавливаем поисковый движок Sphinx и memcached. Если вы хотите использовать Celery, также поставьте Redis

* Устанавливаем MySQL, создаём пользователя и базу данных для него. Обязательно укажите кодировку UTF-8:

    create database mini_fiction character set utf8;

* Устанавливаем новую зависимость:

    pip install mysqlclient

* Создаём файл `local_settings.py` (в нём хранятся локальные настройки, которые нет смысла публиковать) и включаем в нём всё установленное ранее:

    from mini_fiction.settings import Development

    class Local(Development):
        # Подключаем БД MySQL вместо sqlite3
        DATABASE_ENGINE = 'mysql'
        DATABASE = {
            'host': '127.0.0.1',
            'port': 3306,
            'user': 'fanfics',  # не забудьте вписать свои данные
            'passwd': 'fanfics',
            'db': 'fanfics',
        }

        # Включаем поиск Sphinx
        SPHINX_DISABLED = False

        # Если хочется запустить отдельный воркер Celery, который будет обновлять индекс Sphinx, то прописываем это
        CELERY_ALWAYS_EAGER = False

* Прописываем созданные нами настройки в переменную окружения. Учтите, что созданный вами модуль должен быть доступен для импорта (например, с помощью `export PYTHONPATH=.`):

    export MINIFICTION_SETTINGS = local_settings.Local

* Создаём файл с локальными настройками Sphinx (и настраиваем по желанию):

    cp local_sphinx.example.conf local_sphinx.conf

* В файле sphinxroot.txt указываем рабочий каталог Sphinx:

    echo 'sphinx' > sphinxroot.txt

* И создаём его:

    mkdir sphinx && mkdir sphinx/binlog

* Теперь можно запустить Sphinx:

    searchd --config sphinxconf.py

* Если база данных уже не пустая, а поиск ещё пустой, то загружаем данные в индексы Sphinx:

    mini_fiction initsphinx

* Если вы указали `CELERY_ALWAYS_EAGER = False`, то запускаем воркер Celery, который будет обновлять индекс поиска (тоже в virtualenv при его наличии):

    celery -A mini_fiction worker --loglevel=INFO

Для боевого (production) окружения наследуйте класс с настройками от модуля `mini_fiction.settings.Config` вместо `Development`.
