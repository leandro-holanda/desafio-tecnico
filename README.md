# Weather Pipeline API

Uma API para previsão de tempo e análise de conforto climático em cidades brasileiras, com integração da Open-Meteo API e armazenamento em banco de dados PostgreSQL.

## Como Rodar o Projeto

### Clonar o projeto

Execute o comando abaixo para clonar este repositório e entrar na pasta do projeto:

```bash
git clone https://github.com/leandro-holanda/desafio-tecnico
cd desafio-tecnico
```


### Pré-requisitos

- Docker e Docker Compose instalados
- Python 3.12+ (se rodar localmente)
- PostgreSQL 15+ (se rodar localmente)

### Como rodar com Docker Compose (Recomendado)

#### Passo 1: Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto:

```bash
touch .env
```

Adicione as seguintes variáveis:

```env
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=weather_db
DB_HOST=db
DB_PORT=5432
```

#### Passo 2: Build e execução

Para rodar em background:

```bash
docker compose up --build -d
```


Isso significa que o banco já está criado e pronto para usar! Não precisa rodar migrations manualmente.

O Swagger da API estará disponível em: **http://localhost:8000/docs/**

#### Passo 3: Verificar saúde da aplicação

```bash
curl http://localhost:8000/health
```

Resposta esperada:
```json
{"status": "ok"}
```


## Endpoints Principais

### 1. Listar cidades disponíveis
```bash
curl http://localhost:8000/api/v1/cities/
```

### 2. Obter previsão e índice de conforto
```bash
curl http://localhost:8000/api/v1/cities/sao-paulo/forecast/
curl http://localhost:8000/api/v1/cities/sao-paulo/forecast/?days=5
```

### 3. Ranking das cidades mais quentes
```bash
curl http://localhost:8000/api/v1/cities/ranking/hottest/
curl http://localhost:8000/api/v1/cities/ranking/hottest/?limit=5
```

### 4. Resumo geral das cidades
```bash
curl http://localhost:8000/api/v1/cities/summary/
```

### 5. Health check
```bash
curl http://localhost:8000/health
```

## Parar a aplicação

Se rodando com Docker Compose:

```bash
docker compose down
```

Para remover volumes (limpar banco de dados):

```bash
docker compose down -v
```

---

### Detalhamento: O que cada arquivo faz

#### 1. `docker-compose.yml`
Define a orquestração:
```yaml
app:
  depends_on:
    - db          # app inicia DEPOIS que db está ready
  command: uvicorn weather.app:app --host 0.0.0.0 --port 8000 --reload
```

#### 2. `Dockerfile`
Prepara a imagem:
```dockerfile
RUN pip install -r requirements.txt
COPY . .
```


#### 4. `migrations/versions/` 
Contém as migrations versionadas:
```
eb84beacee7a_create_weather_forecast_table.py
└─ Cria a tabela weather_forecast automaticamente
```


 **Neste ponto**: Banco de dados já está com todas as tabelas criadas e a API está pronta para receber requisições!

### Por que é importante?

1. **Automático**: Não precisa rodar `docker exec app alembic upgrade head` manualmente
2. **Idempotente**: Alembic sabe se a migration já foi rodada (não cria duplicata)
3. **Reproduzível**: Qualquer pessoa que clone o repo terá o mesmo ambiente

---
##  Fluxo de Persistência de Dados

### Pergunta: "Quando os dados da API são salvos no banco de dados?"


Quando você roda `docker compose up --build` pela **primeira vez**, o fluxo é:

```
docker compose up --build
    |
[Banco criado + migrations rodadas]
    |
[IMPORTANTE] Banco está VAZIO! Nenhuma previsão foi buscada ainda!
    |
Após isso o conteiner seeder roda o script que fazer a coleta dos dados e aplica no banco.

```


**Resultado:**
```
Banco populado com sucesso.
```

Agora você tem dados para as 5 cidades pré-carregadas!

### Consulta via GET (Apenas Leitura)

Quando você chama:

```bash
curl http://localhost:8000/api/v1/cities/sao-paulo/forecast/
```

**O que acontece:**

```
Request GET /api/v1/cities/sao-paulo/forecast/
    ↓
[Função get_city_forecast() no router]
    ↓
[SELECT * FROM weather_forecast WHERE slug = 'sao-paulo']
    ↓
[Calcula médias, índice de conforto]
    ↓
Response JSON
```

 **Importante**: Os endpoints **apenas LEEM** do banco. Não fazem POST/PUT/DELETE.

## Decisões Técnicas

### 1. Stack Escolhida: FastAPI + PostgreSQL + SQLAlchemy

**Por quê FastAPI?**
- **Performance**: Uma das frameworks web mais rápidas em Python, compete com Node.js e Go, além de ser um dos frameworks mais utilizados atualmente.
- **Developer Experience**: Documentação automática com Swagger UI, validação automática com Pydantic
- **Async/Await nativo**: Suporta operações assíncronas out-of-the-box, ideal para I/O-bound (requisições HTTP, banco de dados)
- **Type hints**: Melhor DX com autocomplete e type checking

**Por quê PostgreSQL?**
- **Confiabilidade**: ACID completo, ideal para dados de previsão que precisam ser consistentes
- **JSON nativo**: Possibilita expandir o schema facilmente
- **Escalabilidade**: Suporta replicação e sharding para volumes grandes
- **Histórico**: 25+ anos de desenvolvimento, maduro e testado

**Por quê SQLAlchemy + Alembic?**
- **ORM robusto**: Queries type-safe, migrations automáticas
- **Migrações versionadas**: Alembic permite rastrear mudanças no schema ao longo do tempo
- **Compatibility**: Suporta múltiplos bancos (fácil migrar se necessário)

### 2. Modelagem do Banco de Dados

#### Tabela `weather_forecast`

```sql
CREATE TABLE weather_forecast (
    id SERIAL PRIMARY KEY,
    city VARCHAR(100),
    slug VARCHAR(100) INDEXED,
    forecast_date DATE,
    temperature_max NUMERIC(5,2),
    temperature_min NUMERIC(5,2),
    precipitation_sum NUMERIC(5,2),
    relative_humidity_2m_max NUMERIC(5,2)
);
```

**Decisões de design:**

- **Denormalização**: Armazenar `city` e `slug` juntos na mesma tabela, mesmo que redundante
  - Leitura mais rápida (sem JOINs)
  - Queries mais simples
  - Redundância pequena, aceitável para este caso de uso

- **Índice em `slug`**: Consultas por cidade são muito comuns
  - Melhora drasticamente a performance de SELECT em previsões

- **NUMERIC(5,2)**: Precisão exata em cálculos de temperatura/precipitação
  - Melhor que FLOAT para dados financeiros/científicos
  - Sem problemas de arredondamento

- **Cidade como referência**: Cidades são armazenadas em `weather/models/cities.py` (hardcoded)
  - Simplifica o projeto inicialmente
  - Com mais tempo: criar tabela `cities` separada e fazer FK

### 3. Fórmula do Índice de Conforto

```
Índice de Conforto = 100 - |temp_média - 22| × 3 - (umidade_média - 60) × 0.4 - precipitação_total × 0.5
Resultado final = max(0, min(100, Índice))
```

**Fundamentação científica:**

1. **Temperatura ideal = 22°C**
   - Pesquisas de conforto térmico (ASHRAE Standard 55) indicam 20-24°C como confortável
   - 22°C é o ponto médio, balanceado para diferentes atividades

2. **Penalidade por temperatura = 3 pontos por °C**
   - Desvios grandes impactam mais o conforto
   - A cada 1°C longe de 22°C, perde 3 pontos

3. **Umidade ideal = 60%**
   - ASHRAE recomenda 30-60% para conforto
   - 60% é o limite superior (acima disso começa a ficar abafado)
   - Penalidade = 0.4 por 1% acima de 60% (menor impacto que temperatura)

4. **Precipitação = -0.5 por mm**
   - Reduz conforto (atividades ao ar livre)
   - Impacto moderado (0.5 é menor que temperatura)

5. **Intervalo 0-100**
   - 100: Condições climáticas ideais
   - 50: Mediocre (aceitável)
   - 0: Condições muito desfavoráveis

**Exemplo:**
- São Paulo com 25°C média, 70% umidade, 5mm de chuva:
  - `100 - |25-22|×3 - (70-60)×0.4 - 5×0.5`
  - `100 - 9 - 4 - 2.5 = 84.5` Confortável


##  O Que Faria Diferente com Mais Tempo

### 1. **Tabela `cities` separada**
   - Atualmente: cidades hardcoded em `cities.py`
   - Melhor: Tabela `cities` com campos id, name, slug, latitude, longitude, timezone
   - Benefício: Admin UI para gerenciar cidades dinamicamente

### 2. **Integração com Redis para cache**
   - Dados da Open-Meteo são atualizados 1x por dia
   - Redis cache diminuiria latência e economia de API calls

### 3. **Sistema de alertas (Webhooks)**
   - Notificar quando previsão ultrapassar limites (ex: temp > 35°C, chuva intensa)
   - Implementar com Celery + Redis para jobs assincronos

### 4. **Histórico de previsões**
   - Comparar previsão vs. realidade (foi acertada?)
   - Tabela `weather_actual` para dados reais
   - Calcular accuracy do modelo de previsão

### 5. **Autenticação + Rate limiting**
   - JWT para autenticação
   - Throttling por IP/usuário
   - Chaves de API para clientes

### 6. **Testes automatizados**
   - Unit tests com `pytest`
   - Integration tests com `testcontainers`
   - Coverage > 80%


---

## Atribuição

### Open-Meteo API

Este projeto utiliza dados de previsão de tempo fornecidos pela **[Open-Meteo](https://open-meteo.com/)**.

Dados climatológicos estão disponíveis sob a licença **[Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/)**.

**Atribuição requerida:**
- Ao usar dados desta API, favor incluir a seguinte menção:
  ```
  "Weather data by Open-Meteo (https://open-meteo.com/)"
  ```

**Mais informações:**
- [Documentação Open-Meteo](https://open-meteo.com/en/docs)
- [Licença CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

---

## Estrutura do Projeto

```
teste_zoryam/
├── weather/                      # Aplicação principal
│   ├── __init__.py
│   ├── app.py                   # Factory da aplicação FastAPI
│   ├── core/
│   │   ├── database.py          # Configuração SQLAlchemy
│   │   └── settings.py          # Variáveis de ambiente
│   ├── models/
│   │   ├── base.py              # Base declarativa
│   │   ├── cities.py            # Lista hardcoded de cidades
│   │   └── weather_forecast.py  # Schema WeatherForecast
│   ├── routers/
│   │   └── cities.py            # Endpoints de cidades
│   ├── schemas/
│   │   └── schemas.py           # Pydantic models
│   └── services/
│       └── open_meteo.py        # Client HTTP para Open-Meteo
├── migrations/                   # Alembic migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── scripts/                
│   └── seed.py                  # Seed data
├── alembic.ini                  # Config Alembic
├── docker-compose.yml           # Orquestração de containers
├── Dockerfile                   # Build da imagem
├── pyproject.toml               # Config Ruff, Taskipy
├── requirements.txt             # Dependências Python
└── README.md                    # Este arquivo
```

---

## License

Este projeto está sob licença MIT. Dados de previsão estão sob CC BY 4.0 (Open-Meteo).
