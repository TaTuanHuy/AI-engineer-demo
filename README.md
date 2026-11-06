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
