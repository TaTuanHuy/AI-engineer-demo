# Demo AI API

FastAPI demo managed with `uv` and runnable through Docker Compose.

## Environment variables

Development uses `.env`; Production uses `.env.production`. Add the relevant
Gemini API key to each file:

```dotenv
GEMINI_API_KEY=your-real-api-key
```

The committed `.env.example` and `.env.production.example` document all
supported variables. Real environment files are ignored by Git.

## Docker Development

```powershell
make
```

`make` and `make dev` build the `development` stage from the shared
`docker/Dockerfile`, install development dependencies, mount `./app` into the
container, and start Uvicorn with `--reload`.

To stop Development:

```powershell
make dev-down
```

To run locally without Docker, use `make local`.

## Docker Production

```powershell
make build
make run
```

Production builds the `production` stage from the same `docker/Dockerfile`, excludes
development dependencies, does not mount source code, and starts Uvicorn with
four workers. Stop it with:

```powershell
make down
```

## MongoDB and Qdrant

MongoDB 8.0, Mongo Express 1.0.2-20, and Qdrant 1.20.0 each have dedicated
Compose configuration files under `docker/`. Runtime environment is supplied
from `.env` or `.env.production`, not embedded in Compose service definitions.
MongoDB data persists under
`data/mongo-data`; Qdrant data persists under `data/qdrant-storage`.

Beanie connection lifecycle is in `app/common/mongo/connection.py`; the Qdrant
client is in `app/common/qdrant/connection.py`. Both initialize through FastAPI
lifespan when enabled in Compose.

Start just MongoDB and Qdrant, or add Mongo Express:

```powershell
make dev-database
make dev-db-ui
```

The Compose files can also be used directly:

```powershell
docker compose -p demo-ai --env-file .env -f docker/docker-compose.database.yaml up -d
docker compose -p demo-ai --env-file .env -f docker/docker-compose.database.yaml -f docker/docker-compose.db-ui.yaml up -d
```

Mongo Express UI: <http://localhost:8081>. Qdrant dashboard/API: <http://localhost:6333/dashboard>.

## Current weather API

The weather module uses `geocoder` to resolve a place name into coordinates and
Open-Meteo to retrieve a daily forecast. No API key is required for these
requests.

```http
GET /weather/current?city=Ho%20Chi%20Minh&day=today
```

The `day` parameter accepts exactly `today`, `tomorrow`, or
`day_after_tomorrow`. Omit `city` to infer the caller's approximate location
from their public IP:

```http
GET /weather/current?day=tomorrow
```

IP geolocation is approximate. A browser or mobile client must send GPS
coordinates separately if street-level device location is required.

The response includes the resolved location, forecast date, minimum and maximum
temperature, apparent temperature, precipitation, weather description, sunrise,
sunset, and wind details. The weather values are supplied in Celsius and km/h.

Gemini can call the weather service through the Python tool wrapper:

```python
from app.module.weather.tools import generate_weather_answer

answer = generate_weather_answer(
    "What will the weather be like in Boston tomorrow?"
)
print(answer)
```

The weather assistant endpoint only requires a prompt:

```http
POST /weather/ask
Content-Type: application/json

{
  "prompt": "Ngày mai ở Hà Nội có mưa không?"
}
```

Without GNU Make, run Development with:

```powershell
docker compose --env-file .env -f docker/docker-compose.development.yaml up --build
```

Run Production with:

```powershell
docker compose --env-file .env.production -f docker/docker-compose.production.yaml up --build -d
```

After startup, open the configured `APP_PORT`. The current defaults are port
`3000` for Development and port `8000` for Production:

- Development Swagger: <http://localhost:3000/docs>
- Production Swagger: <http://localhost:8000/docs>

## Prompt evaluation API

To evaluate the prompt currently used by `classify_prompt_llm`, call
`await score_classify_prompt()` from `app.module.multi_model_smart.service`
after MongoDB has been initialized. It reads the dataset saved by
`generate_dataset_scoring_question_complexity`, runs the classifier for each
case, and returns tier accuracy, temperature mean absolute error, and case
details. Failed classifier calls count against tier accuracy. The saved labels
are the reference for the score; review generated labels before relying on it.
For each successful case, the matching score is the mean of tier matching
(10 for an exact match, otherwise 0) and temperature matching
(`10 * (1 - absolute_error / 2)`); cases without a reference temperature use
only tier matching. `average_matching_score_successful` averages successful
cases, while `average_matching_score_all_cases` also counts failures as zero.
The report includes a SHA-256 fingerprint of the current classifier prompt and
flags cases that exactly match a few-shot example after case and whitespace
normalization. These indicators help compare runs; they do not prove the labels
or results are correct.
Each run also writes a standalone HTML report under
`app/module/multi_model_smart/reports/` and returns its absolute path in
`html_report_path`. With the development Compose bind mount, that directory is
available on the host at the same path under the project root.

Call `POST /multi-model-smart-route/classify-prompt/evaluate` (no request body)
to run this evaluation. The response includes `html_report_url` for opening the
report in a browser and per-case token counts. The complete classifier prompt,
each input prompt, and the classifier prompt sections are counted using
`tiktoken` with `cl100k_base`. These counts are estimates, not Gemini's own
token counts. The aggregate includes all test cases, including failed calls.
The first use may download the encoding data required by tiktoken.

Gemini configuration is shared in `common/gemini/`; the model defaults to
`gemini-3.1-flash` and can be changed with `GEMINI_MODEL`. Set
`GEMINI_API_KEY` in the selected `.env` file before calling these endpoints.

1. `POST /prompt-evaluation/datasets` takes human-authored seed cases and
   optional criteria. Gemini expands them into additional cases and saves the
   complete dataset as JSON. The response includes a dataset JSON URL.
2. `GET /prompt-evaluation/datasets` lists saved datasets in an HTML page.
3. `POST /prompt-evaluation/evaluate` takes a prompt template and a reachable
   dataset JSON URL. Use `{{input_key}}` placeholders in the prompt. Gemini
   runs it against every case, grades each output from 1 to 10, and saves a
   JSON result and an HTML report.

Example dataset request:

```json
{
  "task_description": "Write Python code that lists S3 buckets",
  "test_cases": [
    {"inputs": {"task": "List every S3 bucket"}, "notes": "Basic request"},
    {"inputs": {"task": "List S3 buckets and handle permission errors"}, "notes": "Error handling"}
  ],
  "additional_cases": 3,
  "criteria": ["Uses boto3", "Returns bucket names", "Handles AWS errors"]
}
```

The dataset URL sent to `/evaluate` must be reachable by the API process. For
local Docker use, expose the JSON file through a reachable HTTP server or use
the dataset file endpoint returned by dataset creation when the API is
reachable from the caller. Evaluation reports are available under
`/prompt-evaluation/files/<filename>`.

## Run tests

```powershell
uv run pytest
```
