# Fortigate 8.0.0 Copilot

## Configuration

[Application settings](src/fortigate_8_0_0_copilot/config.py) use
`pydantic-settings` to read environment variables.

Create a local `.env` file in the project root from
[.env.example](.env.example) if one does not already exist. The local `.env`
file is ignored by Git.

```dotenv
APP_ENV=development
```

Import the shared settings instance:

```python
from fortigate_8_0_0_copilot.config import settings

app_env = settings.app_env
```

Environment variables override `.env` values. `APP_ENV` defaults to
`development`. In the source checkout, the `.env` path is resolved
relative to the configuration module, not the working directory. For an
installed deployment, supply settings through environment variables.

`APP_ENV` accepts a string. Unrelated `.env` keys are ignored. The shared instance is
loaded once at import time; create `Settings()` to reload configuration.

## Request behavior

The application does not configure logging or catch and format failures.
FastAPI supplies its default validation responses and internal-server-error
responses. Chainlit receives exceptions raised by backend requests or response
validation; the application does not replace them with custom chat messages.
Framework and dependency logging are unchanged.

Input, configuration, and model-response validation remain enabled. Successful
chat responses still include `request_id` and `answer`, with the same request ID
in the `X-Request-ID` header. Validation responses also retain that header.
Unhandled server failures use FastAPI's default response without a request ID.

## Tests

```powershell
$env:LLM_MODEL = "openai/test-model"
$env:LLM_API_KEY = "test-key"
uv run pytest
```