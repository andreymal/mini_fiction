# Установка и настройка mini_fiction

## Быстрый старт (развёртывание минимального окружения для разработки)

* Устанавливаем системные зависимости:

  * Python 3.8-3.11
  * [Poetry] (официальная документация рекомендует устанавливать его через
    [pipx]; не забудьте настроить переменную окружения `PATH`)
  * [Node.js]
  * [Yarn]
  * GNU Make (для Windows можно взять из MinGW; можно не брать, но тогда
    придётся запускать команды из `Makefile` вручную)

* Скачиваем mini_fiction, выполнив команду `git clone` или просто скачав
  и распаковав zip-архив, и переходим в консоли в каталог с проектом:

  ```
  cd mini_fiction
  ```

* Подготавливаем окружение для разработки. Проект управляется с помощью
  Poetry, который автоматически создаст виртуальное окружение и установит
  в него все обязательные зависимости. Перед выполнением команды убедитесь,
  что в вашем текущем окружении доступны команды `poetry` и `yarn`.

  ```
  make develop
  ```

* По желанию можно доустановить опциональные зависимости:

  ```
  poetry install --all-extras
  ```

* После установки можно для удобства сразу активировать виртуальное окружение:

  ```
  poetry shell
  ```

  Можно не активировать, но тогда вместо команды `mini_fiction` нужно будет
  использовать `poetry run mini_fiction`.

* Создаём каталог под загружаемые данные вроде картинок персонажей или
  аватарок (путь к нему можно изменить в настройках):

  ```
  mkdir media
  ```

* Инициализируем базу данных (с настройками по умолчанию будет создан файл
  `db.sqlite3`):

  ```
  mini_fiction seed
  ```

* Создаём учётную запись администратора:

  ```
  mini_fiction createsuperuser
  ```

* Запускаем сервер для разработки:

  ```
  mini_fiction run
  ```

* Сайт создаст базу данных SQLite3 в текущем каталоге и станет доступен
  по адресу `http://localhost:5000/`. После входа как суперпользователь станет
  доступна админка по адресу `http://localhost:5000/admin/`. Для корректной
  работы сайта нужно создать хотя бы один жанр.

* Проверить корректность основных настроек можно с помощью команды
  `mini_fiction status`.


## Изменение настроек

* Создаём файл `local_settings.py` (в нём хранятся локальные настройки,
  которые нет смысла публиковать) с примерно таким содержимым:

  ```python
  from mini_fiction.settings import Development


  class Local(Development):
      SECRET_KEY = 'some-random-string'
      ...  # здесь и далее все ваши настройки
  ```

* Запускаем `mini_fiction run` (или gunicorn или любой другой wsgi-сервер)
  в том же каталоге, в котором находится `local_settings.py`:
  сайт его найдёт и автоматически подхватит. Если же не подхватит, попробуйте
  переменную окружения `PYTHONPATH=.` (не забудьте про `export PYTHONPATH` в
  юниксовых шеллах; в PowerShell можно использовать `$env:PYTHONPATH="."`).

Для боевого (production) окружения наследуйте класс с настройками от
модуля `mini_fiction.settings.Config` вместо `Development`. Это важно,
так как в режиме разработки доступны некоторые средства для удалённого
выполнения кода. (А ещё крайне желательно прописать случайную строку в
`SECRET_KEY` для защиты пользовательских сессий.)

Скорее всего, вы захотите изменить домен по умолчанию `localhost:5000`
на какой-нибудь другой. Для этого пропишите настройку
`SERVER_NAME = 'example.com'` (если порт нестандартный, его тоже нужно
прописать через двоеточие). Если у вас настроен HTTPS, пропишите
`PREFERRED_URL_SCHEME = 'https'` для прописывания этого протокола во всех
ссылках сайта. Другие примеры настроек можно посмотреть в файле
`local_settings.example.py`.

Все настройки, предлагаемые к изменению ниже, прописываются в этом файле
(не забудьте про отступ в четыре пробела — см. `local_settings.example.py`).

Вы также можете переопределить модуль с настройками с помощью переменной
окружения `MINIFICTION_SETTINGS`. Например, если вы создали файл настроек
`my_settings.py` с классом настроек `SuperProd`, пропишите следующую
переменную окружения:

```
MINIFICTION_SETTINGS=my_settings.SuperProd
```

Файл `my_settings.py` может располагаться везде, откуда его сможет
импортировать Python.

Если вы установите модуль `python-dotenv`, то Flask сможет загрузить переменные
окружения из специального файла `.env`, так что вместо постоянного их
прописывания в консоли можно просто записать всё нужное в этот файл.

Если `MINIFICTION_SETTINGS` не указана, то по умолчанию используется
`mini_fiction.settings.Config` при обычном запуске и
`mini_fiction.settings.Test` для тестов.


## Установка дополнительных плюшек

Всё описанное выше это хорошо, только вот не поддерживает поиск и MySQL.
Для них следует установить дополнительные модули (которые собираются
из исходников, с чем бывают проблемы на некоторых ОС, поэтому это всё
опционально).

Ниже приводятся примеры команд для Ubuntu, но можно найти аналоги для
почти любой современной ОС.

Для сборки зависимостей из исходников:

```
sudo apt-get install git build-essential python3-dev
```

Команда `poetry install --all-extras` автоматически установит все опциональные
зависимости, однако вы скорее всего столкнётесь с ошибками компиляции из-за
недостающих библиотек, поэтому ниже приведён их подробный разбор.


### MySQL

* `sudo apt-get install libmysqlclient21` — библиотека для работы с MySQL

* `sudo apt-get install libmysqlclient-dev` нужен для сборки Python-модуля

* `pip install mysqlclient` — установка Python-модуля (не забудьте
  про установку внутри виртуального окружения: `poetry shell`)

* На MySQL-сервере создайте базу данных, не забыв указать кодировку utf8mb4
  (в отличие от просто utf8, utf8mb4 корректно хранит Emoji и прочий юникод):

  ```
  create database mini_fiction character set utf8mb4;
  ```

* Подключаем в настройках:

  ```python
  DATABASE_ENGINE = 'mysql'
  DATABASE = {
      'host': '127.0.0.1',
      'port': 3306,
      'user': 'fanfics',  # Не забудьте вписать свои данные!
      'passwd': 'fanfics',
      'db': 'mini_fiction',
      'charset': 'utf8mb4',
  }
  ```


### Поиск рассказов (Manticore)

* Для подключения к Manticore используется mysqlclient. Установите его как
  описано выше (первые три пункта).

* Для подключения к Manticore, очевидно, нужен сам Manticore :) Смотрите
  инструкции на официальном сайте: https://manticoresearch.com/install/

* Создаём каталоги для работы Manticore (вы можете переопределить путь
  настройкой `SPHINX_ROOT`):

  ```
  mkdir sphinx && mkdir sphinx/binlog
  ```

* Включаем поиск в настройках:

  ```python
  SPHINX_DISABLED = False
  ```

* Теперь можно запустить Manticore. (Примечание: `sphinxconf.sh` просто
  запускает `mini_fiction sphinxconf`, который генерирует настройки;
  не забудьте про включение виртуального окружения (при его наличии) и
  `MINIFICTION_SETTINGS`, иначе что-нибудь пойдёт не так.)

  ```
  searchd --config sphinxconf.sh --nodetach
  ```

* Если база данных уже не пустая, а поиск ещё пустой, то загружаем данные
  в поисковый индекс:

  ```
  mini_fiction initsphinx
  ```


### Воркер Celery для производительности

Обновление индекса поиска и отправка почты могут быть делами небыстрыми,
поэтому целесообразно выполнить их не на веб-сервере, а в отдельном
процессе. Кроме того, есть задачи, выполняемые по расписанию (создание
публичного дампа некоторых настроек сайта каждую ночь). Для всего этого
используется Celery.

* Для связи с отдельным процессом по умолчанию используется Redis:

  ```
  sudo apt-get install redis-server
  ```

* Включаем использование отдельных воркеров в настройках:

  ```python
  CELERY_CONFIG = dict(Config.CELERY_CONFIG)
  CELERY_CONFIG['task_always_eager'] = False
  ```

* Включаем сам воркер:

  ```
  celery -A mini_fiction worker --loglevel=INFO
  ```

* Для выполнения задач по расписанию нужна пиналка, которая будет отправлять
  эти задачи воркеру в указанное в настройках время:

  ```
  celery -A mini_fiction beat
  ```

* Кроме того, есть вариант объединения воркера и пиналки в одном процессе,
  хотя он не рекомендуется документацией Celery:

  ```
  celery -A mini_fiction worker -B --loglevel=INFO
  ```

Управление через консоль также доступно:

```
celery -A mini_fiction status
```


### Кэширование в Redis

Пропишите настройку `CACHE_TYPE = "redis"` и параметры подключения к редису:

```python
CACHE_TYPE = "redis"
CACHE_PARAMS = {
    "host": "127.0.0.1",
    "port": 6379,
    "password": "correcthorsebatterystaple",
    "db": 1,
    "key_prefix": "mfc_",
}
```


### ReCaptcha при регистрации

```python
CAPTCHA_CLASS = 'mini_fiction.captcha.ReCaptcha'
RECAPTCHA_PUBLIC_KEY = '6Ldcxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
RECAPTCHA_PRIVATE_KEY = '6Ldczzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz'
```


### Статика в отдельном каталоге

Если не хочется прописывать в nginx длинный путь к Python-пакету (который
к тому же при обновлении сломается), можно собрать статику в свой каталог
и прописать в nginx путь уже к нему. Для этого пропишите в настройках
этот каталог:

```python
STATIC_ROOT = '/path/to/static'
```

А потом соберите туда статику:

```
mini_fiction collectstatic
```

Недостаток: эту команду нужно выполнять при каждом обновлении mini_fiction.

Теперь можно раздавать статику через nginx, примерно вот так:

```
location /static {
    alias /path/to/static;
}
```

Браузеры будут кэшировать статику. Для эффективной отдачи файлов рекомендуется
использовать версионированные ассеты (см. [long-term caching]).


## Прикручивание своего дизайна

На момент написания этого файла полноценного движка тем не
предоставляется, зато можно переопределять шаблоны Jinja2 и дополнять
статику. Делается это с помощью следующих параметров
(`local_settings.py`):

* `LOCALSTATIC_ROOT = '/path/to/localstatic'` — путь к каталогу с вашей
  статикой. После добавления данного параметра файлы из этого каталога
  становятся доступны по пути `http://example.com/localstatic/` и
  появляется возожность вставлять ссылки в шаблонах через
  `{{ url_for('localstatic', filename='foo/bar.baz') }}`.

* `LOCALTEMPLATES = '/path/to/templates'` — каталог с шаблонами Jinja2.
  При добавлении этого параметра любой загружаемый шаблон ищется сперва в
  указанном вами каталоге, а если он не найден, то берётся шаблон по
  умолчанию. Скорее всего, вам потребуется лишь создать свой `base.html`,
  прописав в нём собственные шапку и CSS. Можно указать несколько каталогов
  с шаблонами, завернув их в питоновый список; каталоги в начале списка
  будут более приоритетными.

* Кроме того, движок автоматически подгрузит информацию об ассетах из файлов
  `localstatic/*/manifest.json`, таким образом вы можете создавать свои
  дополнения к фронтенду без редактирования шаблонов Jinja2 с помощью Webpack
  с плагином `webpack-assets-manifest`.

Можно попробовать поискать архивы и репозитории с готовой конфигурацией
всего этого.

[Poetry]: https://python-poetry.org/

[pipx]: https://github.com/pypa/pipx

[Node.js]: https://nodejs.org/en

[Yarn]: https://yarnpkg.com/

[long-term caching]: https://developers.google.com/web/fundamentals/performance/webpack/use-long-term-caching
