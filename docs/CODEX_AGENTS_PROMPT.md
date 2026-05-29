# КОНСТИТУЦИЯ ПРОЕКТА

## Local Legal LLM / Legal Claim AI

### Локальная Legal AI-система подготовки претензий, исков, отправки, загрузки и мониторинга арбитражных дел

---

# 1. Назначение документа

Этот документ является основной “конституцией проекта” для разработчиков, Codex-субагентов, технического лида, QA и аналитиков.

Он определяет:

* назначение системы;
* границы MVP;
* архитектуру;
* роли пользователей;
* бизнес-правила;
* юридические ограничения;
* справочники организаций, сотрудников, подписантов и доверенностей;
* LLM/RAG-контур;
* документный контур;
* интеграции с ФНС, Почтой России, КАД / Мой Арбитр;
* требования к безопасности;
* требования к audit log;
* требования к API;
* требования к frontend;
* требования к тестированию;
* правила работы Codex-субагентов.

Главный принцип проекта:

```text
AI готовит документы, контролирует процесс и помогает юристу.
Профессиональный юрист принимает юридически значимое решение.
```

---

# 2. Цель проекта

Создать локальную Legal AI-систему для автоматизации претензионно-исковой работы предприятия.

Система должна обеспечивать управляемый процесс:

```text
Организация-истец
  ↓
Документы и дебиторская задолженность
  ↓
Претензия
  ↓
Отправка ответчику
  ↓
Контроль срока оплаты
  ↓
Исковое заявление
  ↓
Проверка полномочий подписанта
  ↓
Проверка RAG-источников
  ↓
Утверждение юристом
  ↓
Направление копии иска ответчику
  ↓
Формирование комплекта для суда
  ↓
Подача / ручная фиксация подачи
  ↓
Загрузка и мониторинг дел из КАД
  ↓
Папка дела
  ↓
Дашборд и аудит
```

Система не является “чат-ботом”.
Система является юридическим workflow-контуром с AI-помощниками.

---

# 3. Границы MVP

## 3.1. Входит в MVP

MVP должен включать:

1. Авторизацию и роли.
2. Кабинет дела.
3. Справочник организаций-истцов.
4. Автозаполнение организации по ИНН через FNS Adapter в mock/manual режиме.
5. Справочник сотрудников.
6. Справочник подписантов.
7. Справочник доверенностей.
8. Проверку полномочий подписанта.
9. Загрузку документов по делу.
10. Хранилище документов и версий.
11. OCR / парсинг документов.
12. Извлечение фактов.
13. Локальный LLM-контур.
14. RAG-контур по локальной базе.
15. Генерацию проекта претензии.
16. Генерацию проекта иска.
17. Рабочее место юриста.
18. Чек-листы юридической проверки.
19. Утверждение претензии юристом.
20. Утверждение иска юристом.
21. Почтовые отправления в режиме manual/mock.
22. Загрузку доказательств отправки.
23. CourtArbitrAdapter в режиме manual/mock.
24. Загрузку дел из судебного источника за период.
25. Привязку внешнего судебного дела к внутреннему делу.
26. Формирование папки дела.
27. Экспорт комплекта.
28. Дашборд руководителя.
29. Журнал аудита.
30. DevOps-контур через Docker Compose.
31. Тестовый E2E-сценарий.

---

## 3.2. Не входит в MVP

В MVP не входит:

1. Автоматическая подача документов в суд без участия человека.
2. Автоматическое юридическое утверждение документов AI.
3. Автоматическая оплата госпошлины.
4. Промышленная интеграция с 1С.
5. Промышленная интеграция с Почтой России.
6. Промышленная интеграция с КАД / Мой Арбитр.
7. Электронная подпись.
8. Обучение собственной LLM с нуля.
9. Полный промышленный мониторинг всех судебных событий.
10. Обход защит внешних сайтов.
11. Хранение cookies как основной промышленный механизм.
12. Отправка чувствительных документов во внешние LLM.

---

## 3.3. Допустимые режимы MVP

Для внешних интеграций в MVP разрешены режимы:

```text
MOCK_FOR_DEV
MANUAL_UPLOAD
MANUAL_IMPORT
LOCAL_FILES
```

Архитектура должна быть готова к промышленным режимам:

```text
OFFICIAL_API
LICENSED_PROVIDER_API
ENTERPRISE_INTEGRATION
```

---

# 4. Главные запреты проекта

AI не может:

1. Утверждать претензию.
2. Утверждать иск.
3. Самостоятельно принимать юридически значимое решение.
4. Самостоятельно подавать документы в суд.
5. Самостоятельно отправлять документы ответчику без утвержденного документа.
6. Самостоятельно оплачивать госпошлину.
7. Придумывать данные организации.
8. Придумывать данные руководителя.
9. Придумывать доверенность.
10. Придумывать подписанта.
11. Придумывать нормы права без RAG-источника.
12. Удалять документы.
13. Удалять audit log.
14. Менять утвержденные версии документов.
15. Использовать внешние LLM для чувствительных данных без явного разрешения.

Если источник, полномочие или юридически значимое основание не подтверждено, система должна показать предупреждение и перевести вопрос на проверку юриста.

---

# 5. Технологическая архитектура

## 5.1. Общая схема

```text
Frontend
  ↓
Backend API
  ↓
Business Services
  ↓
Workflow / Audit / Documents / AI / Integrations
  ↓
PostgreSQL / MinIO / Redis / Vector DB / Local LLM
```

---

## 5.2. Основные компоненты

```text
frontend/
  Next.js
  TypeScript
  React
  Tailwind
  shadcn/ui

backend/
  Python
  FastAPI
  SQLAlchemy
  Alembic
  Pydantic
  Celery/RQ worker

storage/
  PostgreSQL
  Redis
  MinIO / S3-compatible storage
  Qdrant или pgvector

ai/
  local LLM server
  OpenAI-compatible API
  embeddings
  reranker
  RAG pipeline

infra/
  Docker Compose
  .env.example
  README
```

---

## 5.3. Backend-структура

```text
backend/
  app/
    api/
      endpoints/
      dependencies/
    core/
      config.py
      security.py
      logging.py
      errors.py
    models/
    schemas/
    repositories/
    services/
      case_service.py
      organization_service.py
      employee_service.py
      signatory_service.py
      power_of_attorney_service.py
      document_service.py
      extraction_service.py
      rag_service.py
      llm_service.py
      pretension_service.py
      claim_service.py
      checklist_service.py
      workflow_service.py
      audit_service.py
      export_service.py
      postal_dispatch_service.py
      court_import_service.py
    integrations/
      fns/
      russian_post/
      court_arbitr/
      onec/
    workers/
    prompts/
    tests/
```

---

# 6. Роли пользователей

## 6.1. Роли

```text
initiator
lawyer
manager
admin
service_agent
```

---

## 6.2. Права

### initiator

Может:

* создавать дело;
* загружать документы;
* видеть свои дела;
* смотреть статус;
* отвечать на комментарии юриста.

Не может:

* утверждать претензию;
* утверждать иск;
* менять доверенности;
* менять настройки интеграций;
* запускать юридически значимые действия без юриста.

---

### lawyer

Может:

* проверять документы;
* редактировать претензию;
* редактировать иск;
* закрывать чек-листы;
* проверять RAG-источники;
* проверять полномочия подписанта;
* утверждать претензию;
* утверждать иск;
* возвращать дело на доработку;
* формировать комплект для суда.

---

### manager

Может:

* видеть дашборд;
* видеть статусы дел;
* видеть просрочки;
* видеть нагрузку по юристам;
* открывать дело в режиме чтения.

---

### admin

Может:

* управлять пользователями;
* управлять организациями;
* управлять сотрудниками;
* управлять подписантами;
* управлять доверенностями;
* загружать правовую базу;
* управлять настройками LLM/RAG;
* управлять настройками интеграций;
* смотреть audit log.

---

### service_agent

Техническая роль для фоновых задач.

Может:

* выполнять задачи очереди;
* обновлять статусы;
* писать технические события;
* выполнять mock/manual integration jobs.

Не может:

* утверждать документы;
* менять юридически значимые данные без логирования;
* удалять документы;
* удалять audit log.

---

# 7. Статусы дела

```text
NEW
DOCUMENTS_UPLOADED
EXTRACTION_IN_PROGRESS
FACTS_EXTRACTED
PRETENSION_DRAFT_READY
PRETENSION_REVIEW
PRETENSION_APPROVED
PRETENSION_DISPATCH_DRAFT
PRETENSION_SENT
WAITING_PAYMENT
CLAIM_DRAFT_READY
LAWYER_REVIEW
RETURNED_FOR_REVISION
APPROVED_BY_LAWYER
CLAIM_COPY_DISPATCH_DRAFT
CLAIM_COPY_SENT
COURT_PACKAGE_DRAFT
COURT_PACKAGE_READY
SUBMITTED_MANUALLY
COURT_CASE_LINKED
IN_COURT_MONITORING
EXPORTED
CLOSED
ERROR_MANUAL_REVIEW
```

---

# 8. Справочник организаций

## 8.1. Назначение

В системе должен быть справочник организаций, от имени которых формируются претензии, иски и иные документы.

Организация используется как:

* истец;
* отправитель претензии;
* владелец дела;
* субъект, от имени которого действует подписант;
* участник загрузки судебных дел из КАД;
* субъект для почтовых отправлений.

---

## 8.2. Создание организации

Пользователь вводит ИНН.

Система через `FnsCompanyAdapter` получает и заполняет:

```text
- полное наименование
- сокращенное наименование
- ИНН
- КПП
- ОГРН
- юридический адрес
- дата регистрации
- статус организации
- ФИО руководителя
- должность руководителя
- дата актуальности сведений
- источник сведений
- технические метаданные ответа
```

---

## 8.3. Режимы FNS Adapter

```text
OFFICIAL_FNS_INTEGRATION
LOCAL_EGRUL_FILES
MANUAL_UPLOAD
MOCK_FOR_DEV
```

Для MVP разрешены:

```text
MOCK_FOR_DEV
MANUAL_UPLOAD
LOCAL_EGRUL_FILES
```

---

## 8.4. Проверка организации

Система должна проверять:

```text
- организация найдена
- ИНН корректен
- ОГРН получен
- КПП получен, если применимо
- организация не ликвидирована
- руководитель определен
- дата актуальности сведений сохранена
```

Если данные неполные, организация получает статус:

```text
REQUIRES_MANUAL_REVIEW
```

---

## 8.5. Organization

```text
id
inn
kpp
ogrn
full_name
short_name
legal_address
registration_date
status
current_director_name
current_director_position
fns_actual_date
fns_source
last_fns_sync_at
requires_manual_review
created_at
updated_at
```

---

## 8.6. OrganizationSnapshot

```text
id
organization_id
snapshot_json
source
source_actual_date
hash
created_by
created_at
```

---

## 8.7. FnsCompanyLookupLog

```text
id
inn
request_payload
response_payload
status
error_message
source
requested_by
created_at
```

---

# 9. Сотрудники, подписанты и доверенности

## 9.1. Общий принцип

Претензия или иск не могут быть утверждены, если не выбран подписант и не подтверждены его полномочия.

---

## 9.2. Employee

```text
id
organization_id
user_id
full_name
position
email
phone
status
created_at
updated_at
```

Сотрудник может быть связан с учетной записью пользователя.

Важно:

```text
Доверенность связывается с employee_id и user_id.
Пароль не хранится в открытом виде.
Пароль не связывается с доверенностью.
Пароль хранится только как безопасный hash в системе авторизации.
```

---

## 9.3. Signatory

```text
id
organization_id
employee_id
signatory_type
full_name
position
authority_basis_type
authority_basis_text
status
created_at
updated_at
```

Типы подписантов:

```text
DIRECTOR
AUTHORIZED_EMPLOYEE
```

---

## 9.4. Директор

Если подписант является действующим руководителем организации по данным ФНС/ЕГРЮЛ, система считает его базово уполномоченным.

Для директора основание полномочий:

```text
Действует на основании Устава / сведений ЕГРЮЛ.
```

Текст основания должен быть редактируемым юристом.

---

## 9.5. Сотрудник по доверенности

Если подписант не является директором, обязательна доверенность.

---

## 9.6. PowerOfAttorney

```text
id
organization_id
employee_id
number
issued_at
valid_from
valid_until
status
file_document_id
issued_by
signed_by
authority_scope_json
created_at
updated_at
last_checked_at
```

---

## 9.7. Статусы доверенности

```text
DRAFT
ACTIVE
EXPIRED
REVOKED
SUSPENDED
REQUIRES_REVIEW
```

---

## 9.8. Полномочия по доверенности

Минимальный набор полномочий:

```text
SIGN_PRETENSION
SIGN_CLAIM
REPRESENT_IN_COURT
SUBMIT_COURT_DOCUMENTS
RECEIVE_COURT_DOCUMENTS
SIGN_SETTLEMENT
SIGN_POWER_OF_ATTORNEY_COPY
```

Для MVP обязательны:

```text
SIGN_PRETENSION
SIGN_CLAIM
REPRESENT_IN_COURT
```

---

## 9.9. PowerOfAttorneyHistory

```text
id
power_of_attorney_id
event_type
old_value
new_value
created_by
created_at
comment
```

История должна фиксировать:

```text
- создание
- загрузку файла
- изменение срока
- изменение статуса
- отзыв
- истечение срока
- ручную проверку юристом
- использование при подписании документа
```

---

## 9.10. Проверка полномочий

Перед утверждением претензии проверяется:

```text
- организация выбрана
- подписант выбран
- если подписант директор — он соответствует руководителю организации
- если подписант сотрудник — есть активная доверенность
- доверенность не истекла
- доверенность не отозвана
- есть полномочие SIGN_PRETENSION
```

Перед утверждением иска проверяется:

```text
- организация выбрана
- подписант выбран
- если директор — подтвержден по данным организации
- если сотрудник — есть активная доверенность
- есть полномочие SIGN_CLAIM
- есть полномочие REPRESENT_IN_COURT
- файл доверенности загружен
- доверенность добавлена в список приложений
```

---

## 9.11. SignatoryAuthorityCheck

```text
id
case_id
organization_id
signatory_id
power_of_attorney_id
document_type
check_result
reasons_json
checked_at
checked_by
```

Результаты:

```text
VALID
WARNING
INVALID
```

Если результат `INVALID`, утверждение документа запрещено.

---

# 10. Документный контур

## 10.1. Поддерживаемые форматы

```text
PDF
DOCX
XLSX
PNG
JPG
TXT
EML
ZIP
```

---

## 10.2. Pipeline обработки документа

```text
upload
  ↓
validate
  ↓
store original
  ↓
extract metadata
  ↓
parse text
  ↓
ocr if needed
  ↓
save searchable text
  ↓
create document version
  ↓
link to case
  ↓
send to extraction queue
  ↓
write audit log
```

---

## 10.3. Document

```text
id
case_id
organization_id
type
filename
storage_path
hash
version
status
uploaded_by
created_at
updated_at
```

---

## 10.4. Типы документов

```text
CONTRACT
ADDENDUM
ACT
UPD
INVOICE
PAYMENT_ORDER
CORRESPONDENCE
PRETENSION
PRETENSION_PROOF
CLAIM
CLAIM_COPY_PROOF
POWER_OF_ATTORNEY
STATE_DUTY_PROOF
COURT_SUBMISSION_CONFIRMATION
COURT_ACT
OTHER
```

---

## 10.5. Запрет изменения утвержденных документов

Утвержденная версия претензии или иска не может быть изменена.

Любая правка создает новую версию.

---

# 11. LLM-контур

## 11.1. LLM Server

Подключение к локальной модели должно идти через OpenAI-compatible API.

Настройки:

```text
LLM_BASE_URL
LLM_API_KEY
LLM_MODEL
LLM_TEMPERATURE
LLM_MAX_TOKENS
EMBEDDING_MODEL
RERANKER_MODEL
RAG_TOP_K
RAG_CHUNK_SIZE
RAG_CHUNK_OVERLAP
```

---

## 11.2. Рекомендуемые модели

Для MVP:

```text
Qwen Instruct 14B–32B
Llama Instruct 8B–70B
Mistral / Mixtral Instruct
Gemma Instruct
```

Embeddings:

```text
bge-m3
multilingual-e5-large
jina-embeddings
nomic-embed-text
```

Reranker:

```text
bge-reranker
jina-reranker
multilingual cross-encoder
```

---

## 11.3. Prompt Registry

Каждый prompt должен иметь:

```text
name
version
input_schema
output_schema
template
created_at
```

Минимальные prompt-шаблоны:

```text
extract_contract_facts
extract_act_facts
extract_invoice_facts
summarize_case
generate_rag_queries
generate_pretension
review_pretension
generate_claim
detect_claim_risks
generate_appendix_list
answer_lawyer_comment
check_signatory_authority_context
```

---

## 11.4. Правила LLM

LLM обязана:

```text
- использовать данные организации только из справочника
- использовать данные подписанта только из справочника
- использовать доверенность только из справочника доверенностей
- не выдумывать ИНН, КПП, ОГРН, адрес, руководителя
- не выдумывать номер доверенности
- не выдумывать дату доверенности
- не выдумывать срок доверенности
- маркировать спорные места
- возвращать structured JSON там, где возможно
- передавать предупреждения юристу
```

---

# 12. RAG-контур

## 12.1. Назначение

RAG используется для:

```text
- поиска норм права
- поиска судебной практики
- поиска внутренних шаблонов
- поиска методик юридического отдела
- поиска документов дела
- формирования правового обоснования
- проверки комплектности
```

---

## 12.2. Источники RAG

```text
- локальная правовая база
- локальная судебная практика
- внутренние шаблоны
- документы дела
- методические материалы
```

---

## 12.3. RagSource

```text
id
title
source_type
document_date
jurisdiction
category
fragment
page
section
url_or_internal_path
score
created_at
```

---

## 12.4. Правило ссылок

Если RAG-источник не найден, LLM не имеет права создавать ссылку на норму или практику.

Вместо этого система должна вернуть:

```text
Источник не найден. Требуется проверка юриста.
```

---

# 13. Генерация претензии

## 13.1. Входные данные

```text
- организация-истец
- данные организации
- подписант
- полномочия подписанта
- договор
- акты
- счета
- сумма задолженности
- расчет неустойки
- адрес ответчика
- документы-доказательства
```

---

## 13.2. Структура претензии

```text
1. Адресат
2. Отправитель
3. Основание обязательства
4. Описание нарушения
5. Расчет задолженности
6. Требование об оплате
7. Срок исполнения
8. Последствия неисполнения
9. Приложения
10. Подписант и основание полномочий
```

---

## 13.3. Правило подписанта

Если подписант директор:

```text
Основание: действует на основании Устава / сведений ЕГРЮЛ.
```

Если подписант сотрудник:

```text
Основание: доверенность № ___ от ___, срок действия до ___.
```

---

# 14. Генерация искового заявления

## 14.1. Входные данные

```text
- карточка дела
- организация-истец
- подписант
- доверенность, если применимо
- утвержденная претензия
- доказательство направления претензии
- договор
- акты
- счета
- расчет задолженности
- RAG-источники
- комментарии юриста
```

---

## 14.2. Структура иска

```text
1. Арбитражный суд
2. Истец
3. Ответчик
4. Цена иска
5. Госпошлина
6. Обстоятельства дела
7. Доказательства
8. Правовое обоснование
9. Расчет требований
10. Досудебный порядок
11. Просительная часть
12. Приложения
13. Подписант и основание полномочий
```

---

## 14.3. Доверенность в приложениях

Если иск подписывает сотрудник по доверенности, система обязана добавить доверенность в список приложений.

Если доверенность отсутствует, истекла или не содержит нужных полномочий, утверждение иска запрещено.

---

# 15. Почта России

## 15.1. Назначение

Интеграция с Почтой России нужна для:

```text
- направления претензии ответчику
- направления копии иска ответчику
- получения трек-номера
- контроля доставки
- получения доказательства вручения
- сохранения доказательств в папку дела
```

---

## 15.2. RussianPostAdapter

Модуль:

```text
backend/app/integrations/russian_post/
  provider.py
  schemas.py
  service.py
  otpravka_provider.py
  ezp_provider.py
  manual_provider.py
  mock_provider.py
  tasks.py
```

---

## 15.3. Режимы работы

```text
RUSSIAN_POST_OTPRAVKA_API
RUSSIAN_POST_EZP_API
MANUAL_UPLOAD
MOCK_FOR_DEV
```

Для MVP:

```text
MANUAL_UPLOAD
MOCK_FOR_DEV
```

---

## 15.4. RussianPostProvider

```python
class RussianPostProvider:
    async def normalize_address(self, address: str) -> AddressNormalizationResult:
        ...

    async def calculate_delivery_cost(self, request: DeliveryCostRequest) -> DeliveryCostResult:
        ...

    async def create_letter(self, request: CreateLetterRequest) -> CreateLetterResult:
        ...

    async def send_letter(self, letter_id: str) -> SendLetterResult:
        ...

    async def get_tracking_status(self, tracking_number: str) -> TrackingStatusResult:
        ...

    async def get_delivery_proof(self, tracking_number: str) -> DeliveryProofResult:
        ...
```

---

## 15.5. PostalDispatch

```text
id
case_id
organization_id
recipient_name
recipient_inn
recipient_address
normalized_recipient_address
dispatch_type
provider
status
tracking_number
external_letter_id
external_batch_id
sent_at
delivered_at
delivery_failed_at
proof_document_id
created_by
created_at
updated_at
error_message
raw_payload_json
```

---

## 15.6. Типы отправлений

```text
PRETENSION
CLAIM_COPY
COURT_DOCUMENT_COPY
OTHER
```

---

## 15.7. Статусы отправлений

```text
DRAFT
ADDRESS_NORMALIZATION_REQUIRED
READY_TO_SEND
SENDING
SENT
IN_TRANSIT
DELIVERED
DELIVERY_FAILED
RETURNED
CANCELLED
MANUAL_REVIEW_REQUIRED
```

---

## 15.8. PostalProofDocument

```text
id
postal_dispatch_id
document_id
proof_type
source
created_at
```

Типы доказательств:

```text
SEND_RECEIPT
TRACKING_REPORT
DELIVERY_NOTICE
RETURN_NOTICE
F103
EZP_CONFIRMATION
OTHER
```

---

## 15.9. Правило направления копии иска

Если отсутствует `PostalDispatch` типа `CLAIM_COPY` со статусом `SENT` или `DELIVERED`, система не может перевести дело в статус:

```text
COURT_PACKAGE_READY
```

Для MVP допускается ручная загрузка доказательства направления.

---

# 16. КАД / Мой Арбитр / CourtArbitrAdapter

## 16.1. Назначение

CourtArbitrAdapter нужен для:

```text
- загрузки дел из КАД / судебного источника за период
- поиска дел по организации, ИНН, роли участия
- сохранения внешних дел в локальной БД
- привязки внешнего дела к внутреннему делу
- мониторинга судебных событий
- подготовки комплекта для ручной подачи
- фиксации факта подачи
```

---

## 16.2. Режимы работы

```text
OFFICIAL_API
LICENSED_PROVIDER_API
PUBLIC_SEARCH
MANUAL_IMPORT
MOCK_FOR_DEV
```

Для MVP:

```text
MANUAL_IMPORT
MOCK_FOR_DEV
PUBLIC_SEARCH_ONLY_IF_ALLOWED
```

Запрещено:

```text
- реализовывать обход защит
- считать наличие официального API гарантированным
- хранить cookies как промышленный механизм
- смешивать парсинг публичной страницы с бизнес-логикой
```

---

## 16.3. CourtArbitrAdapter

```text
backend/app/integrations/court_arbitr/
  provider.py
  schemas.py
  service.py
  kad_provider.py
  my_arbitr_provider.py
  manual_provider.py
  mock_provider.py
  parser.py
  tasks.py
```

---

## 16.4. CourtArbitrProvider

```python
class CourtArbitrProvider:
    async def import_cases(self, request: CourtCaseImportRequest) -> CourtCaseImportResult:
        ...

    async def search_cases(self, request: CourtCaseSearchRequest) -> CourtCaseSearchResult:
        ...

    async def get_case_card(self, external_case_id: str) -> ExternalCourtCaseCard:
        ...

    async def refresh_case_status(self, external_case_id: str) -> CourtCaseStatusResult:
        ...

    async def get_case_events(self, external_case_id: str) -> list[CourtCaseEventData]:
        ...

    async def prepare_submission_package(self, case_id: int) -> CourtSubmissionPackage:
        ...
```

---

## 16.5. Загрузка дел за период

Пользователь указывает:

```text
organization_id
inn
date_from
date_to
participant_role
```

Дополнительно:

```text
court
case_number
case_type
judge
only_new
```

Роли участия:

```text
ANY
PLAINTIFF
DEFENDANT
THIRD_PARTY
OTHER
```

---

## 16.6. CourtCaseImportJob

```text
id
organization_id
inn
date_from
date_to
participant_role
court
case_number
case_type
status
provider
started_by
started_at
finished_at
total_found
total_imported
total_duplicates
error_message
created_at
updated_at
```

Статусы:

```text
CREATED
RUNNING
DONE
FAILED
PARTIAL
CANCELLED
```

---

## 16.7. ExternalCourtCase

```text
id
organization_id
import_job_id
source
external_id
case_number
case_link
case_type
court
judge
registration_date
plaintiff_name
plaintiff_inn
respondent_name
respondent_inn
third_parties_json
current_status
current_instance
last_event_date
raw_payload_json
payload_hash
created_at
updated_at
last_checked_at
linked_case_id
```

---

## 16.8. CourtCaseEvent

```text
id
external_court_case_id
event_date
event_type
title
description
instance
document_link
document_id
raw_payload_json
payload_hash
created_at
```

---

## 16.9. CourtCaseSnapshot

```text
id
external_court_case_id
snapshot_json
snapshot_hash
source
created_at
```

---

# 17. Комплект для суда

## 17.1. CourtSubmissionPackage

```text
id
case_id
status
package_document_id
claim_document_id
attachments_json
postal_proof_document_id
state_duty_document_id
created_by
created_at
updated_at
```

Статусы:

```text
DRAFT
READY_FOR_MANUAL_SUBMISSION
SUBMITTED_MANUALLY
SUBMISSION_CONFIRMED
REJECTED
```

---

## 17.2. Правила готовности комплекта

Комплект может быть готов к ручной подаче, только если:

```text
- иск утвержден юристом
- организация-истец выбрана
- подписант выбран
- полномочия подписанта подтверждены
- есть файл иска
- есть расчет требований
- есть список приложений
- есть доказательство направления копии иска ответчику
```

Если отсутствует госпошлина, система должна показать warning.
Блокировка по госпошлине определяется настройкой проекта.

---

# 18. Папка дела

После утверждения иска и формирования комплекта система должна поддерживать структуру:

```text
/Дело_{case_id}
  /01_Исходные_документы
  /02_Организация_и_полномочия
  /03_Претензия
  /04_Отправка_претензии
  /05_Проект_иска
  /06_Утверждено_юристом
  /07_Расчет_требований
  /08_Источники_RAG
  /09_Направление_копии_иска
  /10_Комплект_для_суда
  /11_КАД_и_судебные_события
  /12_Журнал_действий
```

---

# 19. Основные API-группы

```text
/auth
/users
/roles
/organizations
/employees
/signatories
/powers-of-attorney
/fns
/cases
/documents
/extraction
/rag
/pretensions
/claims
/checklists
/workflow
/russian-post
/postal-dispatches
/court-import
/external-court-cases
/court-submission
/audit
/dashboard
/export
/settings
```

---

## 19.1. Organizations API

```text
POST /organizations/lookup-by-inn
POST /organizations
GET /organizations
GET /organizations/{id}
PATCH /organizations/{id}
POST /organizations/{id}/refresh-fns
GET /organizations/{id}/snapshots
```

---

## 19.2. Employees API

```text
POST /organizations/{organization_id}/employees
GET /organizations/{organization_id}/employees
GET /employees/{id}
PATCH /employees/{id}
```

---

## 19.3. Signatories API

```text
POST /organizations/{organization_id}/signatories
GET /organizations/{organization_id}/signatories
GET /signatories/{id}
PATCH /signatories/{id}
POST /signatories/{id}/check-authority
```

---

## 19.4. Powers of Attorney API

```text
POST /employees/{employee_id}/powers-of-attorney
GET /employees/{employee_id}/powers-of-attorney
GET /powers-of-attorney/{id}
PATCH /powers-of-attorney/{id}
POST /powers-of-attorney/{id}/revoke
POST /powers-of-attorney/{id}/upload-file
GET /powers-of-attorney/{id}/history
```

---

## 19.5. Postal Dispatch API

```text
POST /cases/{case_id}/postal-dispatches
GET /cases/{case_id}/postal-dispatches
GET /postal-dispatches/{id}
PATCH /postal-dispatches/{id}
POST /postal-dispatches/{id}/send
POST /postal-dispatches/{id}/refresh-status
POST /postal-dispatches/{id}/upload-proof
GET /postal-dispatches/{id}/proofs
```

---

## 19.6. Court Import API

```text
POST /court-import/jobs
GET /court-import/jobs
GET /court-import/jobs/{id}
POST /court-import/jobs/{id}/cancel
POST /court-import/jobs/{id}/retry
GET /court-import/jobs/{id}/cases
GET /court-import/jobs/{id}/logs
```

---

## 19.7. External Court Cases API

```text
GET /external-court-cases
GET /external-court-cases/{id}
POST /external-court-cases/{id}/refresh
GET /external-court-cases/{id}/events
GET /external-court-cases/{id}/snapshots
POST /external-court-cases/{id}/link-to-case
POST /external-court-cases/{id}/unlink-from-case
```

---

## 19.8. Court Submission API

```text
POST /cases/{case_id}/court-submission-package
GET /cases/{case_id}/court-submission-package
POST /court-submission/{id}/mark-submitted-manually
POST /court-submission/{id}/upload-confirmation
POST /court-submission/{id}/mark-rejected
```

---

# 20. Frontend-страницы

```text
/login
/cases
/cases/new
/cases/[id]
/cases/[id]/documents
/cases/[id]/facts
/cases/[id]/pretension
/cases/[id]/claim
/cases/[id]/lawyer-review
/cases/[id]/postal-dispatches
/cases/[id]/court
/cases/[id]/court-submission
/organizations
/organizations/[id]
/organizations/[id]/employees
/organizations/[id]/signatories
/organizations/[id]/powers-of-attorney
/court-import
/court-import/[job_id]
/external-court-cases
/external-court-cases/[id]
/dashboard
/audit
/settings
/settings/russian-post
/settings/court-arbitr
/settings/llm-rag
/legal-sources
```

---

# 21. Audit Log

Система обязана логировать:

```text
- вход пользователя
- ошибка входа
- создание дела
- изменение дела
- загрузка документа
- скачивание документа
- запуск OCR
- запуск LLM
- запрос к RAG
- генерация претензии
- утверждение претензии
- генерация иска
- утверждение иска
- создание организации
- обновление данных ФНС
- создание сотрудника
- создание подписанта
- создание доверенности
- изменение доверенности
- отзыв доверенности
- проверка полномочий
- создание почтового отправления
- отправка через Почту России
- ручная загрузка доказательства отправки
- обновление трек-статуса
- запуск загрузки дел из КАД
- завершение загрузки дел
- привязка внешнего дела к внутреннему
- создание комплекта для суда
- отметка о ручной подаче
- экспорт папки дела
- изменение настроек интеграций
```

Audit log нельзя удалять через UI/API.

---

# 22. Безопасность

## 22.1. Общие требования

```text
- все endpoint, кроме login/healthcheck, требуют авторизацию
- RBAC обязателен
- пользователь не видит чужие дела без роли
- frontend не знает токены внешних API
- backend не логирует секреты
- API-токены хранятся только в env/secrets
- пароли не хранятся в открытом виде
- файлы скачиваются только после проверки прав
- опасные файлы запрещены к загрузке
- имена файлов нормализуются
- утвержденные версии не меняются
- audit log нельзя удалить
```

---

## 22.2. Особые требования по доверенностям

```text
- доступ к доверенностям ограничен ролями
- доверенности чужой организации недоступны
- изменения доверенностей логируются
- использование доверенности при подписании логируется
- истекшая доверенность блокирует утверждение
- отозванная доверенность блокирует утверждение
```

---

## 22.3. Особые требования по интеграциям

```text
- не писать токены API в audit log
- не писать токены API в обычные логи
- raw_payload хранить без секретов
- ошибки внешнего API показывать безопасно
- все внешние вызовы выполнять через backend
- все внешние вызовы выполнять через adapter interface
```

---

# 23. Настройки

```text
APP_ENV
DATABASE_URL
REDIS_URL
MINIO_ENDPOINT
MINIO_ACCESS_KEY
MINIO_SECRET_KEY
JWT_SECRET

LLM_BASE_URL
LLM_API_KEY
LLM_MODEL
LLM_TEMPERATURE
LLM_MAX_TOKENS
EMBEDDING_MODEL
RERANKER_MODEL
RAG_TOP_K
RAG_CHUNK_SIZE
RAG_CHUNK_OVERLAP

FNS_MODE
FNS_API_BASE_URL
FNS_TIMEOUT_SECONDS

RUSSIAN_POST_MODE
RUSSIAN_POST_API_BASE_URL
RUSSIAN_POST_APP_TOKEN
RUSSIAN_POST_USER_KEY
RUSSIAN_POST_EZP_ENABLED
RUSSIAN_POST_TIMEOUT_SECONDS

COURT_ARBITR_MODE
COURT_ARBITR_PROVIDER
COURT_ARBITR_BASE_URL
COURT_ARBITR_TIMEOUT_SECONDS
COURT_ARBITR_RATE_LIMIT_PER_MINUTE
COURT_ARBITR_PUBLIC_SEARCH_ENABLED
COURT_ARBITR_MANUAL_SUBMISSION_ONLY
```

---

# 24. DevOps

## 24.1. Docker Compose services

```text
frontend
backend
worker
postgres
redis
minio
qdrant
llm-server
```

Если реальный LLM server не поднимается в MVP, должен быть mock/openai-compatible stub.

---

## 24.2. Минимальные команды

```text
make up
make down
make migrate
make seed
make test
make lint
```

---

# 25. Тестирование

## 25.1. Unit tests

Покрыть:

```text
- создание дела
- смену статуса
- запрет некорректного workflow transition
- создание организации по ИНН
- mock-заполнение данных ФНС
- создание сотрудника
- создание подписанта
- создание доверенности
- проверка полномочий директора
- проверка полномочий сотрудника
- истечение доверенности
- отзыв доверенности
- загрузку документа
- создание audit log
- JSON parsing LLM response
- RAG search mock
- создание почтового отправления
- загрузку доказательства отправки
- загрузку дел за период
- исключение дублей
```

---

## 25.2. Integration tests

Покрыть:

```text
- auth flow
- case CRUD
- organization lookup mock
- employee/signatory/power of attorney flow
- document upload
- fact extraction mock
- pretension generation mock
- claim generation mock
- authority check
- postal dispatch manual flow
- court import mock flow
- approval flow
- export flow
```

---

## 25.3. E2E сценарий

```text
1. Войти как admin.
2. Создать организацию по ИНН.
3. Получить mock-данные ФНС.
4. Проверить руководителя.
5. Создать сотрудника.
6. Создать доверенность.
7. Войти как initiator.
8. Создать дело.
9. Выбрать организацию-истца.
10. Загрузить документы.
11. Извлечь факты.
12. Сгенерировать претензию.
13. Войти как lawyer.
14. Проверить полномочия подписанта.
15. Утвердить претензию.
16. Создать почтовое отправление претензии.
17. Загрузить доказательство отправки.
18. Сгенерировать иск.
19. Проверить RAG-источники.
20. Проверить риски.
21. Проверить полномочия подписанта.
22. Закрыть чек-лист.
23. Утвердить иск.
24. Создать отправление копии иска.
25. Загрузить доказательство направления копии иска.
26. Сформировать комплект для суда.
27. Запустить загрузку дел из КАД за период.
28. Получить mock-дела.
29. Привязать внешнее дело к внутреннему.
30. Экспортировать папку дела.
31. Проверить audit log.
32. Проверить dashboard.
```

---

# 26. Codex-субагенты

## 26.1. Общие правила для всех Codex-субагентов

Перед началом работы:

```text
- изучи README
- изучи docs/CODEX_AGENTS_PROMPT.md
- изучи структуру проекта
- изучи существующие модели
- изучи существующие тесты
- не переписывай проект с нуля без необходимости
```

После выполнения задачи дай отчет:

```text
Что сделано:
- ...

Какие файлы изменены:
- ...

Как запустить:
- ...

Как проверить:
- ...

Тесты:
- ...

Ограничения / что осталось:
- ...
```

---

## 26.2. Backend Core Agent

Отвечает за:

```text
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Users/Roles
- Cases
- Organizations
- Employees
- Signatories
- Powers of Attorney
- Workflow
- AuditLog
- PostalDispatch
- CourtImport
- Export
```

---

## 26.3. Frontend Agent

Отвечает за:

```text
- Next.js UI
- login
- cases
- organizations
- employees
- signatories
- powers of attorney
- documents
- lawyer review
- RAG sources
- postal dispatches
- court import
- dashboard
- audit
- settings
```

---

## 26.4. RAG/LLM Agent

Отвечает за:

```text
- OpenAI-compatible LLM client
- prompt registry
- fact extraction
- pretension generation
- claim generation
- risk detection
- RAG search
- embeddings
- reranking
- citations
```

Правило:

```text
LLM не выдумывает организацию, подписанта, доверенность и правовые источники.
```

---

## 26.5. Documents Agent

Отвечает за:

```text
- upload
- validation
- parsing
- OCR
- versions
- PDF generation
- ZIP export
- папка дела
```

---

## 26.6. Security Agent

Отвечает за:

```text
- JWT
- RBAC
- access control
- document access
- organization access
- power of attorney access
- integration secrets
- audit log
- upload security
```

---

## 26.7. QA Agent

Отвечает за:

```text
- unit tests
- integration tests
- E2E tests
- fixtures
- seed users
- test documents
- negative tests
- workflow tests
```

---

## 26.8. DevOps Agent

Отвечает за:

```text
- Docker Compose
- env
- healthchecks
- logs
- local startup
- README
- seed
- test command
```

---

## 26.9. Tech Lead Agent

Проверяет:

```text
- архитектурную целостность
- единый workflow
- RBAC
- audit log
- безопасность
- отсутствие автоутверждения AI
- отсутствие автоподачи в суд
- отсутствие хардкода секретов
- корректность adapter pattern
- тесты
- README
```

---

# 27. Универсальный промт для Codex

```text
Изучи docs/CODEX_AGENTS_PROMPT.md.

Ты работаешь в проекте Local Legal LLM / Legal Claim AI.

Роль субагента:
[Backend / Frontend / RAG / LLM / Documents / Security / QA / DevOps / Tech Lead]

Задача:
[описать задачу]

Контекст:
Проект — MVP локальной Legal AI-системы подготовки претензий и исков.
AI не принимает юридически значимые решения.
Юрист утверждает претензию и иск.
Автоматическая подача в суд не входит в MVP.
Внешние интеграции работают только через adapter interface.

Что нужно сделать:
1. ...
2. ...
3. ...

Ограничения:
- не ломать существующие API
- не хардкодить секреты
- не отправлять документы во внешние сервисы
- не добавлять автоматическую подачу в суд
- не добавлять утверждение документов AI
- не выдумывать данные организации
- не выдумывать доверенности
- не обходить защиты внешних сайтов
- использовать существующий стиль проекта

Критерии приемки:
1. ...
2. ...
3. ...

Тесты:
- добавить / обновить тесты
- указать команду запуска тестов

Финальный отчет:
- что сделано
- какие файлы изменены
- как запустить
- как проверить
- какие ограничения остались
```

---

# 28. Definition of Done

Задача считается выполненной, если:

```text
- код написан
- код прошел review
- есть миграции, если менялась БД
- есть тесты
- endpoint отражен в Swagger
- ошибки обрабатываются
- действия логируются
- роли проверены
- UI-состояния обработаны
- README обновлен, если изменился запуск или поведение
- QA подтвердил сценарий
```

---

# 29. Главный критерий успеха MVP

MVP успешен, если профессиональный юрист может пройти путь:

```text
Организация по ИНН
  ↓
Подписант и полномочия
  ↓
Документы
  ↓
Факты
  ↓
Претензия
  ↓
Отправка / доказательство отправки
  ↓
Иск
  ↓
RAG-источники
  ↓
Проверка юриста
  ↓
Направление копии иска
  ↓
Комплект суда
  ↓
Загрузка/привязка дела из КАД
  ↓
Папка дела
  ↓
Экспорт
  ↓
Аудит
```

без участия разработчика и без ручного копирования между разными системами.

---

# 30. Главный принцип безопасности

Если есть конфликт между скоростью и юридической безопасностью — выбирай юридическую безопасность.

Если есть конфликт между автоматизацией и контролем юриста — выбирай контроль юриста.

Если источник права не найден — не выдумывай.

Если полномочия не подтверждены — не утверждай.

Если действие юридически значимое — требуй подтверждение юриста.

Если внешний API недоступен — переходи в ручной режим.

Если данные чувствительные — не отправляй их наружу.
